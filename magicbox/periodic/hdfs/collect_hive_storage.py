#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import logging
import sys
import time
from typing import Any, Dict, Optional
import inspect
import signal
from datetime import datetime
import os
import re

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
        
    def _execute_hdfs_command(self, command: str) -> tuple:
        """
        执行 HDFS 命令
        
        Args:
            command: 要执行的 HDFS 命令
            
        Returns:
            tuple: (return_code, output)
        """
        try:
            return_code, stdout, stderr = self.os_client.execute_command(command)
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
            command = "hdfs dfs -ls /user/hive/warehouse"
            return_code, output = self._execute_hdfs_command(command)
            
            if return_code != 0:
                raise Exception(f"HDFS命令执行失败，返回码: {return_code}")
                
            # 解析数据库列表
            db_list = []
            for line in output.strip().split('\n'):
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 8:  # 确保行包含足够的信息
                        db_name = parts[-1].split('/')[-1]
                        if db_name and not db_name.startswith('.'):
                            db_list.append(db_name)
            
            # 采集每个数据库的存储信息
            db_storage_info = []
            for db_name in db_list:
                # 获取数据库存储大小和文件数量
                count_command = f"hdfs dfs -count /user/hive/warehouse/{db_name}"
                return_code, count_output = self._execute_hdfs_command(count_command)
                
                if return_code == 0 and count_output.strip():
                    # 输出格式: DIR_COUNT FILE_COUNT CONTENT_SIZE PATHNAME
                    parts = count_output.strip().split()
                    if len(parts) >= 3:
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
            self.logger.debug(f"数据已保存到表 {table_name}")
            
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