import requests
from typing import Any, Dict, Optional, Union, Callable, TypeVar
import time
import functools
import logging
from requests.auth import HTTPBasicAuth
from requests.exceptions import RequestException
import json
from urllib.parse import urljoin
from datetime import datetime, timedelta

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

T = TypeVar('T')

def retry(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    重试装饰器
    
    Args:
        max_retries: 最大重试次数
        delay: 初始延迟时间（秒）
        backoff: 延迟时间的增长因子
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except RequestException as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(f"请求失败，{current_delay}秒后重试: {str(e)}")
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"达到最大重试次数，请求失败: {str(e)}")
                        raise last_exception
            raise last_exception
        return wrapper
    return decorator

def timeout(seconds: float):
    """
    超时装饰器
    
    Args:
        seconds: 超时时间（秒）
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            kwargs['timeout'] = seconds
            return func(*args, **kwargs)
        return wrapper
    return decorator

def log_request_response(log_level: int = logging.INFO):
    """
    日志装饰器
    
    Args:
        log_level: 日志级别
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            start_time = time.time()
            
            # 记录请求信息
            request_info = {
                'method': kwargs.get('method', 'GET'),
                'url': kwargs.get('url', ''),
                'params': kwargs.get('params', {}),
                'data': kwargs.get('data', {}),
                'headers': kwargs.get('headers', {})
            }
            logger.log(log_level, f"请求信息: {json.dumps(request_info, ensure_ascii=False)}")
            
            try:
                response = func(*args, **kwargs)
                end_time = time.time()
                
                # 记录响应信息
                response_info = {
                    'status_code': response.status_code,
                    'elapsed_time': f"{end_time - start_time:.2f}秒",
                    'response': response.text
                }
                logger.log(log_level, f"响应信息: {json.dumps(response_info, ensure_ascii=False)}")
                
                return response
            except Exception as e:
                logger.error(f"请求异常: {str(e)}")
                raise
        return wrapper
    return decorator

class Cache:
    """简单的内存缓存实现"""
    def __init__(self):
        self._cache = {}
    
    def get(self, key: str) -> Optional[Any]:
        if key in self._cache:
            value, expiry = self._cache[key]
            if expiry is None or datetime.now() < expiry:
                return value
            del self._cache[key]
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        expiry = None if ttl is None else datetime.now() + timedelta(seconds=ttl)
        self._cache[key] = (value, expiry)

_cache = Cache()

def cache(ttl: Optional[int] = None):
    """
    缓存装饰器
    
    Args:
        ttl: 缓存时间（秒），None表示永久缓存
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            # 生成缓存键
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # 尝试从缓存获取
            cached_value = _cache.get(cache_key)
            if cached_value is not None:
                logger.info(f"从缓存获取结果: {cache_key}")
                return cached_value
            
            # 执行函数并缓存结果
            result = func(*args, **kwargs)
            _cache.set(cache_key, result, ttl)
            logger.info(f"缓存结果: {cache_key}")
            
            return result
        return wrapper
    return decorator

class HttpClient:
    def __init__(self):
        """初始化HTTP客户端"""
        self.session = requests.Session()

    @retry()
    @log_request_response()
    def request(
        self,
        method: str,
        url: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        auth: Optional[HTTPBasicAuth] = None,
        timeout: int = 30
    ) -> requests.Response:
        """
        发送HTTP请求
        
        Args:
            method: 请求方法（GET, POST等）
            url: 请求URL
            params: URL参数
            data: 表单数据
            json_data: JSON数据
            headers: 请求头
            auth: 认证信息
            timeout: 超时时间（秒）
            
        Returns:
            响应对象
        """
        response = self.session.request(
            method=method,
            url=url,
            params=params,
            data=data,
            json=json_data,
            headers=headers,
            auth=auth,
            timeout=timeout
        )
        response.raise_for_status()
        return response

    def get(
        self,
        url: str,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        auth: Optional[HTTPBasicAuth] = None,
        timeout: int = 30
    ) -> requests.Response:
        """发送GET请求"""
        return self.request('GET', url, params=params, headers=headers, auth=auth, timeout=timeout)

    def post(
        self,
        url: str,
        data: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        auth: Optional[HTTPBasicAuth] = None,
        timeout: int = 30
    ) -> requests.Response:
        """发送POST请求"""
        return self.request('POST', url, data=data, json_data=json_data, headers=headers, auth=auth, timeout=timeout)

    def put(
        self,
        url: str,
        data: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        auth: Optional[HTTPBasicAuth] = None,
        timeout: int = 30
    ) -> requests.Response:
        """发送PUT请求"""
        return self.request('PUT', url, data=data, json_data=json_data, headers=headers, auth=auth, timeout=timeout)

    def delete(
        self,
        url: str,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        auth: Optional[HTTPBasicAuth] = None,
        timeout: int = 30
    ) -> requests.Response:
        """发送DELETE请求"""
        return self.request('DELETE', url, params=params, headers=headers, auth=auth, timeout=timeout) 