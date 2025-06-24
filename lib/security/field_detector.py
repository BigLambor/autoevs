#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import logging
from typing import Dict, List, Set

logger = logging.getLogger(__name__)

class PasswordFieldDetector:
    """密码字段检测器"""
    
    def __init__(self):
        # 密码字段模式（正则表达式）
        self.password_patterns = [
            r'.*password.*',
            r'.*passwd.*',
            r'.*secret.*',
            r'.*key$',  # 以key结尾，但不包括key_id等
            r'.*token.*',
            r'.*credential.*',
            r'.*auth.*password.*',
            r'.*admin.*password.*',
            r'.*root.*password.*',
            r'.*db.*password.*',
            r'.*database.*password.*',
        ]
        
        # 编译正则表达式
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) 
                                for pattern in self.password_patterns]
        
        # 明确的密码字段名称（精确匹配）
        self.exact_password_fields = {
            'password', 'passwd', 'secret', 'key', 'token',
            'metastore_password', 'admin_password', 'root_password',
            'mysql_password', 'hive_password', 'ambari_password'
        }
        
        # 排除字段（即使匹配模式也不认为是密码）
        self.excluded_fields = {
            'password_policy', 'password_length', 'password_complexity',
            'password_min_length', 'password_max_length', 'password_rules',
            'key_id', 'key_type', 'public_key', 'ssh_key_path', 'key_path',
            'token_type', 'token_expiry', 'secret_type', 'secret_path',
            'password_file', 'keystore_file', 'truststore_file'
        }
    
    def is_password_field(self, field_name: str) -> bool:
        """
        判断字段名是否为密码字段
        
        Args:
            field_name: 字段名称
            
        Returns:
            bool: True表示是密码字段，False表示不是
        """
        if not field_name or not isinstance(field_name, str):
            return False
        
        field_lower = field_name.lower()
        
        # 检查排除列表
        if field_lower in self.excluded_fields:
            return False
        
        # 检查精确匹配
        if field_lower in self.exact_password_fields:
            return True
        
        # 检查模式匹配
        return any(pattern.match(field_name) for pattern in self.compiled_patterns)
    
    def is_encrypted_value(self, value: str) -> bool:
        """
        判断值是否为加密值
        
        Args:
            value: 要检查的值
            
        Returns:
            bool: True表示是加密值，False表示不是
        """
        if not isinstance(value, str):
            return False
        
        # 检查加密前缀
        if not value.startswith('ENCRYPTED:'):
            return False
        
        # 检查加密值格式（base64）
        encrypted_part = value[10:]  # 移除 'ENCRYPTED:' 前缀
        if not encrypted_part:
            return False
        
        try:
            import base64
            base64.b64decode(encrypted_part)
            return True
        except:
            return False
    
    def should_decrypt(self, field_name: str, field_value: str) -> bool:
        """
        综合判断是否应该解密此字段
        
        Args:
            field_name: 字段名称
            field_value: 字段值
            
        Returns:
            bool: True表示应该解密，False表示不应该解密
        """
        return (self.is_password_field(field_name) and 
                self.is_encrypted_value(field_value))
    
    def scan_config(self, config: Dict, path: str = "") -> List[str]:
        """
        扫描配置中所有需要解密的字段路径
        
        Args:
            config: 配置字典
            path: 当前路径
            
        Returns:
            List[str]: 需要解密的字段路径列表
        """
        encrypted_fields = []
        
        def scan_dict(data, current_path=""):
            if isinstance(data, dict):
                for key, value in data.items():
                    if key.startswith('_'):  # 跳过元数据字段
                        continue
                        
                    field_path = f"{current_path}.{key}" if current_path else key
                    
                    if isinstance(value, str) and self.should_decrypt(key, value):
                        encrypted_fields.append(field_path)
                        logger.debug(f"发现加密字段: {field_path}")
                    elif isinstance(value, (dict, list)):
                        scan_dict(value, field_path)
            elif isinstance(data, list):
                for i, item in enumerate(data):
                    item_path = f"{current_path}[{i}]"
                    scan_dict(item, item_path)
        
        scan_dict(config, path)
        return encrypted_fields
    
    def add_password_field(self, field_name: str):
        """
        添加自定义密码字段
        
        Args:
            field_name: 字段名称
        """
        self.exact_password_fields.add(field_name.lower())
        logger.info(f"添加自定义密码字段: {field_name}")
    
    def add_excluded_field(self, field_name: str):
        """
        添加排除字段
        
        Args:
            field_name: 字段名称
        """
        self.excluded_fields.add(field_name.lower())
        logger.info(f"添加排除字段: {field_name}")

# 全局检测器实例
_detector = PasswordFieldDetector()

def should_decrypt_field(field_name: str, field_value: str) -> bool:
    """
    便捷函数：判断字段是否需要解密
    
    Args:
        field_name: 字段名称
        field_value: 字段值
        
    Returns:
        bool: True表示需要解密，False表示不需要解密
    """
    return _detector.should_decrypt(field_name, field_value)

def is_password_field(field_name: str) -> bool:
    """
    便捷函数：判断字段名是否为密码字段
    
    Args:
        field_name: 字段名称
        
    Returns:
        bool: True表示是密码字段，False表示不是
    """
    return _detector.is_password_field(field_name)

def scan_encrypted_fields(config: Dict) -> List[str]:
    """
    便捷函数：扫描配置中的加密字段
    
    Args:
        config: 配置字典
        
    Returns:
        List[str]: 加密字段路径列表
    """
    return _detector.scan_config(config) 