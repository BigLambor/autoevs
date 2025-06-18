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
import re
import json

from magicbox.script_template import ScriptTemplate
from lib.os.os_client import OSClient
from lib.mysql.mysql_client import MySQLClient
from lib.yarn.yarn_client import YARNClient

class YARNResourceCollector(ScriptTemplate):
    """YARN 资源采集脚本，用于采集YARN管理资源情况"""
    
    def __init__(self, env: Optional[str] = None):
        """
        初始化 YARN 资源采集脚本
        
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
            
    def _execute_yarn_command(self, command: str) -> tuple:
        """
        执行 YARN 命令
        
        Args:
            command: 要执行的 YARN 命令
            
        Returns:
            tuple: (return_code, output)
        """
        try:
            return_code, stdout, stderr = self.os_client.execute_command(command)
            # 合并标准输出和标准错误
            output = stdout + stderr if stderr else stdout
            return return_code, output
        except Exception as e:
            self.logger.error(f"执行 YARN 命令时发生错误: {str(e)}")
            raise
            
    def _get_yarn_client(self) -> Optional[YARNClient]:
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
            
    def collect_yarn_management_resources(self, cluster_name: str) -> Dict[str, Any]:
        self.logger.info("开始采集YARN管理资源情况（REST API优先）")
        collect_time = datetime.now()
        yarn_client = self._get_yarn_client()
        management_resources = {
            "cluster_name": cluster_name,
            "collect_time": collect_time.strftime('%Y-%m-%d %H:%M:%S'),
            "insert_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        if yarn_client:
            try:
                metrics = yarn_client.get_cluster_metrics().get('clusterMetrics', {})
                management_resources.update({
                    "total_nodes": metrics.get("totalNodes", 0),
                    "active_nodes": metrics.get("activeNodes", 0),
                    "decommissioned_nodes": metrics.get("decommissionedNodes", 0),
                    "lost_nodes": metrics.get("lostNodes", 0),
                    "unhealthy_nodes": metrics.get("unhealthyNodes", 0),
                    "total_memory_mb": metrics.get("totalMB", 0),
                    "total_vcores": metrics.get("totalVirtualCores", 0),
                    "used_memory_mb": metrics.get("allocatedMB", 0),
                    "used_vcores": metrics.get("allocatedVirtualCores", 0),
                    "available_memory_mb": metrics.get("availableMB", 0),
                    "available_vcores": metrics.get("availableVirtualCores", 0),
                    "memory_utilization_percent": round(metrics.get("allocatedMB", 0) / metrics.get("totalMB", 1) * 100, 2) if metrics.get("totalMB", 0) else 0,
                    "vcore_utilization_percent": round(metrics.get("allocatedVirtualCores", 0) / metrics.get("totalVirtualCores", 1) * 100, 2) if metrics.get("totalVirtualCores", 0) else 0,
                    "running_containers": metrics.get("runningContainers", 0),
                    "pending_containers": metrics.get("pendingContainers", 0)
                })
            except Exception as e:
                self.logger.warning(f"YARN REST API采集失败，降级为CLI: {str(e)}")
        # CLI补充（如REST API不可用）
        if "total_nodes" not in management_resources or management_resources["total_nodes"] == 0:
            try:
                command = "yarn node -list -all"
                return_code, output = self._execute_yarn_command(command)
                if return_code == 0:
                    node_info = self._parse_node_list(output)
                    management_resources.update(node_info)
            except Exception as e:
                self.logger.warning(f"YARN CLI采集失败: {str(e)}")
        self._save_to_mysql("yarn_management_resources", management_resources)
        self.logger.info("YARN管理资源信息采集完成")
        return {"status": "success", "management_resources": management_resources}
            
    def _parse_node_list(self, output: str) -> Dict[str, Any]:
        """
        解析节点列表输出
        
        Args:
            output: yarn node -list命令的输出
            
        Returns:
            Dict[str, Any]: 解析后的节点信息
        """
        try:
            lines = output.strip().split('\n')
            
            # 初始化统计信息
            stats = {
                "total_nodes": 0,
                "active_nodes": 0,
                "decommissioned_nodes": 0,
                "lost_nodes": 0,
                "unhealthy_nodes": 0,
                "total_memory_mb": 0,
                "total_vcores": 0,
                "used_memory_mb": 0,
                "used_vcores": 0,
                "available_memory_mb": 0,
                "available_vcores": 0,
                "memory_utilization_percent": 0,
                "vcore_utilization_percent": 0,
                "running_containers": 0
            }
            
            # 解析节点信息
            for line in lines:
                if 'Total Nodes:' in line:
                    match = re.search(r'Total Nodes:(\d+)', line)
                    if match:
                        stats["total_nodes"] = int(match.group(1))
                elif 'Active Nodes:' in line:
                    match = re.search(r'Active Nodes:(\d+)', line)
                    if match:
                        stats["active_nodes"] = int(match.group(1))
                elif 'Decommissioned Nodes:' in line:
                    match = re.search(r'Decommissioned Nodes:(\d+)', line)
                    if match:
                        stats["decommissioned_nodes"] = int(match.group(1))
                elif 'Lost Nodes:' in line:
                    match = re.search(r'Lost Nodes:(\d+)', line)
                    if match:
                        stats["lost_nodes"] = int(match.group(1))
                elif 'Unhealthy Nodes:' in line:
                    match = re.search(r'Unhealthy Nodes:(\d+)', line)
                    if match:
                        stats["unhealthy_nodes"] = int(match.group(1))
                elif 'Total Memory:' in line:
                    match = re.search(r'Total Memory:(\d+)', line)
                    if match:
                        stats["total_memory_mb"] = int(match.group(1))
                elif 'Total VCores:' in line:
                    match = re.search(r'Total VCores:(\d+)', line)
                    if match:
                        stats["total_vcores"] = int(match.group(1))
                elif 'Used Memory:' in line:
                    match = re.search(r'Used Memory:(\d+)', line)
                    if match:
                        stats["used_memory_mb"] = int(match.group(1))
                elif 'Used VCores:' in line:
                    match = re.search(r'Used VCores:(\d+)', line)
                    if match:
                        stats["used_vcores"] = int(match.group(1))
                elif 'Running Containers:' in line:
                    match = re.search(r'Running Containers:\s*(\d+)', line)
                    if match:
                        stats["running_containers"] += int(match.group(1))
            
            # 计算可用资源
            stats["available_memory_mb"] = stats["total_memory_mb"] - stats["used_memory_mb"]
            stats["available_vcores"] = stats["total_vcores"] - stats["used_vcores"]
            
            # 计算利用率
            if stats["total_memory_mb"] > 0:
                stats["memory_utilization_percent"] = round(
                    stats["used_memory_mb"] / stats["total_memory_mb"] * 100, 2
                )
            
            if stats["total_vcores"] > 0:
                stats["vcore_utilization_percent"] = round(
                    stats["used_vcores"] / stats["total_vcores"] * 100, 2
                )
            
            return stats
            
        except Exception as e:
            self.logger.error(f"解析节点列表失败: {str(e)}")
            return {
                "total_nodes": 0,
                "active_nodes": 0,
                "decommissioned_nodes": 0,
                "lost_nodes": 0,
                "unhealthy_nodes": 0,
                "total_memory_mb": 0,
                "total_vcores": 0,
                "used_memory_mb": 0,
                "used_vcores": 0,
                "available_memory_mb": 0,
                "available_vcores": 0,
                "memory_utilization_percent": 0,
                "vcore_utilization_percent": 0,
                "running_containers": 0
            }
            
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
    parser = argparse.ArgumentParser(description='YARN资源采集脚本')
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
        collector = YARNResourceCollector(env=args.env)
        
        # 执行资源采集
        results = collector.collect_yarn_management_resources(args.cluster_name)
        
        # 打印结果
        print("采集任务执行完成:")
        print(json.dumps(results, indent=2, ensure_ascii=False))
        
    except Exception as e:
        print(f"执行失败: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main() 