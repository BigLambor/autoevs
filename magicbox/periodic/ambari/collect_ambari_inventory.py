#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import logging
import sys
import time
from typing import Any, Dict, Optional, List
from datetime import datetime
import json
import yaml
import os

from magicbox.script_template import ScriptTemplate
from lib.ambari.ambari_client import AmbariClient
from lib.mysql.mysql_client import MySQLClient


class AmbariInventoryCollector(ScriptTemplate):
    """Ambari 集群清单采集脚本，用于采集集群、服务、组件、主机的完整清单信息"""
    
    def __init__(self, env: Optional[str] = None, enable_auto_learn: bool = True, save_learned_rules: bool = False):
        """
        初始化 Ambari 集群清单采集脚本
        
        Args:
            env: 环境名称 (dev/test/prod)，如果为None则使用默认环境
            enable_auto_learn: 是否启用从 Ambari 自动学习组件分类，默认启用
            save_learned_rules: 是否保存学习到的规则到文件，默认不保存
        """
        super().__init__(env=env)
        
        # 设置功能开关
        self.enable_auto_learn = enable_auto_learn
        self.save_learned_rules = save_learned_rules
        
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
            
        # 加载服务角色分类规则
        self.service_rules = self._load_service_rules()
        
        # 记录初始化信息
        if self.enable_auto_learn:
            self.logger.info("已启用从 Ambari 自动学习组件分类功能")
        if self.save_learned_rules:
            self.logger.info("已启用保存学习规则到文件功能")

    def _load_service_rules(self) -> Dict[str, Any]:
        """
        加载服务角色分类规则配置（通过统一配置管理器）
        
        Returns:
            Dict: 服务规则配置
        """
        try:
            # 使用统一的配置管理器加载配置
            rules = self.get_component_config("ambari_service_rules")
            self.logger.info(f"成功加载服务规则配置 (环境: {self.env})，支持 {len(rules.get('service_component_rules', {}))} 个服务")
            return rules
                
        except Exception as e:
            self.logger.warning(f"加载服务规则配置失败: {str(e)}，使用默认规则")
            return self._get_default_service_rules()
    
    def _get_default_service_rules(self) -> Dict[str, Any]:
        """
        获取默认的服务角色分类规则
        
        Returns:
            Dict: 默认规则配置
        """
        return {
            'service_component_rules': {
                'HDFS': {
                    'master_components': ['NAMENODE', 'SECONDARY_NAMENODE', 'JOURNALNODE'],
                    'worker_components': ['DATANODE'],
                    'client_components': ['HDFS_CLIENT']
                },
                'YARN': {
                    'master_components': ['RESOURCEMANAGER', 'APP_TIMELINE_SERVER'],
                    'worker_components': ['NODEMANAGER'],
                    'client_components': ['YARN_CLIENT']
                },
                'HIVE': {
                    'master_components': ['HIVE_METASTORE', 'HIVE_SERVER'],
                    'worker_components': [],
                    'client_components': ['HIVE_CLIENT']
                },
                'HBASE': {
                    'master_components': ['HBASE_MASTER'],
                    'worker_components': ['HBASE_REGIONSERVER'],
                    'client_components': ['HBASE_CLIENT']
                },
                'SPARK': {
                    'master_components': ['SPARK_JOBHISTORYSERVER'],
                    'worker_components': [],
                    'client_components': ['SPARK_CLIENT']
                },
                'ZOOKEEPER': {
                    'master_components': ['ZOOKEEPER_SERVER'],
                    'worker_components': [],
                    'client_components': ['ZOOKEEPER_CLIENT']
                },
                'KAFKA': {
                    'master_components': ['KAFKA_BROKER'],
                    'worker_components': [],
                    'client_components': ['KAFKA_CLIENT']
                }
            },
            'default_rules': {
                'master_keywords': ['MASTER', 'SERVER', 'MANAGER', 'COORDINATOR', 'NAMENODE', 'METASTORE'],
                'worker_keywords': ['WORKER', 'NODE', 'EXECUTOR', 'DATANODE', 'REGIONSERVER'],
                'client_keywords': ['CLIENT', 'GATEWAY']
            }
        }

    def _learn_component_roles_from_ambari(self, cluster_name: str) -> Dict[str, Any]:
        """
        从 Ambari API 动态学习组件角色分类规则
        
        Args:
            cluster_name: 集群名称
            
        Returns:
            Dict: 从 Ambari 学习到的服务组件规则
        """
        learned_rules = {
            'service_component_rules': {},
            'component_metadata': {}
        }
        
        if not self.ambari_available:
            return learned_rules
            
        try:
            self.logger.info(f"开始从 Ambari 学习集群 {cluster_name} 的组件角色分类")
            
            # 获取所有服务
            services = self.ambari_client.get_services(cluster_name)
            
            for service in services:
                service_name = service['ServiceInfo']['service_name']
                self.logger.debug(f"学习服务 {service_name} 的组件分类")
                
                learned_rules['service_component_rules'][service_name] = {
                    'master_components': [],
                    'worker_components': [],
                    'client_components': []
                }
                
                try:
                    # 获取服务的所有组件
                    components = self.ambari_client.get_service_components(cluster_name, service_name)
                    
                    for component in components:
                        component_info = component.get('ServiceComponentInfo', {})
                        component_name = component_info.get('component_name', '')
                        
                        if not component_name:
                            continue
                            
                        # 获取组件的角色类型信息
                        component_category = component_info.get('category', '')
                        component_cardinality = component_info.get('cardinality', '')
                        
                        # 保存组件元数据
                        learned_rules['component_metadata'][f"{service_name}.{component_name}"] = {
                            'category': component_category,
                            'cardinality': component_cardinality,
                            'service_name': service_name,
                            'component_name': component_name
                        }
                        
                        # 基于 Ambari 的分类逻辑进行角色分类
                        role_category = self._classify_component_by_ambari_metadata(
                            service_name, component_name, component_category, component_cardinality
                        )
                        
                        # 将组件添加到对应的角色类别中
                        if role_category == 'MASTER':
                            learned_rules['service_component_rules'][service_name]['master_components'].append(component_name)
                        elif role_category == 'WORKER':
                            learned_rules['service_component_rules'][service_name]['worker_components'].append(component_name)
                        elif role_category == 'CLIENT':
                            learned_rules['service_component_rules'][service_name]['client_components'].append(component_name)
                        
                        self.logger.debug(f"组件 {service_name}.{component_name} 分类为: {role_category} (category={component_category}, cardinality={component_cardinality})")
                        
                except Exception as e:
                    self.logger.warning(f"学习服务 {service_name} 组件分类失败: {str(e)}")
                    continue
            
            # 统计学习结果
            total_services = len(learned_rules['service_component_rules'])
            total_components = len(learned_rules['component_metadata'])
            self.logger.info(f"从 Ambari 成功学习到 {total_services} 个服务的 {total_components} 个组件分类规则")
            
            return learned_rules
            
        except Exception as e:
            self.logger.error(f"从 Ambari 学习组件角色分类失败: {str(e)}")
            return learned_rules

    def _classify_component_by_ambari_metadata(self, service_name: str, component_name: str, 
                                             category: str, cardinality: str) -> str:
        """
        基于 Ambari 元数据对组件进行角色分类
        
        Args:
            service_name: 服务名称
            component_name: 组件名称
            category: Ambari 组件类别
            cardinality: Ambari 组件基数
            
        Returns:
            str: 角色分类 (MASTER/WORKER/CLIENT/UNKNOWN)
        """
        # Ambari 的 category 字段通常包含以下值：
        # - MASTER: 主节点组件
        # - SLAVE: 工作节点组件  
        # - CLIENT: 客户端组件
        
        if category:
            category_upper = category.upper()
            if category_upper == 'MASTER':
                return 'MASTER'
            elif category_upper in ['SLAVE', 'DATANODE']:
                return 'WORKER'
            elif category_upper == 'CLIENT':
                return 'CLIENT'
        
        # 基于 cardinality 进行推断
        # cardinality 表示组件实例数量：
        # - "1": 通常是 Master 组件
        # - "1-2": 通常是 Master 组件（HA模式）
        # - "1+": 通常是 Worker 组件
        # - "ALL": 通常是 Client 组件
        
        if cardinality:
            if cardinality in ['1', '1-2', '2']:
                # 单实例或双实例通常是 Master
                return 'MASTER'
            elif cardinality in ['1+', '0+']:
                # 多实例通常是 Worker
                return 'WORKER'
            elif cardinality == 'ALL':
                # 所有节点通常是 Client
                return 'CLIENT'
        
        # 基于组件名称的关键词进行推断（作为后备方案）
        component_upper = component_name.upper()
        
        # Master 关键词
        master_keywords = [
            'MASTER', 'SERVER', 'MANAGER', 'COORDINATOR', 'NAMENODE', 
            'METASTORE', 'RESOURCEMANAGER', 'JOBHISTORY', 'TIMELINE',
            'JOURNALNODE', 'SECONDARY_NAMENODE', 'HISTORYSERVER'
        ]
        
        # Worker 关键词
        worker_keywords = [
            'WORKER', 'NODE', 'EXECUTOR', 'DATANODE', 'REGIONSERVER',
            'NODEMANAGER', 'TASKMANAGER', 'TASKTRACKER'
        ]
        
        # Client 关键词
        client_keywords = [
            'CLIENT', 'GATEWAY', 'CLI'
        ]
        
        for keyword in master_keywords:
            if keyword in component_upper:
                return 'MASTER'
                
        for keyword in worker_keywords:
            if keyword in component_upper:
                return 'WORKER'
                
        for keyword in client_keywords:
            if keyword in component_upper:
                return 'CLIENT'
        
        # 如果都无法匹配，返回 UNKNOWN
        return 'UNKNOWN'

    def _merge_learned_and_config_rules(self, learned_rules: Dict[str, Any]) -> Dict[str, Any]:
        """
        合并从 Ambari 学习到的规则和配置文件中的规则
        
        Args:
            learned_rules: 从 Ambari 学习到的规则
            
        Returns:
            Dict: 合并后的规则
        """
        # 从配置文件加载的规则作为基础
        merged_rules = self.service_rules.copy()
        
        # 将学习到的规则合并进来
        learned_service_rules = learned_rules.get('service_component_rules', {})
        
        for service_name, service_rules in learned_service_rules.items():
            if service_name in merged_rules.get('service_component_rules', {}):
                # 服务已存在，合并组件列表（配置文件优先）
                existing_rules = merged_rules['service_component_rules'][service_name]
                
                # 只添加配置文件中没有的组件
                for role_type in ['master_components', 'worker_components', 'client_components']:
                    existing_components = set(existing_rules.get(role_type, []))
                    learned_components = set(service_rules.get(role_type, []))
                    
                    # 合并组件列表
                    merged_components = existing_components.union(learned_components)
                    existing_rules[role_type] = list(merged_components)
                    
                self.logger.debug(f"合并服务 {service_name} 的规则: 配置文件 + Ambari学习")
            else:
                # 新服务，直接添加学习到的规则
                if 'service_component_rules' not in merged_rules:
                    merged_rules['service_component_rules'] = {}
                merged_rules['service_component_rules'][service_name] = service_rules
                self.logger.info(f"添加新服务 {service_name} 的学习规则")
        
        return merged_rules

    def _categorize_component(self, service_name: str, component_name: str) -> Dict[str, Any]:
        """
        根据服务和组件名称判断角色类别（支持配置化规则和动态学习）
        
        Args:
            service_name: 服务名称
            component_name: 组件名称
            
        Returns:
            Dict包含is_master, is_worker, role_category信息
        """
        service_rules = self.service_rules.get('service_component_rules', {})
        
        # 如果服务有明确的规则配置
        if service_name in service_rules:
            service_config = service_rules[service_name]
            is_master = component_name in service_config.get('master_components', [])
            is_worker = component_name in service_config.get('worker_components', [])
            is_client = component_name in service_config.get('client_components', [])
            
            if is_master:
                role_category = 'MASTER'
            elif is_worker:
                role_category = 'WORKER'
            elif is_client:
                role_category = 'CLIENT'
            else:
                role_category = 'UNKNOWN'
        else:
            # 使用默认规则（基于关键词匹配）
            default_rules = self.service_rules.get('default_rules', {})
            master_keywords = default_rules.get('master_keywords', [])
            worker_keywords = default_rules.get('worker_keywords', [])
            client_keywords = default_rules.get('client_keywords', [])
            
            is_master = any(keyword in component_name.upper() for keyword in master_keywords)
            is_worker = any(keyword in component_name.upper() for keyword in worker_keywords)
            is_client = any(keyword in component_name.upper() for keyword in client_keywords)
            
            if is_master:
                role_category = 'MASTER'
            elif is_worker:
                role_category = 'WORKER'
            elif is_client:
                role_category = 'CLIENT'
            else:
                role_category = 'UNKNOWN'
                
        # 记录未知服务的组件，用于后续扩展配置
        if service_name not in service_rules:
            self.logger.info(f"发现未配置的服务组件: {service_name}.{component_name} -> {role_category}")
        
        # 特殊服务的额外处理逻辑
        role_info = {
            'is_master': is_master,
            'is_worker': is_worker,
            'role_category': role_category
        }
        
        # 可以在这里添加特殊服务的自定义逻辑
        role_info = self._apply_service_specific_rules(service_name, component_name, role_info)
        
        return role_info
    
    def _apply_service_specific_rules(self, service_name: str, component_name: str, 
                                    role_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        应用服务特定的角色分类规则
        
        Args:
            service_name: 服务名称
            component_name: 组件名称
            role_info: 基础角色信息
            
        Returns:
            Dict: 更新后的角色信息
        """
        # Flink 特殊处理
        if service_name == 'FLINK':
            # Flink JobManager 总是 Master
            if 'JOBMANAGER' in component_name:
                role_info.update({
                    'is_master': True,
                    'is_worker': False,
                    'role_category': 'MASTER'
                })
            # Flink TaskManager 总是 Worker
            elif 'TASKMANAGER' in component_name:
                role_info.update({
                    'is_master': False,
                    'is_worker': True,
                    'role_category': 'WORKER'
                })
        
        # Presto 特殊处理
        elif service_name == 'PRESTO':
            if 'COORDINATOR' in component_name:
                role_info.update({
                    'is_master': True,
                    'is_worker': False,
                    'role_category': 'MASTER'
                })
            elif 'WORKER' in component_name:
                role_info.update({
                    'is_master': False,
                    'is_worker': True,
                    'role_category': 'WORKER'
                })
        
        return role_info

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
                                except Exception as e:
                                    self.logger.debug(f"获取主机 {host_name} 详细信息失败: {str(e)}")
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
                                    'host_memory_mb': int(host_info.get('total_mem', 0) / 1024) if host_info.get('total_mem') and host_info.get('total_mem') > 0 else 0,
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
                        except Exception as e:
                            self.logger.debug(f"获取组件 {component_name} 主机信息失败: {str(e)}")
                            pass
                except Exception as e:
                    self.logger.debug(f"获取服务 {service_name} 组件统计失败: {str(e)}")
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
                    
                # 直接调用 batch_insert 方法
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

    def _save_learned_rules_to_file(self, learned_rules: Dict[str, Any], cluster_name: str) -> None:
        """
        将从 Ambari 学习到的规则保存到文件中（可选功能）
        
        Args:
            learned_rules: 学习到的规则
            cluster_name: 集群名称
        """
        try:
            # 构建输出文件路径（使用配置管理器的环境目录）
            output_dir = self.config_manager.config_dir
            os.makedirs(output_dir, exist_ok=True)  # 确保目录存在
            output_file = os.path.join(output_dir, f'learned_ambari_rules_{cluster_name}.yaml')
            
            # 准备输出内容
            output_content = {
                'metadata': {
                    'cluster_name': cluster_name,
                    'generated_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'description': f'从 Ambari 集群 {cluster_name} 自动学习的组件角色分类规则',
                    'total_services': len(learned_rules.get('service_component_rules', {})),
                    'total_components': len(learned_rules.get('component_metadata', {}))
                },
                'service_component_rules': learned_rules.get('service_component_rules', {}),
                'component_metadata': learned_rules.get('component_metadata', {}),
                'usage_note': '此文件由系统自动生成，可以参考这些规则来完善 ambari_service_rules.yaml 配置文件'
            }
            
            # 保存到文件
            with open(output_file, 'w', encoding='utf-8') as f:
                yaml.dump(output_content, f, default_flow_style=False, allow_unicode=True, indent=2)
            
            self.logger.info(f"已将学习到的规则保存到文件: {output_file}")
            
        except Exception as e:
            self.logger.warning(f"保存学习规则到文件失败: {str(e)}")

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
                
                # 第一步：从 Ambari 动态学习组件角色分类（如果启用）
                learned_rules = {}
                if self.enable_auto_learn:
                    learned_rules = self._learn_component_roles_from_ambari(cluster_name)
                    
                    # 第二步：合并学习到的规则和配置文件规则
                    if learned_rules.get('service_component_rules'):
                        original_rules_count = len(self.service_rules.get('service_component_rules', {}))
                        self.service_rules = self._merge_learned_and_config_rules(learned_rules)
                        updated_rules_count = len(self.service_rules.get('service_component_rules', {}))
                        
                        if updated_rules_count > original_rules_count:
                            self.logger.info(f"动态学习新增了 {updated_rules_count - original_rules_count} 个服务的分类规则")
                else:
                    self.logger.info("自动学习功能已禁用，使用配置文件中的规则")
                
                # 第三步：采集清单信息
                inventory_data = self.collect_cluster_inventory(cluster_name)
                if inventory_data:
                    self._save_to_mysql('ambari_cluster_inventory', inventory_data)
                    
                # 第四步：采集统计信息
                stats_data = self.collect_cluster_stats(cluster_name)
                if stats_data:
                    self._save_to_mysql('ambari_cluster_stats', stats_data)
                    
                # 第五步：保存学习到的规则到文件
                if self.save_learned_rules:
                    self._save_learned_rules_to_file(learned_rules, cluster_name)
                    
                self.logger.info(f"集群 {cluster_name} 处理完成")
                
        except Exception as e:
            self.logger.error(f"执行采集任务失败: {str(e)}")
            raise


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='Ambari集群清单采集脚本')
    parser.add_argument('--env', type=str, default=None,
                       help='环境名称 (dev/test/prod)')
    parser.add_argument('--disable-auto-learn', action='store_true',
                       help='禁用从 Ambari 自动学习组件分类功能')
    parser.add_argument('--save-learned-rules', action='store_true',
                       help='保存学习到的规则到文件')
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
        collector = AmbariInventoryCollector(
            env=args.env,
            enable_auto_learn=not args.disable_auto_learn,
            save_learned_rules=args.save_learned_rules
        )
        collector.run()
    except Exception as e:
        print(f"脚本执行失败: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main() 