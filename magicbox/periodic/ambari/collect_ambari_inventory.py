#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import logging
import sys
import time
from typing import Any, Dict, Optional, List
from datetime import datetime
import json

from magicbox.script_template import ScriptTemplate
from lib.ambari.ambari_client import AmbariClient
from lib.mysql.mysql_client import MySQLClient


class AmbariInventoryCollector(ScriptTemplate):
    """Ambari 集群清单采集脚本，用于采集集群、服务、组件、主机的完整清单信息"""
    
    def __init__(self, env: Optional[str] = None):
        """
        初始化 Ambari 集群清单采集脚本
        
        Args:
            env: 环境名称 (dev/test/prod)，如果为None则使用默认环境
        """
        super().__init__(env=env)
        
        # 创建Ambari客户端
        try:
            self.ambari_client = AmbariClient(
                self.get_component_config("ambari")
            )
            self.ambari_available = True
        except Exception as e:
            self.logger.error(f"Ambari客户端初始化失败: {str(e)}")
            self.ambari_available = False
            
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

    def _categorize_component(self, service_name: str, component_name: str) -> Dict[str, Any]:
        """
        根据服务和组件名称判断角色类别
        
        Args:
            service_name: 服务名称
            component_name: 组件名称
            
        Returns:
            Dict包含is_master, is_worker, role_category信息
        """
        # Master组件列表
        master_components = {
            'HDFS': ['NAMENODE', 'SECONDARY_NAMENODE', 'JOURNALNODE'],
            'YARN': ['RESOURCEMANAGER', 'APP_TIMELINE_SERVER'],
            'HIVE': ['HIVE_METASTORE', 'HIVE_SERVER'],
            'HBASE': ['HBASE_MASTER'],
            'SPARK': ['SPARK_JOBHISTORYSERVER'],
            'ZOOKEEPER': ['ZOOKEEPER_SERVER'],
            'AMBARI_METRICS': ['METRICS_COLLECTOR'],
            'KAFKA': ['KAFKA_BROKER'],
            'STORM': ['NIMBUS', 'STORM_UI_SERVER']
        }
        
        # Worker组件列表
        worker_components = {
            'HDFS': ['DATANODE'],
            'YARN': ['NODEMANAGER'],
            'HBASE': ['HBASE_REGIONSERVER'],
            'STORM': ['SUPERVISOR']
        }
        
        is_master = component_name in master_components.get(service_name, [])
        is_worker = component_name in worker_components.get(service_name, [])
        
        if is_master:
            role_category = 'MASTER'
        elif is_worker:
            role_category = 'WORKER'
        else:
            role_category = 'CLIENT'
            
        return {
            'is_master': is_master,
            'is_worker': is_worker,
            'role_category': role_category
        }

    def collect_cluster_inventory(self, cluster_name: str) -> List[Dict[str, Any]]:
        """
        采集指定集群的完整清单信息
        
        Args:
            cluster_name: 集群名称
            
        Returns:
            List[Dict]: 扁平化的清单记录列表
        """
        if not self.ambari_available:
            self.logger.error("Ambari客户端不可用")
            return []
            
        self.logger.info(f"开始采集集群 {cluster_name} 的清单信息")
        collect_time = datetime.now()
        inventory_records = []
        
        try:
            # 获取集群基本信息
            cluster_info = self.ambari_client.get_cluster_info(cluster_name)
            cluster_basic_info = cluster_info.get('Clusters', {})
            
            # 获取服务列表
            services = self.ambari_client.get_services(cluster_name)
            
            # 获取主机列表和IP映射
            hosts = self.ambari_client.get_hosts(cluster_name)
            host_ip_mapping = self.ambari_client.get_host_ip_mapping(cluster_name)
            
            # 遍历服务
            for service in services:
                service_info = service.get('ServiceInfo', {})
                service_name = service_info.get('service_name', '')
                
                try:
                    # 获取服务组件
                    components = self.ambari_client.get_service_components(cluster_name, service_name)
                    
                    for component in components:
                        component_info = component.get('ServiceComponentInfo', {})
                        component_name = component_info.get('component_name', '')
                        
                        try:
                            # 获取组件所在的主机
                            component_hosts = self.ambari_client.get_role_hosts(
                                cluster_name, service_name, component_name
                            )
                            
                            for host_role in component_hosts:
                                host_name = host_role.get('HostRoles', {}).get('host_name', '')
                                if not host_name:
                                    continue
                                    
                                # 获取主机详细信息
                                try:
                                    host_detail = self.ambari_client.get_host_info(cluster_name, host_name)
                                    host_info = host_detail.get('Hosts', {})
                                except:
                                    host_info = {}
                                
                                # 分类组件角色
                                role_info = self._categorize_component(service_name, component_name)
                                
                                # 构建扁平记录
                                record = {
                                    'collect_time': collect_time.strftime('%Y-%m-%d %H:%M:%S'),
                                    'insert_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                    
                                    # 集群信息
                                    'cluster_name': cluster_name,
                                    'cluster_id': str(cluster_basic_info.get('cluster_id', '')),
                                    'cluster_version': cluster_basic_info.get('version', ''),
                                    'cluster_state': cluster_basic_info.get('provisioning_state', ''),
                                    
                                    # 服务信息
                                    'service_name': service_name,
                                    'service_state': service_info.get('state', ''),
                                    'service_version': service_info.get('repository_version', ''),
                                    
                                    # 组件信息
                                    'component_name': component_name,
                                    'component_state': host_role.get('HostRoles', {}).get('state', ''),
                                    'component_version': component_info.get('component_version', ''),
                                    
                                    # 主机信息
                                    'host_name': host_name,
                                    'host_ip': host_ip_mapping.get(host_name, ''),
                                    'host_os': host_info.get('os_type', ''),
                                    'host_cpu_count': host_info.get('cpu_count', 0) or 0,
                                    'host_memory_mb': int(host_info.get('total_mem', 0) / 1024) if host_info.get('total_mem') else 0,
                                    'host_disk_gb': 0,  # Ambari API通常不直接提供磁盘总容量
                                    'host_state': host_info.get('host_state', ''),
                                    
                                    # 角色信息
                                    'is_master': role_info['is_master'],
                                    'is_worker': role_info['is_worker'],
                                    'role_category': role_info['role_category']
                                }
                                
                                inventory_records.append(record)
                                
                        except Exception as e:
                            self.logger.warning(f"处理组件 {component_name} 时出错: {str(e)}")
                            continue
                            
                except Exception as e:
                    self.logger.warning(f"处理服务 {service_name} 时出错: {str(e)}")
                    continue
            
            self.logger.info(f"成功采集到 {len(inventory_records)} 条清单记录")
            return inventory_records
            
        except Exception as e:
            self.logger.error(f"采集集群清单信息失败: {str(e)}")
            return []

    def collect_cluster_stats(self, cluster_name: str) -> Dict[str, Any]:
        """
        采集集群统计信息
        
        Args:
            cluster_name: 集群名称
            
        Returns:
            Dict: 集群统计信息
        """
        if not self.ambari_available:
            self.logger.error("Ambari客户端不可用")
            return {}
            
        self.logger.info(f"开始采集集群 {cluster_name} 的统计信息")
        collect_time = datetime.now()
        
        try:
            # 获取基础信息
            services = self.ambari_client.get_services(cluster_name)
            hosts = self.ambari_client.get_hosts(cluster_name)
            
            # 统计服务状态
            service_states = {}
            total_components = 0
            component_states = {}
            
            for service in services:
                service_name = service['ServiceInfo']['service_name']
                service_state = service['ServiceInfo']['state']
                service_states[service_state] = service_states.get(service_state, 0) + 1
                
                # 获取服务组件统计
                try:
                    components = self.ambari_client.get_service_components(cluster_name, service_name)
                    total_components += len(components)
                    
                    for component in components:
                        # 获取组件实例状态
                        component_name = component['ServiceComponentInfo']['component_name']
                        try:
                            component_hosts = self.ambari_client.get_role_hosts(
                                cluster_name, service_name, component_name
                            )
                            for host_role in component_hosts:
                                state = host_role.get('HostRoles', {}).get('state', 'UNKNOWN')
                                component_states[state] = component_states.get(state, 0) + 1
                        except:
                            pass
                except:
                    pass
            
            # 统计主机状态
            host_states = {}
            for host in hosts:
                host_state = host['Hosts']['host_state']
                host_states[host_state] = host_states.get(host_state, 0) + 1
            
            # 构建统计记录
            stats = {
                'cluster_name': cluster_name,
                'collect_time': collect_time.strftime('%Y-%m-%d %H:%M:%S'),
                'insert_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                
                'total_services': len(services),
                'running_services': service_states.get('STARTED', 0),
                'stopped_services': service_states.get('INSTALLED', 0),
                
                'total_hosts': len(hosts),
                'healthy_hosts': host_states.get('HEALTHY', 0),
                'unhealthy_hosts': host_states.get('UNHEALTHY', 0),
                
                'total_components': total_components,
                'started_components': component_states.get('STARTED', 0),
                'installed_components': component_states.get('INSTALLED', 0)
            }
            
            self.logger.info(f"成功采集集群统计信息: 服务{stats['total_services']}个, 主机{stats['total_hosts']}个, 组件{stats['total_components']}个")
            return stats
            
        except Exception as e:
            self.logger.error(f"采集集群统计信息失败: {str(e)}")
            return {}

    def _save_to_mysql(self, table_name: str, data) -> None:
        """
        保存数据到MySQL数据库
        
        Args:
            table_name: 表名
            data: 要保存的数据，可以是单条记录(Dict)或记录列表(List[Dict])
        """
        if not self.mysql_available:
            self.logger.info(f"MySQL不可用，跳过保存到表 {table_name}")
            return
            
        if not data:
            self.logger.info(f"没有数据需要保存到表 {table_name}")
            return
            
        try:
            if isinstance(data, list):
                # 批量插入
                if len(data) == 0:
                    return
                    
                first_record = data[0]
                columns = ", ".join(first_record.keys())
                placeholders = ", ".join(["%s"] * len(first_record))
                
                sql = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
                
                # 准备批量数据
                values_list = []
                for record in data:
                    values_list.append(list(record.values()))
                
                # 批量执行
                self.mysql_client.batch_insert(table_name, data)
                self.logger.info(f"成功保存 {len(data)} 条记录到表 {table_name}")
            else:
                # 单条记录
                columns = ", ".join(data.keys())
                placeholders = ", ".join(["%s"] * len(data))
                values = list(data.values())
                
                sql = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
                
                self.mysql_client.execute_update(sql, values)
                self.logger.info(f"成功保存 1 条记录到表 {table_name}")
                
        except Exception as e:
            self.logger.error(f"保存数据到MySQL失败: {str(e)}")
            raise

    def run(self):
        """执行采集任务"""
        self.logger.info("开始执行Ambari集群清单采集任务")
        
        if not self.ambari_available:
            self.logger.error("Ambari客户端不可用，退出")
            return
            
        try:
            # 获取集群列表
            clusters = self.ambari_client.get_clusters()
            
            for cluster in clusters:
                cluster_name = cluster['Clusters']['cluster_name']
                self.logger.info(f"开始处理集群: {cluster_name}")
                
                # 采集清单信息
                inventory_data = self.collect_cluster_inventory(cluster_name)
                if inventory_data:
                    self._save_to_mysql('ambari_cluster_inventory', inventory_data)
                    
                # 采集统计信息
                stats_data = self.collect_cluster_stats(cluster_name)
                if stats_data:
                    self._save_to_mysql('ambari_cluster_stats', stats_data)
                    
                self.logger.info(f"集群 {cluster_name} 处理完成")
                
        except Exception as e:
            self.logger.error(f"执行采集任务失败: {str(e)}")
            raise


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='Ambari集群清单采集脚本')
    parser.add_argument('--env', type=str, default=None,
                       help='环境名称 (dev/test/prod)')
    return parser.parse_args()


def main():
    """主函数"""
    args = parse_args()
    
    # 信号处理
    def signal_handler(signum, frame):
        print("收到信号，正在退出...")
        sys.exit(0)
        
    import signal
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        collector = AmbariInventoryCollector(env=args.env)
        collector.run()
    except Exception as e:
        print(f"脚本执行失败: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main() 