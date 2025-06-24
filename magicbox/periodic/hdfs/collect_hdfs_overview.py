#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import logging
import sys
import time
from typing import Optional, Dict, Any
import re
from datetime import datetime
from magicbox.script_template import ScriptTemplate
from lib.os.os_client import OSClient
from lib.mysql.mysql_client import MySQLClient

class HDFSOverviewCollector(ScriptTemplate):
    """HDFS NameNode状态与存储用量一体化采集脚本"""
    def __init__(self, env: Optional[str] = None, cluster_name: str = None, ns_name: str = None):
        super().__init__(env=env)
        self.cluster_name = cluster_name
        self.ns_name = ns_name
        self.os_client = OSClient({'timeout': 300, 'work_dir': '/tmp'})
        try:
            self.mysql_client = MySQLClient(self.get_component_config("mysql"))
            self.mysql_client.set_logger(self.logger)
            self.mysql_available = True
        except Exception as e:
            self.logger.warning(f"MySQL连接失败，将使用模拟模式: {str(e)}")
            self.mysql_available = False
            
        # 初始化Kerberos客户端（如果需要）
        self.kerberos_client = None
        self.enable_kerberos = False
        try:
            hdfs_config = self.get_component_config("hdfs")
            self.enable_kerberos = hdfs_config.get('enable_kerberos', False)
            
            if self.enable_kerberos:
                from lib.kerberos.kerberos_client import KerberosClient
                kerberos_config = hdfs_config.get('kerberos', {})
                if kerberos_config:
                    self.kerberos_client = KerberosClient(kerberos_config, self.os_client)
                    self.kerberos_client.set_logger(self.logger)
                else:
                    self.logger.warning("启用了Kerberos但未提供Kerberos配置")
                    self.enable_kerberos = False
        except Exception as e:
            self.logger.warning(f"初始化Kerberos客户端失败: {str(e)}")
            self.enable_kerberos = False

    def _ensure_authenticated(self) -> bool:
        """
        确保Kerberos认证有效（如果启用）
        
        Returns:
            bool: 认证是否成功
        """
        if not self.enable_kerberos:
            return True
            
        if not self.kerberos_client:
            self.logger.error("启用了Kerberos但没有Kerberos客户端")
            return False
            
        return self.kerberos_client.ensure_authenticated()

    def collect_namenode_status(self, report: str, collect_time: str) -> Dict[str, Any]:
        """解析hdfs dfsadmin -report输出，采集NameNode整体状态"""
        # 初始化所有必需字段为默认值，确保数据库 NOT NULL 约束
        result = {
            'cluster_name': self.cluster_name,
            'ns_name': self.ns_name,
            'collect_time': collect_time,
            'live_datanodes': 0,
            'dead_datanodes': 0,
            'bad_blocks': 0,
            'blocks': 0,
            'configured_capacity': 0,
            'dfs_used': 0,
            'dfs_remaining': 0
        }
        
        try:
            datanode_match = re.search(r'Live datanodes\s*\((\d+)\):', report)
            if datanode_match:
                result['live_datanodes'] = int(datanode_match.group(1))
            deadnode_match = re.search(r'Dead datanodes\s*\((\d+)\):', report)
            if deadnode_match:
                result['dead_datanodes'] = int(deadnode_match.group(1))
            bad_disk_match = re.search(r'Number of bad blocks:\s*(\d+)', report)
            if bad_disk_match:
                result['bad_blocks'] = int(bad_disk_match.group(1))
            block_match = re.search(r'Blocks:\s*(\d+)', report)
            if block_match:
                result['blocks'] = int(block_match.group(1))
            cap_match = re.search(r'Configured Capacity:\s*(\d+)', report)
            if cap_match:
                result['configured_capacity'] = int(cap_match.group(1))
            used_match = re.search(r'DFS Used:\s*(\d+)', report)
            if used_match:
                result['dfs_used'] = int(used_match.group(1))
            rem_match = re.search(r'DFS Remaining:\s*(\d+)', report)
            if rem_match:
                result['dfs_remaining'] = int(rem_match.group(1))
                
            self.logger.debug(f"成功解析NameNode状态: 活跃节点={result['live_datanodes']}, 死节点={result['dead_datanodes']}")
            
        except Exception as e:
            self.logger.error(f"解析NameNode状态失败: {str(e)}")
            self.logger.debug(f"报告内容前500字符: {report[:500]}...")
            
        return result

    def collect_storage_usage(self, collect_time: str) -> Dict[str, Any]:
        """采集HDFS存储用量（含目录/文件数、使用率等）"""
        info = {
            'cluster_name': self.cluster_name,
            'ns_name': self.ns_name,
            'collect_time': collect_time,
            'total_capacity': 0,
            'used_capacity': 0,
            'remaining_capacity': 0,
            'used_percentage': 0,
            'total_dirs': 0,
            'total_files': 0
        }
        # 先用hdfs dfsadmin -report采集容量
        command = "hdfs dfsadmin -report"
        
        # 确保Kerberos认证有效
        if not self._ensure_authenticated():
            self.logger.error("Kerberos认证失败")
            return info
        
        # 设置环境变量
        env = {}
        if self.enable_kerberos and self.kerberos_client:
            env.update(self.kerberos_client.get_hadoop_env())
        
        return_code, output, stderr = self.os_client.execute_command(command, env=env)
        if return_code != 0:
            self.logger.error(f"hdfs dfsadmin -report 执行失败，返回码: {return_code}, 错误: {stderr}")
            return info
            
        try:
            total_match = re.search(r'Configured Capacity:\s+(\d+)', output)
            used_match = re.search(r'DFS Used:\s+(\d+)', output)
            remaining_match = re.search(r'DFS Remaining:\s+(\d+)', output)
            if total_match and used_match and remaining_match:
                info["total_capacity"] = int(total_match.group(1))
                info["used_capacity"] = int(used_match.group(1))
                info["remaining_capacity"] = int(remaining_match.group(1))
                if info["total_capacity"] > 0:
                    info["used_percentage"] = round(
                        info["used_capacity"] / info["total_capacity"] * 100, 2
                    )
                self.logger.debug(f"成功解析HDFS容量信息: 总容量={info['total_capacity']}, 已用={info['used_capacity']}, 剩余={info['remaining_capacity']}")
            else:
                self.logger.warning(f"无法从 hdfs dfsadmin -report 输出中解析容量信息，输出长度: {len(output)}")
                self.logger.debug(f"hdfs dfsadmin -report 输出内容: {output[:500]}...")  # 只记录前500字符
        except Exception as e:
            self.logger.error(f"解析 hdfs dfsadmin -report 输出失败: {str(e)}")
        # 采集目录和文件数
        count_command = "hdfs dfs -count /"
        return_code, count_output, count_stderr = self.os_client.execute_command(count_command, env=env)
        if return_code == 0 and count_output.strip():
            try:
                # 解析 hdfs dfs -count 输出，格式通常为: DIR_COUNT FILE_COUNT CONTENT_SIZE PATH
                # 但可能包含额外的 JVM 参数或警告信息，需要找到有效的数据行
                lines = count_output.strip().split('\n')
                valid_line = None
                
                # 查找包含有效数据的行（应该以数字开头）
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('-') and not line.startswith('WARNING'):
                        parts = line.split()
                        if len(parts) >= 3:
                            # 检查前两个部分是否为数字
                            try:
                                int(parts[0])  # 目录数
                                int(parts[1])  # 文件数
                                valid_line = line
                                break
                            except ValueError:
                                continue
                
                if valid_line:
                    parts = valid_line.split()
                    info["total_dirs"] = int(parts[0])
                    info["total_files"] = int(parts[1])
                    self.logger.debug(f"成功解析目录和文件数: 目录={parts[0]}, 文件={parts[1]}")
                else:
                    self.logger.warning(f"无法从 hdfs dfs -count 输出中解析有效数据: {count_output}")
                    
            except Exception as e:
                self.logger.error(f"解析 hdfs dfs -count 输出失败: {str(e)}, 输出内容: {count_output}")
        else:
            self.logger.warning(f"hdfs dfs -count 命令执行失败，返回码: {return_code}, 错误: {count_stderr}")
        return info

    def save_namenode_status(self, data: Dict[str, Any]):
        if not self.mysql_available:
            self.logger.warning("MySQL不可用，跳过NameNode状态入库。")
            return
        table = "hdfs_namenode_status"
        data['insert_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        sql = f"""
        INSERT INTO {table} (cluster_name, ns_name, collect_time, insert_time, live_datanodes, dead_datanodes, bad_blocks, blocks, configured_capacity, dfs_used, dfs_remaining)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            live_datanodes=VALUES(live_datanodes),
            dead_datanodes=VALUES(dead_datanodes),
            bad_blocks=VALUES(bad_blocks),
            blocks=VALUES(blocks),
            configured_capacity=VALUES(configured_capacity),
            dfs_used=VALUES(dfs_used),
            dfs_remaining=VALUES(dfs_remaining),
            insert_time=VALUES(insert_time)
        """
        values = (
            data.get('cluster_name', ''),
            data.get('ns_name', ''),
            data.get('collect_time', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            data.get('insert_time', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            data.get('live_datanodes', 0),
            data.get('dead_datanodes', 0),
            data.get('bad_blocks', 0),
            data.get('blocks', 0),
            data.get('configured_capacity', 0),
            data.get('dfs_used', 0),
            data.get('dfs_remaining', 0)
        )
        try:
            self.mysql_client.execute_update(sql, values)
            self.logger.info(f"HDFS NameNode状态已入库: {values}")
        except Exception as e:
            self.logger.error(f"NameNode状态入库失败: {str(e)}")

    def save_storage_usage(self, data: Dict[str, Any]):
        if not self.mysql_available:
            self.logger.warning("MySQL不可用，跳过存储用量入库。")
            return
        table = "hdfs_cluster_storage"
        data['insert_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        sql = f"""
        INSERT INTO {table} (cluster_name, ns_name, collect_time, insert_time, total_capacity, used_capacity, remaining_capacity, used_percentage, total_dirs, total_files)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            total_capacity=VALUES(total_capacity),
            used_capacity=VALUES(used_capacity),
            remaining_capacity=VALUES(remaining_capacity),
            used_percentage=VALUES(used_percentage),
            total_dirs=VALUES(total_dirs),
            total_files=VALUES(total_files),
            insert_time=VALUES(insert_time)
        """
        values = (
            data.get('cluster_name', ''),
            data.get('ns_name', ''),
            data.get('collect_time', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            data.get('insert_time', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            data.get('total_capacity', 0),
            data.get('used_capacity', 0),
            data.get('remaining_capacity', 0),
            data.get('used_percentage', 0.0),
            data.get('total_dirs', 0),
            data.get('total_files', 0)
        )
        try:
            self.mysql_client.execute_update(sql, values)
            self.logger.info(f"HDFS存储用量已入库: {values}")
        except Exception as e:
            self.logger.error(f"存储用量入库失败: {str(e)}")

    def run(self):
        self.logger.info(f"开始采集HDFS NameNode状态和存储用量: cluster={self.cluster_name}, ns={self.ns_name}")
        # 采集时间为采集命令前的时间
        collect_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        command = "hdfs dfsadmin -report"
        
        # 确保Kerberos认证有效
        if not self._ensure_authenticated():
            self.logger.error("Kerberos认证失败")
            return
        
        # 设置环境变量
        env = {}
        if self.enable_kerberos and self.kerberos_client:
            env.update(self.kerberos_client.get_hadoop_env())
        
        return_code, output, stderr = self.os_client.execute_command(command, env=env)
        if return_code != 0:
            self.logger.error(f"hdfs dfsadmin -report 执行失败，返回码: {return_code}, 错误: {stderr}")
            return
        namenode_status = self.collect_namenode_status(output, collect_time)
        self.save_namenode_status(namenode_status)
        storage_usage = self.collect_storage_usage(collect_time)
        self.save_storage_usage(storage_usage)
        self.logger.info("HDFS NameNode状态和存储用量采集完成")


def parse_args():
    parser = argparse.ArgumentParser(description="采集HDFS NameNode整体状态和存储用量")
    parser.add_argument('--env', type=str, help='环境名称 (dev/test/prod)')
    parser.add_argument('--cluster_name', type=str, required=True, help='集群名称')
    parser.add_argument('--ns_name', type=str, required=True, help='命名空间名称')
    return parser.parse_args()


def main():
    args = parse_args()
    collector = HDFSOverviewCollector(env=args.env, cluster_name=args.cluster_name, ns_name=args.ns_name)
    collector.run()

if __name__ == "__main__":
    main() 