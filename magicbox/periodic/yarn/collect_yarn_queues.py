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
            protocol = "https" if config.get('use_https', False) else "http"
            base_url = f"{protocol}://{config['resourcemanager']}:{config.get('resourcemanager_port', 8088)}/ws/v1"
            yarn_config = {
                'base_url': base_url,
                'timeout': config.get('timeout', 30),
                'retry_times': config.get('retry_times', 3),
                'retry_interval': config.get('retry_interval', 1),
                'username': config.get('username', 'hadoop'),
                'verify_ssl': config.get('verify_ssl', False)
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
        self.logger.info("开始采集YARN队列资源配置情况（仅使用REST API）")
        collect_time = datetime.now()
        
        # 获取YARN客户端
        yarn_client = self._get_yarn_client()
        if not yarn_client:
            error_msg = "无法获取YARN客户端实例"
            self.logger.error(error_msg)
            return {"status": "error", "message": error_msg}
            
        queue_details = []
        try:
            # 通过REST API获取调度器信息
            self.logger.info("正在获取YARN调度器信息...")
            scheduler_response = yarn_client._make_request('GET', 'cluster/scheduler')
            scheduler_data = scheduler_response.json()
            
            # 提取队列信息
            scheduler_info = scheduler_data.get('scheduler', {}).get('schedulerInfo', {})
            scheduler_type = scheduler_info.get('type', 'unknown')
            self.logger.info(f"检测到调度器类型: {scheduler_type}")
            
            # 根据调度器类型解析队列数据
            all_queues = []
            if scheduler_type == 'fairScheduler':
                # Fair Scheduler格式
                all_queues = self._parse_fair_scheduler(scheduler_info)
            elif scheduler_type in ['capacityScheduler', 'capacitySchedulerV2']:
                # Capacity Scheduler格式
                all_queues = self._parse_capacity_scheduler(scheduler_info)
            else:
                self.logger.warning(f"未知的调度器类型: {scheduler_type}，尝试通用解析")
                all_queues = self._parse_capacity_scheduler(scheduler_info)
                
            self.logger.info(f"解析后队列总数: {len(all_queues)}")
            
            # 处理每个队列
            for i, queue in enumerate(all_queues):
                try:
                    queue_detail = self._extract_queue_detail(queue, cluster_name, collect_time)
                    if queue_detail:
                        # 保存到MySQL
                        if self.mysql_available:
                            try:
                                self._save_to_mysql("yarn_queue_resources", queue_detail)
                                self.logger.debug(f"队列 {queue_detail['queue_name']} 数据已保存到MySQL")
                            except Exception as e:
                                self.logger.error(f"保存队列 {queue_detail['queue_name']} 数据到MySQL失败: {str(e)}")
                        else:
                            self.logger.info(f"MySQL不可用，跳过保存队列 {queue_detail['queue_name']} 数据")
                            
                        queue_details.append(queue_detail)
                        
                        # 每处理10个队列输出一次进度
                        if (i + 1) % 10 == 0:
                            self.logger.info(f"已处理 {i + 1}/{len(all_queues)} 个队列")
                            
                except Exception as e:
                    queue_name = queue.get("queueName", f"Unknown-{i}")
                    self.logger.error(f"处理队列 {queue_name} 时发生错误: {str(e)}")
                    continue
                    
            self.logger.info(f"YARN队列资源配置信息采集完成，共采集 {len(queue_details)} 个队列")
            
            result = {
                "cluster_name": cluster_name,
                "collect_time": collect_time.strftime('%Y-%m-%d %H:%M:%S'),
                "total_queues": len(queue_details),
                "queue_details": queue_details
            }
            
            return {"status": "success", "queue_resources": result}
            
        except Exception as e:
            error_msg = f"采集队列资源配置失败: {str(e)}"
            self.logger.error(error_msg)
            return {"status": "error", "message": error_msg}
            
    def _parse_fair_scheduler(self, scheduler_info: Dict) -> List[Dict]:
        """
        解析Fair Scheduler的队列数据
        
        Args:
            scheduler_info: 调度器信息
            
        Returns:
            List[Dict]: 队列列表
        """
        queues = []
        
        # Fair Scheduler通常只有一个rootQueue
        root_queue = scheduler_info.get('rootQueue', {})
        if root_queue:
            # 为rootQueue添加队列名称
            root_queue['queueName'] = 'root'
            queues.append(root_queue)
            
            # 递归处理子队列（如果有的话）
            child_queues = root_queue.get('childQueues', {})
            if child_queues:
                if isinstance(child_queues, dict) and 'queue' in child_queues:
                    child_queue_list = child_queues['queue']
                    if isinstance(child_queue_list, list):
                        queues.extend(self._flatten_capacity_queues(child_queue_list))
                    elif isinstance(child_queue_list, dict):
                        queues.extend(self._flatten_capacity_queues([child_queue_list]))
                        
        return queues
        
    def _parse_capacity_scheduler(self, scheduler_info: Dict) -> List[Dict]:
        """
        解析Capacity Scheduler的队列数据
        
        Args:
            scheduler_info: 调度器信息
            
        Returns:
            List[Dict]: 队列列表
        """
        queues_data = scheduler_info.get('queues', {})
        
        # 处理不同的队列数据结构
        root_queues = []
        if isinstance(queues_data, dict) and 'queue' in queues_data:
            root_queues = queues_data['queue']
        elif isinstance(queues_data, list):
            root_queues = queues_data
        
        # 确保root_queues是列表
        if not isinstance(root_queues, list):
            root_queues = [root_queues] if root_queues else []
            
        # 递归展开所有队列
        return self._flatten_capacity_queues(root_queues)
        
    def _flatten_capacity_queues(self, queues: List[Dict]) -> List[Dict]:
        """
        递归展开Capacity Scheduler队列层级结构
        
        Args:
            queues: 队列列表
            
        Returns:
            List[Dict]: 展开后的队列列表
        """
        result = []
        for queue in queues:
            # 添加当前队列
            result.append(queue)
            
            # 递归处理子队列
            child_queues = queue.get('queues', {})
            if isinstance(child_queues, dict) and 'queue' in child_queues:
                child_queue_list = child_queues['queue']
                if isinstance(child_queue_list, list):
                    result.extend(self._flatten_capacity_queues(child_queue_list))
                elif isinstance(child_queue_list, dict):
                    result.extend(self._flatten_capacity_queues([child_queue_list]))
                    
        return result
        
    def _extract_queue_detail(self, queue: Dict, cluster_name: str, collect_time: datetime) -> Optional[Dict[str, Any]]:
        """
        提取队列详细信息（支持Fair Scheduler和Capacity Scheduler）
        
        Args:
            queue: 队列数据
            cluster_name: 集群名称
            collect_time: 采集时间
            
        Returns:
            Optional[Dict[str, Any]]: 队列详细信息，如果提取失败返回None
        """
        try:
            # 基础信息
            queue_name = queue.get("queueName", "")
            state = queue.get("state", "RUNNING")  # Fair Scheduler默认状态
            
            # 资源信息
            used_resources = queue.get("usedResources", {})
            max_resources = queue.get("maxResources", {})
            min_resources = queue.get("minResources", {})
            reserved_resources = queue.get("reservedResources", {})
            
            # 容量信息（Capacity Scheduler专有，Fair Scheduler可能没有）
            capacity_percent = float(queue.get("capacity", 0))
            max_capacity_percent = float(queue.get("maximumCapacity", 0))
            current_capacity_percent = float(queue.get("currentCapacity", 0))
            
            # 如果是Fair Scheduler的root队列，尝试计算资源利用率作为容量
            if queue_name == "root" and capacity_percent == 0:
                max_memory = max_resources.get("memory", 0)
                used_memory = used_resources.get("memory", 0)
                if max_memory > 0:
                    current_capacity_percent = round((used_memory / max_memory) * 100, 2)
            
            queue_detail = {
                "queue_name": queue_name,
                "state": state,
                "capacity_percent": capacity_percent,
                "maximum_capacity_percent": max_capacity_percent,
                "current_capacity_percent": current_capacity_percent,
                "num_containers": int(queue.get("numContainers", 0)),
                "used_memory_mb": int(used_resources.get("memory", 0)),
                "used_vcores": int(used_resources.get("vCores", 0)),
                "reserved_memory_mb": int(reserved_resources.get("memory", 0)),
                "reserved_vcores": int(reserved_resources.get("vCores", 0)),
                "max_memory_mb": int(max_resources.get("memory", 0)),
                "max_vcores": int(max_resources.get("vCores", 0)),
                "min_memory_mb": int(min_resources.get("memory", 0)),
                "min_vcores": int(min_resources.get("vCores", 0)),
                "pending_containers": int(queue.get("pendingContainers", 0)),
                "running_containers": int(queue.get("runningContainers", 0)),
                "cluster_name": cluster_name,
                "collect_time": collect_time.strftime('%Y-%m-%d %H:%M:%S'),
                "insert_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            return queue_detail
            
        except Exception as e:
            queue_name = queue.get("queueName", "Unknown")
            self.logger.error(f"提取队列 {queue_name} 详细信息失败: {str(e)}")
            return None
            
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