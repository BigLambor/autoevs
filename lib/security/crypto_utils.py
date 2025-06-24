#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import base64
import logging
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)

def load_seed_from_env() -> str:
    """从环境变量加载种子"""
    return os.getenv('AUTOEVS_CRYPTO_SEED')

def create_cipher(seed: str) -> Fernet:
    """根据种子创建加密器"""
    if not seed:
        raise ValueError("种子不能为空")
    
    # 使用PBKDF2从种子生成密钥
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b'autoevs_salt_2024',
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(seed.encode()))
    return Fernet(key)

def encrypt_password(password: str, seed: str) -> str:
    """
    加密密码
    
    Args:
        password: 明文密码
        seed: 加密种子
        
    Returns:
        str: 加密后的密码，格式为 ENCRYPTED:base64_encrypted_data
    """
    if not password:
        return password
    
    try:
        cipher = create_cipher(seed)
        encrypted_bytes = cipher.encrypt(password.encode())
        encrypted_b64 = base64.b64encode(encrypted_bytes).decode()
        return f"ENCRYPTED:{encrypted_b64}"
    except Exception as e:
        logger.error(f"密码加密失败: {str(e)}")
        raise

def decrypt_password(encrypted_password: str, seed: str) -> str:
    """
    解密密码
    
    Args:
        encrypted_password: 加密的密码
        seed: 解密种子
        
    Returns:
        str: 明文密码
    """
    if not encrypted_password:
        return encrypted_password
    
    # 如果不是加密密码，直接返回
    if not encrypted_password.startswith('ENCRYPTED:'):
        return encrypted_password
    
    try:
        encrypted_b64 = encrypted_password[10:]  # 移除 'ENCRYPTED:' 前缀
        encrypted_bytes = base64.b64decode(encrypted_b64)
        
        cipher = create_cipher(seed)
        decrypted_bytes = cipher.decrypt(encrypted_bytes)
        return decrypted_bytes.decode()
    except Exception as e:
        logger.error(f"密码解密失败: {str(e)}")
        raise

def is_encrypted_password(value: str) -> bool:
    """
    判断值是否为加密密码
    
    Args:
        value: 要检查的值
        
    Returns:
        bool: True表示是加密密码，False表示不是
    """
    if not isinstance(value, str):
        return False
    
    if not value.startswith('ENCRYPTED:'):
        return False
    
    # 检查加密值格式（base64）
    try:
        encrypted_part = value[10:]  # 移除 'ENCRYPTED:' 前缀
        base64.b64decode(encrypted_part)
        return True
    except:
        return False

def validate_seed(seed: str) -> bool:
    """
    验证种子质量
    
    Args:
        seed: 要验证的种子
        
    Returns:
        bool: True表示种子有效，False表示无效
    """
    if not seed or not isinstance(seed, str):
        return False
    
    # 种子长度应该足够长
    if len(seed) < 16:
        return False
    
    # 可以尝试创建加密器来验证种子
    try:
        create_cipher(seed)
        return True
    except:
        return False 