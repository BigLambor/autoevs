from typing import Dict, Any, List, Optional
import logging
from lib.http.http_client import HttpClient

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class YARNClient:
    def __init__(self, config: Dict[str, Any]):
        """
        初始化YARN客户端
        
        Args:
            config: YARN配置字典，包含以下字段：
                - base_url: ResourceManager基础URL，例如：https://yarn-rm:8088/ws/v1
                - timeout: 请求超时时间（秒），默认30
                - retry_times: 重试次数，默认3
                - retry_interval: 重试间隔（秒），默认1
                - username: YARN REST API用户名，用于user.name参数
                - verify_ssl: 是否验证SSL证书，默认False
        """
        self.base_url = config['base_url'].rstrip('/')  # 移除末尾的斜杠
        self.timeout = config.get('timeout', 30)
        self.retry_times = config.get('retry_times', 3)
        self.retry_interval = config.get('retry_interval', 1)
        self.username = config.get('username', 'hadoop')  # 默认用户名
        self.verify_ssl = config.get('verify_ssl', False)  # 默认不验证SSL证书
        self.logger = logger
        
        # 创建HTTP客户端
        self.http_client = HttpClient()
        
        # 配置SSL验证
        self.http_client.session.verify = self.verify_ssl
        
        # 如果不验证SSL证书，则禁用SSL警告
        if not self.verify_ssl:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def set_logger(self, logger: logging.Logger) -> None:
        """
        设置日志记录器
        
        Args:
            logger: 日志记录器实例
        """
        self.logger = logger

    def _make_request(self, method: str, endpoint: str, **kwargs):
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
        
        # 添加user.name参数到params
        params = kwargs.get('params', {})
        if 'user.name' not in params:
            params['user.name'] = self.username
        
        # 设置请求参数
        request_kwargs = {
            'timeout': self.timeout,
            'params': params
        }
        
        # 添加其他参数（如headers, data等）
        for key, value in kwargs.items():
            if key != 'params' and key != 'verify':  # params和verify已经处理过了
                request_kwargs[key] = value
        
        try:
            response = self.http_client.request(method, url, **request_kwargs)
            return response
        except Exception as e:
            self.logger.error(f"Request failed: {str(e)}")
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