#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import logging
import sys
import time
from typing import Optional, Dict, Any
import inspect
import signal
import re
from datetime import datetime
import os

from magicbox.script_template import ScriptTemplate
from lib.os.os_client import OSClient
from lib.mysql.mysql_client import MySQLClient

class HiveStorageCollector(ScriptTemplate):
    """Hive 存储数据采集脚本，用于采集Hive数据库存储使用情况"""
    
    def __init__(self, env: Optional[str] = None):
        """
        初始化 Hive 存储数据采集脚本
        
        Args:
            env: 环境名称 (dev/test/prod)，如果为None则使用默认环境
        """
        super().__init__(env=env)
        
        # 记录环境信息
        self.logger.info(f"初始化 HiveStorageCollector，使用环境: {self.env}")
        
        # 创建共享的OSClient
        self.os_client = OSClient({
            'timeout': 300,
            'work_dir': '/tmp'
        })
        
        # 创建MySQL客户端（如果配置可用）
        try:
            self.mysql_client = MySQLClient(
                self.get_component_config("mysql")
            )
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
            
        # 获取 Hive 仓库目录配置
        try:
            hive_config = self.get_component_config("hive")
            if hive_config:
                self.warehouse_dir = hive_config.get('warehouse_dir', '/user/hive/warehouse')
                # 向后兼容：如果直接读取失败，尝试从 common 节点读取
                if self.warehouse_dir == '/user/hive/warehouse' and 'common' in hive_config:
                    self.warehouse_dir = hive_config.get('common', {}).get('warehouse_dir', '/user/hive/warehouse')
            else:
                self.warehouse_dir = '/user/hive/warehouse'
            self.logger.info(f"使用 Hive 仓库目录: {self.warehouse_dir}")
        except Exception as e:
            self.warehouse_dir = '/user/hive/warehouse'
            self.logger.warning(f"获取 Hive 配置失败，使用默认仓库目录: {self.warehouse_dir}, 错误: {str(e)}")
        
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
            
    def _execute_hdfs_command(self, command: str) -> tuple:
        """
        执行 HDFS 命令
        
        Args:
            command: 要执行的 HDFS 命令
            
        Returns:
            tuple: (return_code, output)
        """
        try:
            # 确保Kerberos认证有效
            if not self._ensure_authenticated():
                raise Exception("Kerberos认证失败")
            
            # 设置环境变量
            env = {}
            if self.enable_kerberos and self.kerberos_client:
                env.update(self.kerberos_client.get_hadoop_env())
            
            return_code, stdout, stderr = self.os_client.execute_command(command, env=env)
            # 合并标准输出和标准错误
            output = stdout + stderr if stderr else stdout
            return return_code, output
        except Exception as e:
            self.logger.error(f"执行 HDFS 命令时发生错误: {str(e)}")
            raise
            
    def collect_hive_db_storage(self, cluster_name: str, ns_name: str) -> Dict[str, Any]:
        """
        采集各Hive数据库的存储大小
        
        Args:
            cluster_name: 集群名称
            ns_name: 命名空间名称
            
        Returns:
            Dict[str, Any]: 采集结果
        """
        self.logger.info("开始采集Hive数据库存储使用情况")
        try:
            # 记录采集开始时间
            collect_time = datetime.now()
            
            # 获取所有Hive数据库
            command = f"hdfs dfs -ls {self.warehouse_dir}"
            return_code, output = self._execute_hdfs_command(command)
            
            if return_code != 0:
                raise Exception(f"HDFS命令执行失败，返回码: {return_code}, 输出: {output}")
                
            # 解析数据库列表
            db_list = []
            lines = output.strip().split('\n')
            
            for line in lines:
                line = line.strip()
                # 跳过空行和 JVM 参数行
                if not line or line.startswith('-D') or line.startswith('WARNING'):
                    continue
                    
                parts = line.split()
                if len(parts) >= 8:  # 确保行包含足够的信息（HDFS ls 格式）
                    full_path = parts[-1]
                    db_name = full_path.split('/')[-1]
                    
                    # 只识别以 .db 结尾的 Hive 数据库
                    if db_name.endswith('.db'):
                        db_list.append(db_name)
            
            self.logger.info(f"找到 {len(db_list)} 个 Hive 数据库: {db_list}")
            
            # 采集每个数据库的存储信息
            db_storage_info = []
            for db_name in db_list:
                count_command = f"hdfs dfs -count {self.warehouse_dir}/{db_name}"
                return_code, count_output = self._execute_hdfs_command(count_command)
                
                if return_code == 0 and count_output.strip():
                    try:
                        # 解析 hdfs dfs -count 输出，格式通常为: DIR_COUNT FILE_COUNT CONTENT_SIZE PATHNAME
                        # 但可能包含额外的 JVM 参数或警告信息，需要找到有效的数据行
                        lines = count_output.strip().split('\n')
                        valid_line = None
                        
                        # 查找包含有效数据的行（应该以数字开头）
                        for line in lines:
                            line = line.strip()
                            if line and not line.startswith('-') and not line.startswith('WARNING'):
                                parts = line.split()
                                if len(parts) >= 3:
                                    # 检查前三个部分是否为数字
                                    try:
                                        int(parts[0])  # 目录数
                                        int(parts[1])  # 文件数
                                        int(parts[2])  # 存储大小
                                        valid_line = line
                                        break
                                    except ValueError:
                                        continue
                        
                        if valid_line:
                            parts = valid_line.split()
                            info = {
                                "cluster_name": cluster_name,
                                "ns_name": ns_name,
                                "db_name": db_name,
                                "storage_size": int(parts[2]),
                                "dir_count": int(parts[0]),
                                "file_count": int(parts[1]),
                                "collect_time": collect_time.strftime('%Y-%m-%d %H:%M:%S')
                            }
                            db_storage_info.append(info)
                            self.logger.info(f"已采集数据库 {db_name}: 存储大小 {parts[2]} 字节")
                        else:
                            self.logger.warning(f"无法从 hdfs dfs -count 输出中解析数据库 {db_name} 的有效数据: {count_output}")
                            continue
                            
                    except Exception as e:
                        self.logger.error(f"解析数据库 {db_name} 的 hdfs dfs -count 输出失败: {str(e)}, 输出内容: {count_output}")
                        continue
                else:
                    self.logger.warning(f"数据库 {db_name} 采集失败，返回码: {return_code}")
            
            self.logger.info(f"成功采集 {len(db_storage_info)} 个数据库的存储信息")
            
            # 记录插入时间
            insert_time = datetime.now()
            
            # 将所有数据插入MySQL
            for info in db_storage_info:
                info["insert_time"] = insert_time.strftime('%Y-%m-%d %H:%M:%S')
                self._save_to_mysql("hive_db_storage", info)
            
            self.logger.info("Hive数据库存储信息采集完成")
            return {"status": "success", "db_storage_info": db_storage_info}
            
        except Exception as e:
            self.logger.error(f"采集Hive数据库存储信息失败: {str(e)}")
            raise
            
    def _save_to_mysql(self, table_name: str, data: Dict[str, Any]) -> None:
        """
        将数据保存到MySQL数据库
        
        Args:
            table_name: 表名
            data: 要保存的数据
        """
        if not self.mysql_available:
            self.logger.info(f"MySQL不可用，跳过保存到表 {table_name}: {data}")
            return
            
        try:
            columns = ", ".join(data.keys())
            placeholders = ", ".join(["%s"] * len(data))
            values = list(data.values())
            
            sql = f"""
            INSERT INTO {table_name} ({columns})
            VALUES ({placeholders})
            """
            
            self.mysql_client.execute_update(sql, values)
            
        except Exception as e:
            self.logger.error(f"保存数据到MySQL失败: {str(e)}")
            raise

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='Hive存储数据采集脚本')
    parser.add_argument('--env', type=str, help='环境名称 (dev/test/prod)')
    parser.add_argument('--cluster_name', type=str, required=True, help='集群名称')
    parser.add_argument('--ns_name', type=str, required=True, help='命名空间名称')
    return parser.parse_args()

def main():
    """主函数"""
    def signal_handler(signum, frame):
        """信号处理函数"""
        print("\n接收到终止信号，正在退出...")
        sys.exit(0)
        
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 解析命令行参数
    args = parse_args()
    
    try:
        # 创建采集器实例
        collector = HiveStorageCollector(env=args.env)
        
        # 执行采集任务
        results = collector.collect_hive_db_storage(args.cluster_name, args.ns_name)
        
        # 打印结果
        print("采集任务执行完成:")
        print(f"Hive数据库存储信息: {results['db_storage_info']}")
        
    except Exception as e:
        print(f"执行失败: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main() 