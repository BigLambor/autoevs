#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import logging
import sys
import time
from typing import Any, Dict, Optional, List
import inspect
import signal
from datetime import datetime
import os
import json

from magicbox.script_template import ScriptTemplate
from lib.os.os_client import OSClient
from lib.mysql.mysql_client import MySQLClient
from lib.yarn.yarn_client import YARNClient

class YARNAppCollector(ScriptTemplate):
    """YARN 应用状态采集脚本，用于采集YARN应用运行状态信息"""
    
    def __init__(self, env: Optional[str] = None):
        """
        初始化 YARN 应用状态采集脚本
        
        Args:
            env: 环境名称 (dev/test/prod)，如果为None则使用默认环境
        """
        super().__init__(env=env)
        
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
            
    def _get_yarn_client(self) -> Optional[YARNClient]:
        """
        获取YARN客户端实例
        
        Returns:
            Optional[YARNClient]: YARN客户端实例
        """
        try:
            config = self.get_component_config("yarn")
            base_url = f"http://{config['resourcemanager']}:{config.get('resourcemanager_port', 8088)}/ws/v1"
            yarn_config = {
                'base_url': base_url,
                'timeout': config.get('timeout', 30),
                'retry_times': 3,
                'retry_interval': 1
            }
            return YARNClient(yarn_config)
        except Exception as e:
            self.logger.warning(f"YARN REST API配置获取失败: {str(e)}")
            return None
            
    def collect_application_stats(self, cluster_name: str) -> Dict[str, Any]:
        """
        采集YARN应用程序状态统计信息
        
        Args:
            cluster_name: 集群名称
            
        Returns:
            Dict[str, Any]: 应用程序状态统计信息
        """
        self.logger.info("开始采集YARN应用程序状态统计信息")
        collect_time = datetime.now()
        yarn_client = self._get_yarn_client()
        
        if not yarn_client:
            error_msg = "无法获取YARN客户端实例"
            self.logger.error(error_msg)
            return {"status": "error", "message": error_msg}
            
        try:
            # 初始化统计数据
            app_stats = {
                "cluster_name": cluster_name,
                "collect_time": collect_time.strftime('%Y-%m-%d %H:%M:%S'),
                "insert_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "active_apps": 0,
                "completed_apps": 0,
                "killed_apps": 0,
                "failed_apps": 0,
                "abnormal_apps": 0,
                "total_submitted_apps": 0
            }
            
            # 获取所有应用程序信息
            apps_response = yarn_client._make_request('GET', 'cluster/apps')
            if apps_response.status_code != 200:
                error_msg = f"获取应用程序信息失败: HTTP {apps_response.status_code}"
                self.logger.error(error_msg)
                return {"status": "error", "message": error_msg}
                
            apps_data = apps_response.json()
            apps = apps_data.get('apps', {}).get('app', [])
            
            # 设置异常判定阈值（30分钟）
            abnormal_threshold = 30 * 60 * 1000  # 毫秒
            
            # 统计各状态应用数量
            for app in apps:
                state = app.get('state', '').upper()
                final_status = app.get('finalStatus', '').upper()
                
                # 更新统计信息
                if state == 'RUNNING':
                    app_stats["active_apps"] += 1
                elif state == 'FINISHED' and final_status == 'SUCCEEDED':
                    app_stats["completed_apps"] += 1
                elif final_status == 'KILLED':
                    app_stats["killed_apps"] += 1
                elif final_status == 'FAILED':
                    app_stats["failed_apps"] += 1
                    
                # 检查是否为异常应用（初始状态停留时间过长）
                if state in ['NEW', 'NEW_SAVING', 'SUBMITTED', 'ACCEPTED']:
                    elapsed_time = app.get('elapsedTime', 0)
                    if elapsed_time > abnormal_threshold:
                        app_stats["abnormal_apps"] += 1
                        
                app_stats["total_submitted_apps"] += 1
                
            # 保存到MySQL
            if self.mysql_available:
                try:
                    self._save_to_mysql("yarn_application_stats", app_stats)
                except Exception as e:
                    self.logger.error(f"保存应用统计数据到MySQL失败: {str(e)}")
                    
            self.logger.info("YARN应用程序状态统计信息采集完成")
            return {"status": "success", "application_stats": app_stats}
            
        except Exception as e:
            error_msg = f"采集应用程序状态统计信息失败: {str(e)}"
            self.logger.error(error_msg)
            return {"status": "error", "message": error_msg}
            
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
    parser = argparse.ArgumentParser(description='YARN应用状态采集脚本')
    parser.add_argument('--env', type=str, help='环境名称 (dev/test/prod)')
    parser.add_argument('--cluster_name', type=str, required=True, help='集群名称')
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
        collector = YARNAppCollector(env=args.env)
        
        # 执行应用状态采集
        results = collector.collect_application_stats(args.cluster_name)
        
        # 打印结果
        print("采集任务执行完成:")
        print(json.dumps(results, indent=2, ensure_ascii=False))
        
    except Exception as e:
        print(f"执行失败: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main() 