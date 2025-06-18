import requests
from typing import Dict, Any, List, Optional
import logging
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class YARNClient:
    def __init__(self, config: Dict[str, Any]):
        """
        初始化YARN客户端
        
        Args:
            config: YARN配置字典，包含以下字段：
                - base_url: ResourceManager基础URL，例如：http://yarn-rm:8088/ws/v1
                - timeout: 请求超时时间（秒），默认30
                - retry_times: 重试次数，默认3
                - retry_interval: 重试间隔（秒），默认1
        """
        self.base_url = config['base_url'].rstrip('/')  # 移除末尾的斜杠
        self.timeout = config.get('timeout', 30)
        self.retry_times = config.get('retry_times', 3)
        self.retry_interval = config.get('retry_interval', 1)
        
        # 创建会话并配置重试
        self.session = requests.Session()
        retry_strategy = Retry(
            total=self.retry_times,
            backoff_factor=self.retry_interval,
            status_forcelist=[500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """
        发送HTTP请求
        
        Args:
            method: HTTP方法
            endpoint: API端点
            **kwargs: 请求参数
            
        Returns:
            Response对象
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        try:
            response = self.session.request(
                method,
                url,
                timeout=self.timeout,
                **kwargs
            )
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {str(e)}")
            raise

    def get_cluster_info(self) -> Dict[str, Any]:
        """获取集群信息"""
        response = self._make_request('GET', 'cluster/info')
        return response.json()

    def get_cluster_metrics(self) -> Dict[str, Any]:
        """获取集群指标"""
        response = self._make_request('GET', 'cluster/metrics')
        return response.json()

    def get_cluster_applications(self, states: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        获取应用程序列表
        
        Args:
            states: 应用程序状态列表，可选
        """
        params = {}
        if states:
            params['states'] = ','.join(states)
        
        response = self._make_request('GET', 'cluster/apps', params=params)
        return response.json()['apps']['app']

    def get_application_info(self, application_id: str) -> Dict[str, Any]:
        """
        获取应用程序信息
        
        Args:
            application_id: 应用程序ID
        """
        response = self._make_request('GET', f'cluster/apps/{application_id}')
        return response.json()['app']

    def get_application_attempts(self, application_id: str) -> List[Dict[str, Any]]:
        """
        获取应用程序尝试列表
        
        Args:
            application_id: 应用程序ID
        """
        response = self._make_request('GET', f'cluster/apps/{application_id}/appattempts')
        return response.json()['appAttempts']['appAttempt']

    def get_containers(self, application_id: str, attempt_id: str) -> List[Dict[str, Any]]:
        """
        获取容器列表
        
        Args:
            application_id: 应用程序ID
            attempt_id: 尝试ID
        """
        response = self._make_request('GET', f'cluster/apps/{application_id}/appattempts/{attempt_id}/containers')
        return response.json()['containers']['container']

    def get_node_info(self, node_id: str) -> Dict[str, Any]:
        """
        获取节点信息
        
        Args:
            node_id: 节点ID
        """
        response = self._make_request('GET', f'cluster/nodes/{node_id}')
        return response.json()['node']

    def get_nodes(self, states: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        获取节点列表
        
        Args:
            states: 节点状态列表，可选
        """
        params = {}
        if states:
            params['states'] = ','.join(states)
        
        response = self._make_request('GET', 'cluster/nodes', params=params)
        return response.json()['nodes']['node']

    def kill_application(self, application_id: str) -> None:
        """
        终止应用程序
        
        Args:
            application_id: 应用程序ID
        """
        response = self._make_request('PUT', f'cluster/apps/{application_id}/state', json={'state': 'KILLED'})
        response.raise_for_status() 