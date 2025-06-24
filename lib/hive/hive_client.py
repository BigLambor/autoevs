#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import tempfile
import logging
from typing import Dict, Any, Optional, Tuple
from ..os.os_client import OSClient

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HiveClient:
    """Hive 命令执行客户端"""
    
    def __init__(self, config: Dict[str, Any], os_client: Optional[OSClient] = None, kerberos_client=None):
        """
        初始化 Hive 客户端
        
        Args:
            config: Hive配置字典，包含以下字段：
                - hive_cmd: Hive命令路径
                - host: Hive服务器主机名
                - port: Hive服务器端口
                - username: 用户名
                - password: 密码
                - properties: 其他Hive属性
                - enable_kerberos: 是否启用Kerberos认证，默认False
            os_client: 操作系统命令执行客户端，如果为None则创建新的实例
            kerberos_client: Kerberos客户端实例，用于认证
        """
        self.config = config
        # 优先从环境变量获取 hive_cmd，其次从配置文件获取，最后使用默认值
        self.hive_cmd = os.environ.get('HIVE_CMD') or self.config.get('hive_cmd', 'hive')
        self.host = self.config.get('host', 'localhost')
        self.port = self.config.get('port', 10000)
        self.username = self.config.get('username')
        self.password = self.config.get('password')
        self.properties = self.config.get('properties', {})
        self.enable_kerberos = self.config.get('enable_kerberos', False)
        self.kerberos_client = kerberos_client
        
        self.logger = logger
        
        # 使用传入的OSClient或创建新的
        self.os_client = os_client or OSClient({
            'timeout': self.config.get('timeout', 300),
            'work_dir': self.config.get('work_dir', '/tmp'),
            'user': self.config.get('user'),
            'group': self.config.get('group')
        })
        
        # 如果启用Kerberos但没有提供kerberos_client，尝试创建
        if self.enable_kerberos and not self.kerberos_client:
            try:
                from lib.kerberos.kerberos_client import KerberosClient
                kerberos_config = self.config.get('kerberos', {})
                if kerberos_config:
                    self.kerberos_client = KerberosClient(kerberos_config, self.os_client)
                else:
                    self.logger.warning("启用了Kerberos但未提供Kerberos配置")
                    self.enable_kerberos = False
            except Exception as e:
                self.logger.warning(f"创建Kerberos客户端失败: {str(e)}")
                self.enable_kerberos = False
        
    def set_logger(self, logger: logging.Logger) -> None:
        """
        设置日志记录器
        
        Args:
            logger: 日志记录器实例
        """
        self.logger = logger
        if self.os_client:
            self.os_client.logger = logger
        if self.kerberos_client:
            self.kerberos_client.set_logger(logger)
        
    def _ensure_authenticated(self) -> bool:
        """
        确保Kerberos认证有效（如果启用）
        
        Returns:
            bool: 认证是否成功
        """
        if not self.enable_kerberos:
            return True
            
        if not self.kerberos_client:
            self.logger.error("启用了Kerberos但没有Kerberos客户端")
            return False
            
        return self.kerberos_client.ensure_authenticated()
        
    def _build_hive_cmd(self, sql_file: str) -> str:
        """
        构建Hive命令
        
        Args:
            sql_file: SQL文件路径
            
        Returns:
            str: 完整的Hive命令
        """
        cmd = [self.hive_cmd]
        
        # 如果启用Kerberos，添加相关配置
        if self.enable_kerberos:
            # 使用Kerberos认证时，通常不需要用户名密码
            cmd.extend(['--hiveconf', 'hive.security.authorization.enabled=true'])
            cmd.extend(['--hiveconf', 'hive.security.authenticator.manager=org.apache.hadoop.hive.ql.security.SessionStateUserAuthenticator'])
        else:
            # 添加连接参数
            if self.host:
                cmd.extend(['--hiveconf', f'hive.server2.host={self.host}'])
            if self.port:
                cmd.extend(['--hiveconf', f'hive.server2.port={self.port}'])
            if self.username:
                cmd.extend(['--hiveconf', f'hive.server2.username={self.username}'])
            if self.password:
                cmd.extend(['--hiveconf', f'hive.server2.password={self.password}'])
            
        # 添加其他属性
        for key, value in self.properties.items():
            cmd.extend(['--hiveconf', f'{key}={value}'])
            
        # 添加SQL文件
        cmd.extend(['-f', sql_file])
        
        return ' '.join(cmd)
        
    def execute_sql(self, sql: str, timeout: Optional[int] = None) -> Tuple[int, str]:
        """
        执行 Hive SQL 命令
        
        Args:
            sql: SQL 语句
            timeout: 超时时间（秒）
            
        Returns:
            Tuple[int, str]: (返回码, 输出结果)
            
        Raises:
            Exception: 执行失败时抛出异常
        """
        temp_file = None
        try:
            # 确保Kerberos认证有效
            if not self._ensure_authenticated():
                raise Exception("Kerberos认证失败")
            
            # 创建临时文件
            with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as f:
                temp_file = f.name
                f.write(sql)
            
            # 构建命令
            cmd = self._build_hive_cmd(temp_file)
            
            # 设置环境变量
            env = {}
            if self.enable_kerberos and self.kerberos_client:
                env.update(self.kerberos_client.get_hadoop_env())
            
            # 使用 OSClient 执行命令
            if timeout:
                return_code, stdout, stderr = self.os_client.execute_command_with_timeout(cmd, timeout=timeout, env=env)
            else:
                return_code, stdout, stderr = self.os_client.execute_command(cmd, env=env)
            
            if return_code != 0:
                error_msg = f"Hive 命令执行失败: {stderr}"
                self.logger.error(error_msg)
                raise Exception(error_msg)
            
            return return_code, stdout
            
        except Exception as e:
            self.logger.error(f"执行 Hive 命令时发生错误: {str(e)}")
            raise
            
        finally:
            # 清理临时文件
            if temp_file and os.path.exists(temp_file):
                try:
                    os.unlink(temp_file)
                except Exception as e:
                    self.logger.warning(f"删除临时文件失败: {str(e)}")
                        
    def execute_sql_file(self, sql_file: str, timeout: Optional[int] = None) -> Tuple[int, str]:
        """
        执行 Hive SQL 文件
        
        Args:
            sql_file: SQL 文件路径
            timeout: 超时时间（秒）
            
        Returns:
            Tuple[int, str]: (返回码, 输出结果)
            
        Raises:
            Exception: 执行失败时抛出异常
        """
        try:
            # 确保Kerberos认证有效
            if not self._ensure_authenticated():
                raise Exception("Kerberos认证失败")
            
            # 构建命令
            cmd = self._build_hive_cmd(sql_file)
            
            # 设置环境变量
            env = {}
            if self.enable_kerberos and self.kerberos_client:
                env.update(self.kerberos_client.get_hadoop_env())
            
            # 使用 OSClient 执行命令
            if timeout:
                return_code, stdout, stderr = self.os_client.execute_command_with_timeout(cmd, timeout=timeout, env=env)
            else:
                return_code, stdout, stderr = self.os_client.execute_command(cmd, env=env)
            
            if return_code != 0:
                error_msg = f"Hive 命令执行失败: {stderr}"
                self.logger.error(error_msg)
                raise Exception(error_msg)
            
            return return_code, stdout
            
        except Exception as e:
            self.logger.error(f"执行 Hive 命令时发生错误: {str(e)}")
            raise
