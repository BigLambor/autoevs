import requests
from typing import Dict, Any, List, Optional
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AmbariClient:
    def __init__(self, config: Dict[str, Any]):
        """
        初始化Ambari客户端
        
        Args:
            config: Ambari配置字典，包含base_url、username、password等信息
        """
        self.base_url = config['base_url'].rstrip('/')  # 移除末尾的斜杠
        self.username = config['username']
        self.password = config['password']
        self.cluster_name = config.get('cluster_name')
        self.timeout = config.get('timeout', 30)
        self.verify_ssl = config.get('verify_ssl', True)
        
        self.session = requests.Session()
        self.session.auth = (self.username, self.password)
        self.session.headers.update({
            'X-Requested-By': 'ambari'
        })
        self.session.verify = self.verify_ssl

    def get_clusters(self) -> List[Dict[str, Any]]:
        """获取集群列表"""
        response = self.session.get(f"{self.base_url}/clusters")
        response.raise_for_status()
        return response.json()['items']

    def get_cluster_info(self, cluster_name: str) -> Dict[str, Any]:
        """
        获取集群信息
        
        Args:
            cluster_name: 集群名称
        """
        response = self.session.get(f"{self.base_url}/clusters/{cluster_name}")
        response.raise_for_status()
        return response.json()

    def get_services(self, cluster_name: str) -> List[Dict[str, Any]]:
        """
        获取服务列表
        
        Args:
            cluster_name: 集群名称
        """
        response = self.session.get(f"{self.base_url}/clusters/{cluster_name}/services")
        response.raise_for_status()
        return response.json()['items']

    def get_service_info(self, cluster_name: str, service_name: str) -> Dict[str, Any]:
        """
        获取服务信息
        
        Args:
            cluster_name: 集群名称
            service_name: 服务名称
        """
        response = self.session.get(f"{self.base_url}/clusters/{cluster_name}/services/{service_name}")
        response.raise_for_status()
        return response.json()

    def get_hosts(self, cluster_name: str) -> List[Dict[str, Any]]:
        """
        获取主机列表
        
        Args:
            cluster_name: 集群名称
        """
        response = self.session.get(f"{self.base_url}/clusters/{cluster_name}/hosts")
        response.raise_for_status()
        return response.json()['items']

    def get_host_info(self, cluster_name: str, host_name: str) -> Dict[str, Any]:
        """
        获取主机信息
        
        Args:
            cluster_name: 集群名称
            host_name: 主机名
        """
        response = self.session.get(f"{self.base_url}/clusters/{cluster_name}/hosts/{host_name}")
        response.raise_for_status()
        return response.json()

    def get_host_components(self, cluster_name: str, host_name: str) -> List[Dict[str, Any]]:
        """
        获取主机组件列表
        
        Args:
            cluster_name: 集群名称
            host_name: 主机名
        """
        response = self.session.get(f"{self.base_url}/clusters/{cluster_name}/hosts/{host_name}/host_components")
        response.raise_for_status()
        return response.json()['items']

    def start_service(self, cluster_name: str, service_name: str) -> None:
        """
        启动服务
        
        Args:
            cluster_name: 集群名称
            service_name: 服务名称
        """
        response = self.session.put(
            f"{self.base_url}/clusters/{cluster_name}/services/{service_name}",
            json={'ServiceInfo': {'state': 'STARTED'}}
        )
        response.raise_for_status()

    def stop_service(self, cluster_name: str, service_name: str) -> None:
        """
        停止服务
        
        Args:
            cluster_name: 集群名称
            service_name: 服务名称
        """
        response = self.session.put(
            f"{self.base_url}/clusters/{cluster_name}/services/{service_name}",
            json={'ServiceInfo': {'state': 'INSTALLED'}}
        )
        response.raise_for_status()

    def restart_service(self, cluster_name: str, service_name: str) -> None:
        """
        重启服务
        
        Args:
            cluster_name: 集群名称
            service_name: 服务名称
        """
        self.stop_service(cluster_name, service_name)
        self.start_service(cluster_name, service_name)

    def get_cluster_hosts(self, cluster_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        获取集群所有主机列表
        
        Args:
            cluster_name: 集群名称，如果为None则使用配置中的集群名
            
        Returns:
            主机列表
        """
        if not cluster_name:
            raise ValueError("cluster_name参数不能为空")
        response = self.session.get(
            f"{self.base_url}/clusters/{cluster_name}/hosts"
        )
        response.raise_for_status()
        return response.json()['items']

    def get_service_hosts(self, cluster_name: Optional[str] = None, service_name: str = None) -> List[Dict[str, Any]]:
        """
        获取指定服务的所有主机列表
        
        Args:
            cluster_name: 集群名称，如果为None则使用配置中的集群名
            service_name: 服务名称
            
        Returns:
            主机列表
        """
        if not cluster_name:
            raise ValueError("cluster_name参数不能为空")
        if not service_name:
            raise ValueError("service_name参数不能为空")
            
        response = self.session.get(
            f"{self.base_url}/clusters/{cluster_name}/services/{service_name}/components"
        )
        
        # 获取所有组件
        components = response.json()['items']
        hosts = []
        
        # 遍历组件获取主机信息
        for component in components:
            component_name = component['HostRoles'].get('component_name')
            host_response = self.session.get(
                f"{self.base_url}/clusters/{cluster_name}/services/{service_name}/components/{component_name}/host_components"
            )
            host_components = host_response.json()['items']
            for host_component in host_components:
                host_info = host_component['HostRoles']
                if host_info not in hosts:
                    hosts.append(host_info)
        
        return hosts

    def get_role_hosts(self, cluster_name: Optional[str] = None, service_name: str = None, role_name: str = None) -> List[Dict[str, Any]]:
        """
        获取指定服务角色的所有主机列表
        
        Args:
            cluster_name: 集群名称，如果为None则使用配置中的集群名
            service_name: 服务名称
            role_name: 角色名称
            
        Returns:
            主机列表
        """
        if not cluster_name:
            raise ValueError("cluster_name参数不能为空")
        if not service_name:
            raise ValueError("service_name参数不能为空")
        if not role_name:
            raise ValueError("role_name参数不能为空")
            
        response = self.session.get(
            f"{self.base_url}/clusters/{cluster_name}/services/{service_name}/components/{role_name}/host_components"
        )
        
        hosts = []
        host_components = response.json()['items']
        for host_component in host_components:
            host_info = host_component['HostRoles']
            if host_info not in hosts:
                hosts.append(host_info)
        
        return hosts

    def get_host_groups(self, cluster_name: Optional[str] = None) -> List[str]:
        """
        获取集群的所有主机组列表
        
        Args:
            cluster_name: 集群名称，如果为None则使用配置中的集群名
            
        Returns:
            主机组名称列表
        """
        if not cluster_name:
            raise ValueError("cluster_name参数不能为空")
            
        response = self.session.get(
            f"{self.base_url}/clusters/{cluster_name}/hosts"
        )
        
        groups = set()
        hosts = response.json()['items']
        for host in hosts:
            host_groups = host['HostRoles'].get('host_groups', [])
            groups.update(host_groups)
        
        return list(groups)

    def get_group_hosts(self, cluster_name: Optional[str] = None, group_name: str = None) -> List[Dict[str, Any]]:
        """
        获取指定主机组的所有主机列表
        
        Args:
            cluster_name: 集群名称，如果为None则使用配置中的集群名
            group_name: 主机组名称
            
        Returns:
            主机列表
        """
        if not cluster_name:
            raise ValueError("cluster_name参数不能为空")
        if not group_name:
            raise ValueError("group_name参数不能为空")
            
        response = self.session.get(
            f"{self.base_url}/clusters/{cluster_name}/hosts"
        )
        
        hosts = []
        all_hosts = response.json()['items']
        for host in all_hosts:
            host_groups = host['HostRoles'].get('host_groups', [])
            if group_name in host_groups:
                hosts.append(host['HostRoles'])
        
        return hosts

    def get_host_services(self, cluster_name: Optional[str] = None, host_name: str = None) -> List[str]:
        """
        获取指定主机的所有服务列表
        
        Args:
            cluster_name: 集群名称，如果为None则使用配置中的集群名
            host_name: 主机名称
            
        Returns:
            服务名称列表
        """
        if not cluster_name:
            raise ValueError("cluster_name参数不能为空")
        if not host_name:
            raise ValueError("host_name参数不能为空")
            
        components = self.get_host_components(cluster_name, host_name)
        services = set()
        for component in components:
            service_name = component['HostRoles'].get('service_name')
            if service_name:
                services.add(service_name)
        return list(services)

    def get_host_roles(self, cluster_name: Optional[str] = None, host_name: str = None, service_name: Optional[str] = None) -> List[str]:
        """
        获取指定主机的所有角色列表
        
        Args:
            cluster_name: 集群名称，如果为None则使用配置中的集群名
            host_name: 主机名称
            service_name: 服务名称，如果指定则只返回该服务的角色
            
        Returns:
            角色名称列表
        """
        if not cluster_name:
            raise ValueError("cluster_name参数不能为空")
        if not host_name:
            raise ValueError("host_name参数不能为空")
            
        components = self.get_host_components(cluster_name, host_name)
        roles = set()
        for component in components:
            host_roles = component['HostRoles']
            if not service_name or host_roles.get('service_name') == service_name:
                role_name = host_roles.get('component_name')
                if role_name:
                    roles.add(role_name)
        return list(roles)

    def get_cluster_services(self, cluster_name: str) -> List[Dict]:
        """获取集群服务信息"""
        response = self.session.get(f"{self.base_url}/clusters/{cluster_name}/services")
        response.raise_for_status()
        return response.json()['items']

    def get_service_components(self, cluster_name: str, service_name: str) -> List[Dict]:
        """获取服务组件信息"""
        response = self.session.get(
            f"{self.base_url}/clusters/{cluster_name}/services/{service_name}/components"
        )
        response.raise_for_status()
        return response.json()['items']

    def get_alerts(self, cluster_name: str) -> List[Dict]:
        """获取集群告警信息"""
        response = self.session.get(
            f"{self.base_url}/clusters/{cluster_name}/alerts"
        )
        response.raise_for_status()
        return response.json()['items']

    def get_comprehensive_cluster_info(self, cluster_name: str = None) -> Dict[str, Any]:
        """
        获取集群的完整信息，包括所有服务、角色、主机、IP等
        
        Args:
            cluster_name: 集群名称，如果为None则获取所有集群
            
        Returns:
            Dict[str, Any]: 完整的集群信息
        """
        comprehensive_info = {
            "clusters": [],
            "total_clusters": 0,
            "total_hosts": 0,
            "total_services": 0
        }
        
        try:
            # 获取所有集群
            clusters = self.get_clusters()
            comprehensive_info["total_clusters"] = len(clusters)
            
            for cluster in clusters:
                cluster_name = cluster['Clusters']['cluster_name']
                cluster_info = {
                    "cluster_name": cluster_name,
                    "cluster_info": cluster,
                    "services": [],
                    "hosts": [],
                    "service_roles": {},
                    "host_details": {}
                }
                
                # 获取集群服务
                try:
                    services = self.get_services(cluster_name)
                    cluster_info["services"] = services
                    comprehensive_info["total_services"] += len(services)
                    
                    # 获取每个服务的组件和角色
                    for service in services:
                        service_name = service['ServiceInfo']['service_name']
                        cluster_info["service_roles"][service_name] = []
                        
                        try:
                            components = self.get_service_components(cluster_name, service_name)
                            cluster_info["service_roles"][service_name] = components
                        except Exception as e:
                            logger.warning(f"获取服务 {service_name} 组件失败: {str(e)}")
                            
                except Exception as e:
                    logger.warning(f"获取集群 {cluster_name} 服务失败: {str(e)}")
                
                # 获取集群主机
                try:
                    hosts = self.get_hosts(cluster_name)
                    cluster_info["hosts"] = hosts
                    comprehensive_info["total_hosts"] += len(hosts)
                    
                    # 获取每个主机的详细信息
                    for host in hosts:
                        host_name = host['Hosts']['host_name']
                        cluster_info["host_details"][host_name] = {
                            "host_info": host,
                            "components": [],
                            "services": [],
                            "roles": []
                        }
                        
                        try:
                            # 获取主机组件
                            components = self.get_host_components(cluster_name, host_name)
                            cluster_info["host_details"][host_name]["components"] = components
                            
                            # 获取主机服务
                            services = self.get_host_services(cluster_name, host_name)
                            cluster_info["host_details"][host_name]["services"] = services
                            
                            # 获取主机角色
                            roles = self.get_host_roles(cluster_name, host_name)
                            cluster_info["host_details"][host_name]["roles"] = roles
                            
                        except Exception as e:
                            logger.warning(f"获取主机 {host_name} 详细信息失败: {str(e)}")
                            
                except Exception as e:
                    logger.warning(f"获取集群 {cluster_name} 主机失败: {str(e)}")
                
                comprehensive_info["clusters"].append(cluster_info)
                
        except Exception as e:
            logger.error(f"获取综合集群信息失败: {str(e)}")
            raise
            
        return comprehensive_info
        
    def get_host_ip_mapping(self, cluster_name: str) -> Dict[str, str]:
        """
        获取主机名到IP地址的映射
        
        Args:
            cluster_name: 集群名称
            
        Returns:
            Dict[str, str]: 主机名到IP地址的映射
        """
        host_ip_mapping = {}
        
        try:
            hosts = self.get_hosts(cluster_name)
            for host in hosts:
                host_name = host['Hosts']['host_name']
                try:
                    host_info = self.get_host_info(cluster_name, host_name)
                    # 从主机信息中提取IP地址
                    ip_address = host_info.get('Hosts', {}).get('ip', '')
                    if ip_address:
                        host_ip_mapping[host_name] = ip_address
                except Exception as e:
                    logger.warning(f"获取主机 {host_name} IP地址失败: {str(e)}")
                    
        except Exception as e:
            logger.error(f"获取主机IP映射失败: {str(e)}")
            
        return host_ip_mapping
        
    def get_service_role_hosts(self, cluster_name: str) -> Dict[str, Dict[str, List[str]]]:
        """
        获取服务角色到主机的映射
        
        Args:
            cluster_name: 集群名称
            
        Returns:
            Dict[str, Dict[str, List[str]]]: 服务角色到主机的映射
        """
        service_role_hosts = {}
        
        try:
            services = self.get_services(cluster_name)
            for service in services:
                service_name = service['ServiceInfo']['service_name']
                service_role_hosts[service_name] = {}
                
                try:
                    components = self.get_service_components(cluster_name, service_name)
                    for component in components:
                        component_name = component['ServiceComponentInfo']['component_name']
                        try:
                            role_hosts = self.get_role_hosts(cluster_name, service_name, component_name)
                            host_names = [host['HostRoles']['host_name'] for host in role_hosts]
                            service_role_hosts[service_name][component_name] = host_names
                        except Exception as e:
                            logger.warning(f"获取角色 {component_name} 主机失败: {str(e)}")
                            service_role_hosts[service_name][component_name] = []
                            
                except Exception as e:
                    logger.warning(f"获取服务 {service_name} 组件失败: {str(e)}")
                    
        except Exception as e:
            logger.error(f"获取服务角色主机映射失败: {str(e)}")
            
        return service_role_hosts 