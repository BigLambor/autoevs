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

class YARNQueueCollector(ScriptTemplate):
    """YARN 队列资源采集脚本，用于采集YARN队列资源配置情况"""
    
    def __init__(self, env: Optional[str] = None):
        """
        初始化 YARN 队列资源采集脚本
        
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
            
    def collect_queue_resources(self, cluster_name: str) -> Dict[str, Any]:
        """
        采集YARN队列资源配置情况
        
        Args:
            cluster_name: 集群名称
            
        Returns:
            Dict[str, Any]: 队列资源配置信息
        """
        self.logger.info("开始采集YARN队列资源配置情况（REST API优先）")
        collect_time = datetime.now()
        yarn_client = self._get_yarn_client()
        queue_details = []
        
        if yarn_client:
            try:
                # 通过REST API获取所有队列信息
                scheduler = yarn_client._make_request('GET', 'cluster/scheduler').json()
                queues = scheduler.get('scheduler', {}).get('schedulerInfo', {}).get('queues', {}).get('queue', [])
                
                def flatten_queues(qs):
                    """递归展开队列层级"""
                    result = []
                    for q in qs:
                        result.append(q)
                        if 'queues' in q and 'queue' in q['queues']:
                            result.extend(flatten_queues(q['queues']['queue']))
                    return result
                    
                all_queues = flatten_queues(queues)
                for q in all_queues:
                    queue_detail = {
                        "queue_name": q.get("queueName", ""),
                        "state": q.get("state", ""),
                        "capacity_percent": q.get("capacity", 0),
                        "maximum_capacity_percent": q.get("maximumCapacity", 0),
                        "current_capacity_percent": q.get("currentCapacity", 0),
                        "num_containers": q.get("numContainers", 0),
                        "used_memory_mb": q.get("usedResources", {}).get("memory", 0),
                        "used_vcores": q.get("usedResources", {}).get("vCores", 0),
                        "reserved_memory_mb": q.get("reservedResources", {}).get("memory", 0),
                        "reserved_vcores": q.get("reservedResources", {}).get("vCores", 0),
                        "max_memory_mb": q.get("maxResources", {}).get("memory", 0),
                        "max_vcores": q.get("maxResources", {}).get("vCores", 0),
                        "min_memory_mb": q.get("minResources", {}).get("memory", 0),
                        "min_vcores": q.get("minResources", {}).get("vCores", 0),
                        "pending_containers": q.get("pendingContainers", 0),
                        "running_containers": q.get("runningContainers", 0),
                        "cluster_name": cluster_name,
                        "collect_time": collect_time.strftime('%Y-%m-%d %H:%M:%S'),
                        "insert_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    
                    # 保存到MySQL
                    if self.mysql_available:
                        try:
                            self._save_to_mysql("yarn_queue_resources", queue_detail)
                        except Exception as e:
                            self.logger.error(f"保存队列 {queue_detail['queue_name']} 数据到MySQL失败: {str(e)}")
                            
                    queue_details.append(queue_detail)
                    
            except Exception as e:
                self.logger.warning(f"YARN REST API队列采集失败，降级为CLI: {str(e)}")
                
        # 如果REST API失败，尝试使用CLI
        if not queue_details:
            try:
                all_queues = self._get_all_queues()
                for queue_name in all_queues:
                    try:
                        command = f"yarn queue -status {queue_name}"
                        return_code, queue_output = self._execute_yarn_command(command)
                        if return_code == 0:
                            queue_detail = self._parse_queue_status(queue_output)
                            queue_detail.update({
                                "queue_name": queue_name,
                                "cluster_name": cluster_name,
                                "collect_time": collect_time.strftime('%Y-%m-%d %H:%M:%S'),
                                "insert_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            })
                            
                            # 保存到MySQL
                            if self.mysql_available:
                                try:
                                    self._save_to_mysql("yarn_queue_resources", queue_detail)
                                except Exception as e:
                                    self.logger.error(f"保存队列 {queue_name} 数据到MySQL失败: {str(e)}")
                                    
                            queue_details.append(queue_detail)
                    except Exception as e:
                        self.logger.warning(f"获取队列 {queue_name} 信息失败: {str(e)}")
                        continue
                        
            except Exception as e:
                self.logger.error(f"CLI方式采集队列信息失败: {str(e)}")
                
        result = {
            "cluster_name": cluster_name,
            "collect_time": collect_time.strftime('%Y-%m-%d %H:%M:%S'),
            "total_queues": len(queue_details),
            "queue_details": queue_details
        }
        
        self.logger.info("YARN队列资源配置信息采集完成")
        return {"status": "success", "queue_resources": result}
        
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
            
    def _get_all_queues(self) -> List[str]:
        """
        获取所有队列名称
        
        Returns:
            List[str]: 队列名称列表
        """
        try:
            # 尝试获取队列列表
            command = "yarn queue -list"
            return_code, output = self._execute_yarn_command(command)
            
            if return_code != 0:
                # 如果获取队列列表失败，返回默认队列
                return ["default"]
                
            queues = []
            lines = output.strip().split('\n')
            
            for line in lines:
                if 'Queue Name :' in line:
                    match = re.search(r'Queue Name :\s*(.+)', line)
                    if match:
                        queue_name = match.group(1).strip()
                        if queue_name and queue_name not in queues:
                            queues.append(queue_name)
                            
            return queues if queues else ["default"]
            
        except Exception as e:
            self.logger.warning(f"获取队列列表失败: {str(e)}")
            return ["default"]
            
    def _parse_queue_status(self, output: str) -> Dict[str, Any]:
        """
        解析队列状态输出
        
        Args:
            output: yarn queue -status命令的输出
            
        Returns:
            Dict[str, Any]: 解析后的队列信息
        """
        try:
            lines = output.strip().split('\n')
            
            queue_info = {
                "state": "",
                "capacity_percent": 0,
                "maximum_capacity_percent": 0,
                "current_capacity_percent": 0,
                "num_containers": 0,
                "used_memory_mb": 0,
                "used_vcores": 0,
                "reserved_memory_mb": 0,
                "reserved_vcores": 0,
                "max_memory_mb": 0,
                "max_vcores": 0,
                "min_memory_mb": 0,
                "min_vcores": 0,
                "pending_containers": 0,
                "running_containers": 0
            }
            
            for line in lines:
                if 'State :' in line:
                    match = re.search(r'State :\s*(.+)', line)
                    if match:
                        queue_info["state"] = match.group(1).strip()
                elif 'Capacity :' in line:
                    match = re.search(r'Capacity :\s*([\d.]+)%', line)
                    if match:
                        queue_info["capacity_percent"] = float(match.group(1))
                elif 'Maximum Capacity :' in line:
                    match = re.search(r'Maximum Capacity :\s*([\d.]+)%', line)
                    if match:
                        queue_info["maximum_capacity_percent"] = float(match.group(1))
                elif 'Current Capacity :' in line:
                    match = re.search(r'Current Capacity :\s*([\d.]+)%', line)
                    if match:
                        queue_info["current_capacity_percent"] = float(match.group(1))
                elif 'Num Containers :' in line:
                    match = re.search(r'Num Containers :\s*(\d+)', line)
                    if match:
                        queue_info["num_containers"] = int(match.group(1))
                elif 'Used Memory :' in line:
                    match = re.search(r'Used Memory :\s*(\d+)', line)
                    if match:
                        queue_info["used_memory_mb"] = int(match.group(1))
                elif 'Used VCores :' in line:
                    match = re.search(r'Used VCores :\s*(\d+)', line)
                    if match:
                        queue_info["used_vcores"] = int(match.group(1))
                elif 'Reserved Memory :' in line:
                    match = re.search(r'Reserved Memory :\s*(\d+)', line)
                    if match:
                        queue_info["reserved_memory_mb"] = int(match.group(1))
                elif 'Reserved VCores :' in line:
                    match = re.search(r'Reserved VCores :\s*(\d+)', line)
                    if match:
                        queue_info["reserved_vcores"] = int(match.group(1))
                elif 'Max Memory :' in line:
                    match = re.search(r'Max Memory :\s*(\d+)', line)
                    if match:
                        queue_info["max_memory_mb"] = int(match.group(1))
                elif 'Max VCores :' in line:
                    match = re.search(r'Max VCores :\s*(\d+)', line)
                    if match:
                        queue_info["max_vcores"] = int(match.group(1))
                elif 'Min Memory :' in line:
                    match = re.search(r'Min Memory :\s*(\d+)', line)
                    if match:
                        queue_info["min_memory_mb"] = int(match.group(1))
                elif 'Min VCores :' in line:
                    match = re.search(r'Min VCores :\s*(\d+)', line)
                    if match:
                        queue_info["min_vcores"] = int(match.group(1))
                elif 'Pending Containers :' in line:
                    match = re.search(r'Pending Containers :\s*(\d+)', line)
                    if match:
                        queue_info["pending_containers"] = int(match.group(1))
                elif 'Running Containers :' in line:
                    match = re.search(r'Running Containers :\s*(\d+)', line)
                    if match:
                        queue_info["running_containers"] = int(match.group(1))
                        
            return queue_info
            
        except Exception as e:
            self.logger.error(f"解析队列状态失败: {str(e)}")
            return {
                "state": "",
                "capacity_percent": 0,
                "maximum_capacity_percent": 0,
                "current_capacity_percent": 0,
                "num_containers": 0,
                "used_memory_mb": 0,
                "used_vcores": 0,
                "reserved_memory_mb": 0,
                "reserved_vcores": 0,
                "max_memory_mb": 0,
                "max_vcores": 0,
                "min_memory_mb": 0,
                "min_vcores": 0,
                "pending_containers": 0,
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
    parser = argparse.ArgumentParser(description='YARN队列资源采集脚本')
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
        collector = YARNQueueCollector(env=args.env)
        
        # 执行队列资源采集
        results = collector.collect_queue_resources(args.cluster_name)
        
        # 打印结果
        print("采集任务执行完成:")
        print(json.dumps(results, indent=2, ensure_ascii=False))
        
    except Exception as e:
        print(f"执行失败: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main() 