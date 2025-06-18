import requests
from typing import Dict, Any, List, Optional
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AmbariClient:
    def __init__(self, base_url: str, username: str = "admin", password: str = "admin"):
        """
        初始化Ambari客户端
        
        Args:
            base_url: Ambari服务器基础URL，例如：http://ambari-server:8080/api/v1
            username: 用户名，默认admin
            password: 密码，默认admin
        """
        self.base_url = base_url.rstrip('/')  # 移除末尾的斜杠
        self.session = requests.Session()
        self.session.auth = (username, password)
        self.session.headers.update({
            'X-Requested-By': 'ambari'
        })

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
        cluster = cluster_name or self.cluster_name
        response = self.session.get(
            f"{self.base_url}/clusters/{cluster}/hosts"
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
        cluster = cluster_name or self.cluster_name
        response = self.session.get(
            f"{self.base_url}/clusters/{cluster}/services/{service_name}/components"
        )
        
        # 获取所有组件
        components = response.json()['items']
        hosts = []
        
        # 遍历组件获取主机信息
        for component in components:
            component_name = component['HostRoles'].get('component_name')
            host_response = self.session.get(
                f"{self.base_url}/clusters/{cluster}/services/{service_name}/components/{component_name}/host_components"
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
        cluster = cluster_name or self.cluster_name
        response = self.session.get(
            f"{self.base_url}/clusters/{cluster}/services/{service_name}/components/{role_name}/host_components"
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
        cluster = cluster_name or self.cluster_name
        response = self.session.get(
            f"{self.base_url}/clusters/{cluster}/hosts"
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
        cluster = cluster_name or self.cluster_name
        response = self.session.get(
            f"{self.base_url}/clusters/{cluster}/hosts"
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