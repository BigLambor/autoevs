#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Ambari连接测试脚本
用于验证Ambari API连接和基本数据采集功能
"""

import argparse
import sys
import json
from magicbox.script_template import ScriptTemplate
from lib.ambari.ambari_client import AmbariClient


class AmbariConnectionTester(ScriptTemplate):
    """Ambari连接测试类"""
    
    def __init__(self, env=None):
        super().__init__(env=env)
        
        try:
            self.ambari_client = AmbariClient(
                self.get_component_config("ambari")
            )
            self.logger.info("Ambari客户端初始化成功")
        except Exception as e:
            self.logger.error(f"Ambari客户端初始化失败: {str(e)}")
            raise
    
    def test_connection(self):
        """测试基本连接"""
        self.logger.info("测试Ambari连接...")
        try:
            clusters = self.ambari_client.get_clusters()
            self.logger.info(f"成功连接Ambari，发现 {len(clusters)} 个集群")
            for cluster in clusters:
                cluster_name = cluster['Clusters']['cluster_name']
                self.logger.info(f"集群名称: {cluster_name}")
            return True
        except Exception as e:
            self.logger.error(f"连接测试失败: {str(e)}")
            return False
    
    def test_cluster_info(self, cluster_name):
        """测试集群信息获取"""
        self.logger.info(f"测试获取集群 {cluster_name} 的信息...")
        try:
            # 获取集群基本信息
            cluster_info = self.ambari_client.get_cluster_info(cluster_name)
            self.logger.info(f"集群基本信息获取成功")
            
            # 获取服务列表
            services = self.ambari_client.get_services(cluster_name)
            self.logger.info(f"发现 {len(services)} 个服务")
            for service in services[:3]:  # 只显示前3个
                service_name = service['ServiceInfo']['service_name']
                service_state = service['ServiceInfo']['state']
                self.logger.info(f"  服务: {service_name}, 状态: {service_state}")
            
            # 获取主机列表
            hosts = self.ambari_client.get_hosts(cluster_name)
            self.logger.info(f"发现 {len(hosts)} 个主机")
            for host in hosts[:3]:  # 只显示前3个
                host_name = host['Hosts']['host_name']
                host_state = host['Hosts']['host_state']
                self.logger.info(f"  主机: {host_name}, 状态: {host_state}")
            
            return True
        except Exception as e:
            self.logger.error(f"集群信息测试失败: {str(e)}")
            return False
    
    def test_sample_collection(self, cluster_name):
        """测试样本数据采集"""
        self.logger.info(f"测试样本数据采集...")
        try:
            # 获取第一个服务的组件信息
            services = self.ambari_client.get_services(cluster_name)
            if not services:
                self.logger.warning("没有发现服务")
                return False
                
            first_service = services[0]
            service_name = first_service['ServiceInfo']['service_name']
            self.logger.info(f"测试服务: {service_name}")
            
            # 获取服务组件
            components = self.ambari_client.get_service_components(cluster_name, service_name)
            self.logger.info(f"服务 {service_name} 有 {len(components)} 个组件")
            
            if components:
                first_component = components[0]
                component_name = first_component['ServiceComponentInfo']['component_name']
                self.logger.info(f"测试组件: {component_name}")
                
                # 获取组件主机
                try:
                    component_hosts = self.ambari_client.get_role_hosts(
                        cluster_name, service_name, component_name
                    )
                    self.logger.info(f"组件 {component_name} 部署在 {len(component_hosts)} 个主机上")
                    
                    if component_hosts:
                        host_name = component_hosts[0]['HostRoles']['host_name']
                        self.logger.info(f"样例主机: {host_name}")
                        
                        # 获取主机详细信息
                        host_detail = self.ambari_client.get_host_info(cluster_name, host_name)
                        host_info = host_detail.get('Hosts', {})
                        self.logger.info(f"主机详情 - OS: {host_info.get('os_type', 'N/A')}, "
                                       f"CPU: {host_info.get('cpu_count', 'N/A')}, "
                                       f"内存: {host_info.get('total_mem', 'N/A')} KB")
                        
                except Exception as e:
                    self.logger.warning(f"获取组件主机信息失败: {str(e)}")
            
            return True
        except Exception as e:
            self.logger.error(f"样本数据采集测试失败: {str(e)}")
            return False
    
    def run_all_tests(self):
        """运行所有测试"""
        self.logger.info("开始运行Ambari连接测试...")
        
        # 测试连接
        if not self.test_connection():
            return False
        
        # 获取集群列表进行后续测试
        try:
            clusters = self.ambari_client.get_clusters()
            if not clusters:
                self.logger.error("没有发现集群")
                return False
                
            cluster_name = clusters[0]['Clusters']['cluster_name']
            
            # 测试集群信息
            if not self.test_cluster_info(cluster_name):
                return False
            
            # 测试样本采集
            if not self.test_sample_collection(cluster_name):
                return False
                
            self.logger.info("所有测试通过！")
            return True
            
        except Exception as e:
            self.logger.error(f"测试过程中出错: {str(e)}")
            return False


def parse_args():
    parser = argparse.ArgumentParser(description='Ambari连接测试脚本')
    parser.add_argument('--env', type=str, default=None, help='环境名称 (dev/test/prod)')
    return parser.parse_args()


def main():
    args = parse_args()
    
    try:
        tester = AmbariConnectionTester(env=args.env)
        success = tester.run_all_tests()
        
        if success:
            print("\n✅ 所有测试通过，可以继续使用采集脚本")
            sys.exit(0)
        else:
            print("\n❌ 测试失败，请检查配置")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n💥 测试过程中出现错误: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main() 