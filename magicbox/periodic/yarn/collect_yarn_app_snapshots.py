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

class YARNAppSnapshotCollector(ScriptTemplate):
    """YARN 应用快照采集脚本，用于采集YARN应用运行详细信息"""
    
    def __init__(self, env: Optional[str] = None):
        """
        初始化 YARN 应用快照采集脚本
        
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
            
    def collect_application_snapshots(self, cluster_name: str, states: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        采集YARN应用程序快照信息
        
        Args:
            cluster_name: 集群名称
            states: 要采集的应用状态列表，如果为None则采集所有状态
            
        Returns:
            Dict[str, Any]: 应用程序快照信息
        """
        self.logger.info("开始采集YARN应用程序快照信息")
        collect_time = datetime.now()
        yarn_client = self._get_yarn_client()
        
        if not yarn_client:
            error_msg = "无法获取YARN客户端实例"
            self.logger.error(error_msg)
            return {"status": "error", "message": error_msg}
            
        try:
            # 构建查询参数
            params = {}
            if states:
                params['states'] = ','.join(states)
                
            # 获取应用程序信息
            apps_response = yarn_client._make_request('GET', 'cluster/apps', params=params)
            if apps_response.status_code != 200:
                error_msg = f"获取应用程序信息失败: HTTP {apps_response.status_code}"
                self.logger.error(error_msg)
                return {"status": "error", "message": error_msg}
                
            apps_data = apps_response.json()
            apps = apps_data.get('apps', {}).get('app', [])
            
            snapshots = []
            for app in apps:
                try:
                    # 获取应用详细信息
                    app_id = app.get('id')
                    if not app_id:
                        continue
                        
                    app_detail_response = yarn_client._make_request('GET', f'cluster/apps/{app_id}')
                    if app_detail_response.status_code != 200:
                        self.logger.warning(f"获取应用 {app_id} 详细信息失败: HTTP {app_detail_response.status_code}")
                        continue
                        
                    app_detail = app_detail_response.json().get('app', {})
                    
                    # 构建快照数据
                    snapshot = {
                        "cluster_name": cluster_name,
                        "collect_time": collect_time.strftime('%Y-%m-%d %H:%M:%S'),
                        "insert_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        "application_id": app_id,
                        "application_name": app.get('name', ''),
                        "application_type": app.get('applicationType', ''),
                        "application_tags": app.get('applicationTags', ''),
                        "user": app.get('user', ''),
                        "queue": app.get('queue', ''),
                        "state": app.get('state', ''),
                        "final_status": app.get('finalStatus', ''),
                        "progress": app.get('progress', 0),
                        "tracking_url": app.get('trackingUrl', ''),
                        "submit_time": datetime.fromtimestamp(app.get('startedTime', 0)/1000).strftime('%Y-%m-%d %H:%M:%S') if app.get('startedTime', 0) else None,
                        "start_time": datetime.fromtimestamp(app.get('startedTime', 0)/1000).strftime('%Y-%m-%d %H:%M:%S') if app.get('startedTime', 0) else None,
                        "finish_time": datetime.fromtimestamp(app.get('finishedTime', 0)/1000).strftime('%Y-%m-%d %H:%M:%S') if app.get('finishedTime', 0) else None,
                        "elapsed_time": app.get('elapsedTime', 0),
                        "am_container_logs_url": app_detail.get('amContainerLogs', ''),
                        "allocated_mb": app.get('allocatedMB', 0),
                        "allocated_vcores": app.get('allocatedVCores', 0),
                        "running_containers": app.get('runningContainers', 0),
                        "memory_seconds": app.get('memorySeconds', 0),
                        "vcore_seconds": app.get('vcoreSeconds', 0),
                        "queue_usage_percentage": app.get('queueUsagePercentage', 0),
                        "cluster_usage_percentage": app.get('clusterUsagePercentage', 0),
                        "preempted_resource_mb": app.get('preemptedResourceMB', 0),
                        "preempted_resource_vcores": app.get('preemptedResourceVCores', 0),
                        "num_non_am_container_preempted": app.get('numNonAMContainerPreempted', 0),
                        "num_am_container_preempted": app.get('numAMContainerPreempted', 0),
                        "diagnostics": app.get('diagnostics', '')[:1000]  # 限制诊断信息长度
                    }
                    
                    # 保存到MySQL
                    if self.mysql_available:
                        try:
                            self._save_to_mysql("yarn_application_snapshots", snapshot)
                        except Exception as e:
                            self.logger.error(f"保存应用 {app_id} 快照数据到MySQL失败: {str(e)}")
                            
                    snapshots.append(snapshot)
                    
                except Exception as e:
                    self.logger.error(f"处理应用快照数据失败: {str(e)}")
                    continue
                    
            self.logger.info(f"YARN应用程序快照信息采集完成，共采集 {len(snapshots)} 个应用")
            return {
                "status": "success",
                "snapshots_count": len(snapshots),
                "snapshots": snapshots
            }
            
        except Exception as e:
            error_msg = f"采集应用程序快照信息失败: {str(e)}"
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
            self.logger.info(f"MySQL不可用，跳过保存到表 {table_name}")
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
    parser = argparse.ArgumentParser(description='YARN应用快照采集脚本')
    parser.add_argument('--env', type=str, help='环境名称 (dev/test/prod)')
    parser.add_argument('--cluster_name', type=str, required=True, help='集群名称')
    parser.add_argument('--states', type=str, help='要采集的应用状态，多个状态用逗号分隔 (NEW,NEW_SAVING,SUBMITTED,ACCEPTED,RUNNING,FINISHED,FAILED,KILLED)')
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
        collector = YARNAppSnapshotCollector(env=args.env)
        
        # 解析状态列表
        states = args.states.split(',') if args.states else None
        
        # 执行应用快照采集
        results = collector.collect_application_snapshots(args.cluster_name, states)
        
        # 打印结果
        print("采集任务执行完成:")
        print(json.dumps(results, indent=2, ensure_ascii=False))
        
    except Exception as e:
        print(f"执行失败: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main() 