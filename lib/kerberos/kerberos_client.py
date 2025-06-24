#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import time
import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import re

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KerberosClient:
    """Kerberos认证管理客户端"""
    
    def __init__(self, config: Dict[str, Any], os_client=None):
        """
        初始化Kerberos客户端
        
        Args:
            config: Kerberos配置字典，包含以下字段：
                - principal: Kerberos主体（用户名@REALM）
                - keytab_path: keytab文件路径（可选）
                - password: 密码（可选，如果没有keytab）
                - realm: Kerberos域
                - kdc: KDC服务器地址（可选）
                - ticket_lifetime: 票据生存时间（小时，默认24）
                - renew_threshold: 自动续期阈值（小时，默认4）
            os_client: OS客户端实例，用于执行命令
        """
        self.config = config
        self.principal = config.get('principal')
        self.keytab_path = config.get('keytab_path')
        self.password = config.get('password')
        self.realm = config.get('realm')
        self.kdc = config.get('kdc')
        self.ticket_lifetime = config.get('ticket_lifetime', 24)  # 小时
        self.renew_threshold = config.get('renew_threshold', 4)   # 小时
        
        if not self.principal:
            raise ValueError("principal参数不能为空")
            
        if not self.keytab_path and not self.password:
            raise ValueError("必须提供keytab_path或password")
        
        self.logger = logger
        
        # 使用传入的OSClient或创建新的
        if not os_client:
            from lib.os.os_client import OSClient
            os_client = OSClient({
                'timeout': 300,
                'work_dir': '/tmp'
            })
        self.os_client = os_client
        
        # 初始化认证
        self._last_auth_time = None
        
    def set_logger(self, logger: logging.Logger) -> None:
        """设置日志记录器"""
        self.logger = logger
        if self.os_client:
            self.os_client.logger = logger
            
    def kinit(self, force: bool = False) -> bool:
        """
        执行kinit认证
        
        Args:
            force: 是否强制重新认证
            
        Returns:
            bool: 认证是否成功
        """
        try:
            # 检查是否需要认证
            if not force and self.is_authenticated():
                self.logger.info("Kerberos票据仍然有效，跳过认证")
                return True
                
            self.logger.info(f"开始Kerberos认证，主体: {self.principal}")
            
            if self.keytab_path:
                # 使用keytab认证
                command = f"kinit -kt {self.keytab_path} {self.principal}"
            else:
                # 使用密码认证（不推荐在生产环境使用）
                command = f"echo '{self.password}' | kinit {self.principal}"
                
            return_code, stdout, stderr = self.os_client.execute_command(command)
            
            if return_code == 0:
                self._last_auth_time = datetime.now()
                self.logger.info("Kerberos认证成功")
                return True
            else:
                error_msg = f"Kerberos认证失败: {stderr}"
                self.logger.error(error_msg)
                return False
                
        except Exception as e:
            self.logger.error(f"执行kinit时发生错误: {str(e)}")
            return False
            
    def klist(self) -> Tuple[bool, Dict[str, Any]]:
        """
        检查当前Kerberos票据状态
        
        Returns:
            Tuple[bool, Dict[str, Any]]: (是否有有效票据, 票据信息)
        """
        try:
            command = "klist -s"
            return_code, stdout, stderr = self.os_client.execute_command(command)
            
            if return_code == 0:
                # 获取详细票据信息
                command = "klist"
                return_code, stdout, stderr = self.os_client.execute_command(command)
                ticket_info = self._parse_klist_output(stdout)
                return True, ticket_info
            else:
                return False, {}
                
        except Exception as e:
            self.logger.error(f"执行klist时发生错误: {str(e)}")
            return False, {}
            
    def is_authenticated(self) -> bool:
        """
        检查是否已认证且票据有效
        
        Returns:
            bool: 是否已认证
        """
        try:
            has_ticket, ticket_info = self.klist()
            if not has_ticket:
                return False
                
            # 检查票据是否即将过期
            if 'expires' in ticket_info:
                expires_time = ticket_info['expires']
                current_time = datetime.now()
                time_until_expiry = expires_time - current_time
                
                # 如果票据在renew_threshold小时内过期，认为需要重新认证
                if time_until_expiry.total_seconds() < self.renew_threshold * 3600:
                    self.logger.warning(f"Kerberos票据将在 {time_until_expiry} 后过期，需要重新认证")
                    return False
                    
            return True
            
        except Exception as e:
            self.logger.error(f"检查认证状态时发生错误: {str(e)}")
            return False
            
    def ensure_authenticated(self) -> bool:
        """
        确保已认证，如果未认证则自动认证
        
        Returns:
            bool: 认证是否成功
        """
        if self.is_authenticated():
            return True
        else:
            return self.kinit()
            
    def kdestroy(self) -> bool:
        """
        销毁Kerberos票据
        
        Returns:
            bool: 是否成功
        """
        try:
            command = "kdestroy"
            return_code, stdout, stderr = self.os_client.execute_command(command)
            
            if return_code == 0:
                self._last_auth_time = None
                self.logger.info("Kerberos票据已销毁")
                return True
            else:
                self.logger.error(f"销毁Kerberos票据失败: {stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"执行kdestroy时发生错误: {str(e)}")
            return False
            
    def _parse_klist_output(self, output: str) -> Dict[str, Any]:
        """
        解析klist命令输出
        
        Args:
            output: klist命令输出
            
        Returns:
            Dict[str, Any]: 解析后的票据信息
        """
        ticket_info = {}
        
        try:
            lines = output.strip().split('\n')
            
            for line in lines:
                line = line.strip()
                
                # 解析主体
                if 'Default principal:' in line:
                    ticket_info['principal'] = line.split(':', 1)[1].strip()
                    
                # 解析过期时间
                elif 'Valid starting' in line and 'Expires' in line:
                    # 格式: Valid starting     Expires            Service principal
                    # 示例: 12/01/23 10:00:00  12/02/23 10:00:00  krbtgt/REALM@REALM
                    parts = line.split()
                    if len(parts) >= 4:
                        try:
                            expires_str = f"{parts[2]} {parts[3]}"
                            # 尝试解析时间格式
                            expires_time = datetime.strptime(expires_str, "%m/%d/%y %H:%M:%S")
                            ticket_info['expires'] = expires_time
                        except ValueError:
                            pass
                            
                # 解析票据缓存位置
                elif 'Ticket cache:' in line:
                    ticket_info['cache'] = line.split(':', 1)[1].strip()
                    
        except Exception as e:
            self.logger.warning(f"解析klist输出失败: {str(e)}")
            
        return ticket_info
        
    def get_hadoop_env(self) -> Dict[str, str]:
        """
        获取Hadoop相关的环境变量
        
        Returns:
            Dict[str, str]: 环境变量字典
        """
        env = {}
        
        # 设置Kerberos相关环境变量
        if self.realm:
            env['KRB5_REALM'] = self.realm
            
        if self.kdc:
            env['KRB5_KDC'] = self.kdc
            
        # 设置Hadoop安全相关环境变量
        env['HADOOP_SECURITY_AUTHENTICATION'] = 'kerberos'
        env['HADOOP_SECURITY_AUTHORIZATION'] = 'true'
        
        return env 