#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import logging
import sys
import time
from typing import Any, Dict, Optional
import inspect
import signal
from datetime import datetime, timedelta
import os
import re

from magicbox.script_template import ScriptTemplate
from lib.hive.hive_client import HiveClient
from lib.os.os_client import OSClient

class HiveMonitor(ScriptTemplate):
    """Hive 监控脚本，用于监控各种 Hive 操作"""
    
    def __init__(self, env: Optional[str] = None, execution_engine: Optional[str] = None):
        """
        初始化 Hive 监控脚本
        
        Args:
            env: 环境名称 (dev/test/prod)，如果为None则使用默认环境
            execution_engine: Hive执行引擎 (mr/tez/spark)，如果为None则使用默认引擎
        """
        super().__init__(env=env)
        
        # 设置执行引擎
        self.execution_engine = execution_engine
        
        # 创建共享的OSClient
        self.os_client = OSClient({
            'timeout': 300,
            'work_dir': '/tmp'
        })
        
        # 创建Kerberos客户端（如果需要）
        self.kerberos_client = None
        try:
            hive_config = self.get_component_config("hive")
            enable_kerberos = hive_config.get('enable_kerberos', False)
            
            if enable_kerberos:
                from lib.kerberos.kerberos_client import KerberosClient
                kerberos_config = hive_config.get('kerberos', {})
                if kerberos_config:
                    self.kerberos_client = KerberosClient(kerberos_config, self.os_client)
                    self.kerberos_client.set_logger(self.logger)
        except Exception as e:
            self.logger.warning(f"初始化Kerberos客户端失败: {str(e)}")
        
        # 创建Hive客户端
        self.hive_client = HiveClient(
            self.get_component_config("hive"),
            os_client=self.os_client,
            kerberos_client=self.kerberos_client
        )
        self.hive_client.set_logger(self.logger)
        

        
    def _execute_hive_command(self, sql: str) -> tuple:
        """
        执行 Hive 命令
        
        Args:
            sql: 要执行的 SQL 语句
            
        Returns:
            tuple: (return_code, output)
        """
        try:
            # 如果指定了执行引擎，将设置命令和实际SQL合并执行
            if self.execution_engine:
                engine_sql = f"SET hive.execution.engine={self.execution_engine};"
                combined_sql = f"{engine_sql}\n{sql}"
                self.logger.info(f"设置Hive执行引擎为 {self.execution_engine}")
                return self.hive_client.execute_sql(combined_sql)
            else:
                return self.hive_client.execute_sql(sql)
        except Exception as e:
            self.logger.error(f"执行 Hive 命令时发生错误: {str(e)}")
            raise
    
    def check_execution_engine(self, **kwargs) -> Dict[str, Any]:
        """
        检查当前Hive执行引擎设置
        
        Returns:
            Dict[str, Any]: 执行结果
        """
        self.logger.info("开始检查Hive执行引擎")
        try:
            # 查询当前执行引擎
            engine_sql = "SET hive.execution.engine"
            
            # 如果配置了执行引擎，直接使用HiveClient执行，避免重复设置
            if self.execution_engine:
                combined_sql = f"SET hive.execution.engine={self.execution_engine};\n{engine_sql}"
                self.logger.info(f"检查执行引擎设置 (配置为: {self.execution_engine})")
                _, output = self.hive_client.execute_sql(combined_sql)
            else:
                _, output = self.hive_client.execute_sql(engine_sql)
            
            # 解析输出获取当前引擎
            current_engine = "unknown"
            for line in output.strip().split('\n'):
                if 'hive.execution.engine' in line and '=' in line:
                    current_engine = line.split('=')[-1].strip()
                    break
            
            result = {
                "current_engine": current_engine,
                "configured_engine": self.execution_engine or "default"
            }
            
            self.logger.info(f"Hive执行引擎信息: {result}")
            return {"status": "success", "engine_info": result}
        except Exception as e:
            self.logger.error(f"检查Hive执行引擎失败: {str(e)}")
            raise
            
    def create_test_table(self, **kwargs) -> Dict[str, Any]:
        """
        创建测试表
        
        Returns:
            Dict[str, Any]: 执行结果
        """
        self.logger.info("开始创建测试表")
        try:
            # 创建测试表
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS test_monitor (
                id INT,
                name STRING,
                create_time TIMESTAMP,
                value DOUBLE,
                status STRING
            )
            PARTITIONED BY (dt STRING)
            STORED AS ORC
            TBLPROPERTIES ('orc.compress'='SNAPPY')
            """
            
            self._execute_hive_command(create_table_sql)
            self.logger.info("测试表创建成功")
            
            return {"status": "success", "message": "测试表创建成功"}
        except Exception as e:
            self.logger.error(f"创建测试表失败: {str(e)}")
            raise
            
    def drop_test_table(self, **kwargs) -> Dict[str, Any]:
        """
        删除测试表
        
        Returns:
            Dict[str, Any]: 执行结果
        """
        self.logger.info("开始删除测试表")
        try:
            # 删除测试表
            drop_table_sql = "DROP TABLE IF EXISTS test_monitor"
            
            self._execute_hive_command(drop_table_sql)
            self.logger.info("测试表删除成功")
            
            return {"status": "success", "message": "测试表删除成功"}
        except Exception as e:
            self.logger.error(f"删除测试表失败: {str(e)}")
            raise
            
    def add_test_partition(self, **kwargs) -> Dict[str, Any]:
        """
        添加测试分区
        
        Returns:
            Dict[str, Any]: 执行结果
        """
        self.logger.info("开始添加测试分区")
        try:
            # 添加测试分区
            current_date = datetime.now().strftime('%Y%m%d')
            add_partition_sql = f"""
            ALTER TABLE test_monitor ADD IF NOT EXISTS
            PARTITION (dt='{current_date}')
            """
            
            self._execute_hive_command(add_partition_sql)
            self.logger.info(f"测试分区 {current_date} 添加成功")
            
            return {"status": "success", "message": f"测试分区 {current_date} 添加成功"}
        except Exception as e:
            self.logger.error(f"添加测试分区失败: {str(e)}")
            raise
            
    def load_test_data(self, **kwargs) -> Dict[str, Any]:
        """
        加载测试数据
        
        Returns:
            Dict[str, Any]: 执行结果
        """
        self.logger.info("开始加载测试数据")
        try:
            # 加载测试数据
            current_date = datetime.now().strftime('%Y%m%d')
            load_data_sql = f"""
            INSERT INTO TABLE test_monitor PARTITION (dt='{current_date}')
            VALUES 
            (1, 'test1', CURRENT_TIMESTAMP, 100.5, 'active'),
            (2, 'test2', CURRENT_TIMESTAMP, 200.3, 'inactive'),
            (3, 'test3', CURRENT_TIMESTAMP, 300.7, 'active')
            """
            
            self._execute_hive_command(load_data_sql)
            self.logger.info("测试数据加载成功")
            
            return {"status": "success", "message": "测试数据加载成功"}
        except Exception as e:
            self.logger.error(f"加载测试数据失败: {str(e)}")
            raise
            
    def count_test_data(self, **kwargs) -> Dict[str, Any]:
        """
        统计测试数据
        
        Returns:
            Dict[str, Any]: 执行结果
        """
        self.logger.info("开始统计测试数据")
        try:
            # 统计测试数据
            count_sql = "SELECT COUNT(*) FROM test_monitor"
            
            _, output = self._execute_hive_command(count_sql)
            count = output.strip().split('\n')[-1]  # 获取最后一行结果
            
            self.logger.info(f"测试数据统计结果: {count}")
            
            return {"status": "success", "count": count}
        except Exception as e:
            self.logger.error(f"统计测试数据失败: {str(e)}")
            raise
            
    def check_table_storage(self, **kwargs) -> Dict[str, Any]:
        """检查表存储格式和压缩方式"""
        self.logger.info("开始检查表存储格式")
        try:
            check_sql = """
            DESCRIBE FORMATTED test_monitor
            """
            _, output = self._execute_hive_command(check_sql)
            
            # 解析输出
            storage_format = re.search(r'InputFormat:\s+(.*)', output)
            compression = re.search(r'Compressed:\s+(.*)', output)
            
            result = {
                "storage_format": storage_format.group(1) if storage_format else "Unknown",
                "compression": compression.group(1) if compression else "Unknown"
            }
            
            self.logger.info(f"表存储信息: {result}")
            return {"status": "success", "storage_info": result}
        except Exception as e:
            self.logger.error(f"检查表存储格式失败: {str(e)}")
            raise

    def check_partition_health(self, **kwargs) -> Dict[str, Any]:
        """检查分区健康状态"""
        self.logger.info("开始检查分区健康状态")
        try:
            check_sql = """
            SHOW PARTITIONS test_monitor
            """
            _, output = self._execute_hive_command(check_sql)
            
            partitions = [line.strip() for line in output.strip().split('\n') if line.strip()]
            
            # 检查分区数据
            partition_stats = {}
            for partition in partitions:
                dt = partition.split('=')[1]
                count_sql = f"SELECT COUNT(*) FROM test_monitor WHERE dt='{dt}'"
                _, count_output = self._execute_hive_command(count_sql)
                count = count_output.strip().split('\n')[-1]
                partition_stats[dt] = int(count)
            
            self.logger.info(f"分区健康状态: {partition_stats}")
            return {"status": "success", "partition_stats": partition_stats}
        except Exception as e:
            self.logger.error(f"检查分区健康状态失败: {str(e)}")
            raise

    def check_data_quality(self, **kwargs) -> Dict[str, Any]:
        """检查数据质量"""
        self.logger.info("开始检查数据质量")
        try:
            quality_checks = {
                "null_check": """
                SELECT COUNT(*) 
                FROM test_monitor 
                WHERE id IS NULL OR name IS NULL OR create_time IS NULL
                """,
                "value_range_check": """
                SELECT COUNT(*) 
                FROM test_monitor 
                WHERE value < 0 OR value > 1000
                """,
                "status_check": """
                SELECT COUNT(*) 
                FROM test_monitor
                WHERE status NOT IN ('active', 'inactive')
                """
            }
            
            results = {}
            for check_name, sql in quality_checks.items():
                _, output = self._execute_hive_command(sql)
                count = output.strip().split('\n')[-1]
                results[check_name] = int(count)
            
            self.logger.info(f"数据质量检查结果: {results}")
            return {"status": "success", "quality_checks": results}
        except Exception as e:
            self.logger.error(f"检查数据质量失败: {str(e)}")
            raise

    def check_query_performance(self, **kwargs) -> Dict[str, Any]:
        """检查查询性能"""
        self.logger.info("开始检查查询性能")
        try:
            # 执行测试查询
            test_queries = {
                "simple_count": "SELECT COUNT(*) FROM test_monitor",
                "partition_scan": "SELECT * FROM test_monitor WHERE dt='20240101'",
                "value_aggregation": "SELECT AVG(value) FROM test_monitor"
            }
            
            results = {}
            for query_name, sql in test_queries.items():
                start_time = time.time()
                self._execute_hive_command(sql)
                execution_time = time.time() - start_time
                results[query_name] = execution_time
            
            self.logger.info(f"查询性能测试结果: {results}")
            return {"status": "success", "performance_metrics": results}
        except Exception as e:
            self.logger.error(f"检查查询性能失败: {str(e)}")
            raise

    def check_table_metadata(self, **kwargs) -> Dict[str, Any]:
        """检查表元数据"""
        self.logger.info("开始检查表元数据")
        try:
            # 获取表信息
            table_info_sql = """
            DESCRIBE FORMATTED test_monitor
            """
            _, output = self._execute_hive_command(table_info_sql)
            
            # 解析输出
            table_type = re.search(r'Table Type:\s+(.*)', output)
            location = re.search(r'Location:\s+(.*)', output)
            owner = re.search(r'Owner:\s+(.*)', output)
            
            result = {
                "table_type": table_type.group(1) if table_type else "Unknown",
                "location": location.group(1) if location else "Unknown",
                "owner": owner.group(1) if owner else "Unknown"
            }
            
            self.logger.info(f"表元数据信息: {result}")
            return {"status": "success", "metadata": result}
        except Exception as e:
            self.logger.error(f"检查表元数据失败: {str(e)}")
            raise

    def run_all(self, **kwargs) -> Dict[str, Any]:
        """运行所有检查"""
        self.logger.info("开始运行所有检查")
        try:
            results = {}
            
            # 运行各个检查
            checks = [
                "check_execution_engine",
                "create_test_table",
                "add_test_partition",
                "load_test_data",
                "count_test_data",
                "check_table_storage",
                #"check_partition_health",
                #"check_data_quality",
                #"check_query_performance",
                "check_table_metadata",
                "drop_test_table"
            ]
            
            for check in checks:
                try:
                    result = getattr(self, check)()
                    results[check] = result
                except Exception as e:
                    self.logger.error(f"执行 {check} 失败: {str(e)}")
                    results[check] = {"status": "error", "message": str(e)}
            
            self.logger.info("所有检查完成")
            return {"status": "success", "results": results}
        except Exception as e:
            self.logger.error(f"运行所有检查失败: {str(e)}")
            raise

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='Hive 监控脚本')
    parser.add_argument('--run', type=str, required=True, metavar='FUNCTION',
                      help='要执行的函数名 (例如: --run=check_table_storage)')
    parser.add_argument('--env', type=str, choices=['dev', 'test', 'prod'],
                      help='环境名称 (dev/test/prod)')
    parser.add_argument('--engine', type=str, choices=['mr', 'tez', 'spark'],
                      help='Hive执行引擎 (mr/tez/spark)')
    parser.add_argument('--debug', action='store_true',
                      help='启用调试模式')
    
    return parser.parse_args()

def main():
    """主函数"""
    def signal_handler(signum, frame):
        print("\n正在优雅退出...")
        sys.exit(0)
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    args = parse_args()
    
    # 创建脚本实例
    script = HiveMonitor(env=args.env, execution_engine=args.engine)
    
    # 如果启用调试模式，设置日志级别为DEBUG
    if args.debug:
        script.logger.setLevel(logging.DEBUG)
    
    try:
        # 执行指定的函数
        result = script.run_function(args.run)
        script.logger.info(f"执行结果: {result}")
    except Exception as e:
        script.logger.error(f"执行失败: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main() 