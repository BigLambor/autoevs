#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import yaml
import getpass
import argparse
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from lib.security.crypto_utils import encrypt_password, load_seed_from_env, is_encrypted_password
from lib.security.field_detector import should_decrypt_field

class PasswordEncryptor:
    """密码加密工具"""
    
    def __init__(self):
        self.seed = load_seed_from_env()
        if not self.seed:
            print("❌ 未找到加密种子")
            print("   请先生成种子: python tools/generate_seed.py")
            print("   然后设置环境变量: export AUTOEVS_CRYPTO_SEED='your_seed'")
            sys.exit(1)
        print("✅ 已加载加密种子")
    
    def encrypt_single_password(self) -> str:
        """
        加密单个密码
        
        Returns:
            str: 加密后的密码
        """
        print("🔐 密码加密工具")
        print("输入要加密的密码（输入时不会显示）:")
        
        password = getpass.getpass("密码: ")
        if not password:
            print("❌ 密码不能为空")
            return None
        
        try:
            encrypted = encrypt_password(password, self.seed)
            print(f"✅ 加密完成")
            print(f"📋 密文: {encrypted}")
            print(f"💡 请将此密文复制到配置文件中")
            return encrypted
        except Exception as e:
            print(f"❌ 加密失败: {str(e)}")
            return None
    
    def encrypt_config_file(self, config_file: str, password_fields: list = None, 
                          dry_run: bool = False) -> bool:
        """
        加密配置文件中的密码字段
        
        Args:
            config_file: 配置文件路径
            password_fields: 密码字段列表（可选）
            dry_run: 是否为预览模式
            
        Returns:
            bool: 操作是否成功
        """
        print(f"🔧 处理配置文件: {config_file}")
        
        if not os.path.exists(config_file):
            print(f"❌ 配置文件不存在: {config_file}")
            return False
        
        try:
            # 读取配置文件
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            if not config:
                print("⚠️  配置文件为空或格式错误")
                return False
            
            # 备份原文件（非预览模式）
            if not dry_run:
                backup_file = f"{config_file}.backup"
                with open(config_file, 'r', encoding='utf-8') as src:
                    with open(backup_file, 'w', encoding='utf-8') as dst:
                        dst.write(src.read())
                print(f"📄 原文件已备份: {backup_file}")
            
            # 扫描并加密密码字段
            changes = []
            
            def process_dict(data, path=""):
                if isinstance(data, dict):
                    for key, value in data.items():
                        if key.startswith('_'):  # 跳过元数据
                            continue
                            
                        current_path = f"{path}.{key}" if path else key
                        
                        if isinstance(value, str):
                            # 检查是否为需要加密的密码字段
                            if self._should_encrypt_field(key, value, password_fields):
                                print(f"\n🔍 发现密码字段: {current_path}")
                                print(f"   当前值: {'*' * min(len(value), 8)}")  # 脱敏显示
                                
                                if not dry_run:
                                    choice = input("是否加密此字段? (y/n/q): ").strip().lower()
                                    if choice == 'q':
                                        return False
                                    elif choice == 'y':
                                        try:
                                            encrypted = encrypt_password(value, self.seed)
                                            data[key] = encrypted
                                            changes.append(f"{current_path}: [已加密]")
                                            print(f"✅ 已加密: {current_path}")
                                        except Exception as e:
                                            print(f"❌ 加密失败: {str(e)}")
                                            return False
                                else:
                                    # 预览模式
                                    changes.append(f"{current_path}: [将被加密]")
                        elif isinstance(value, (dict, list)):
                            if not process_dict(value, current_path):
                                return False
                elif isinstance(data, list):
                    for i, item in enumerate(data):
                        item_path = f"{path}[{i}]"
                        if not process_dict(item, item_path):
                            return False
                return True
            
            # 处理配置
            if process_dict(config):
                if changes:
                    print(f"\n📊 处理结果:")
                    print(f"   发现 {len(changes)} 个密码字段")
                    for change in changes:
                        print(f"   - {change}")
                    
                    if not dry_run:
                        # 写入加密后的配置
                        with open(config_file, 'w', encoding='utf-8') as f:
                            yaml.dump(config, f, default_flow_style=False, 
                                    allow_unicode=True, indent=2)
                        print(f"✅ 配置文件已更新: {config_file}")
                    else:
                        print("ℹ️  预览模式，未实际修改文件")
                else:
                    print("ℹ️  没有发现需要加密的密码字段")
                
                return True
            else:
                print("❌ 用户取消操作")
                return False
                
        except Exception as e:
            print(f"❌ 处理配置文件时出错: {str(e)}")
            return False
    
    def _should_encrypt_field(self, field_name: str, field_value: str, 
                            custom_fields: list = None) -> bool:
        """
        判断字段是否应该加密
        
        Args:
            field_name: 字段名
            field_value: 字段值
            custom_fields: 自定义密码字段列表
            
        Returns:
            bool: 是否应该加密
        """
        # 如果已经是加密字段，跳过
        if is_encrypted_password(field_value):
            return False
        
        # 如果指定了自定义字段列表，优先使用
        if custom_fields:
            return field_name in custom_fields
        
        # 使用智能检测
        from lib.security.field_detector import is_password_field
        return is_password_field(field_name)
    
    def batch_encrypt_configs(self, config_pattern: str, **kwargs) -> bool:
        """
        批量加密配置文件
        
        Args:
            config_pattern: 配置文件模式（支持通配符）
            **kwargs: 其他参数
            
        Returns:
            bool: 操作是否成功
        """
        import glob
        
        config_files = glob.glob(config_pattern)
        if not config_files:
            print(f"❌ 未找到匹配的配置文件: {config_pattern}")
            return False
        
        print(f"📁 找到 {len(config_files)} 个配置文件")
        
        success_count = 0
        for config_file in config_files:
            print(f"\n{'='*50}")
            if self.encrypt_config_file(config_file, **kwargs):
                success_count += 1
        
        print(f"\n📊 批量处理完成:")
        print(f"   总计: {len(config_files)} 个文件")
        print(f"   成功: {success_count} 个文件")
        print(f"   失败: {len(config_files) - success_count} 个文件")
        
        return success_count == len(config_files)

def main():
    parser = argparse.ArgumentParser(description="AutoEVS 密码加密工具")
    parser.add_argument('--mode', choices=['single', 'config', 'batch'], 
                       default='single', help="加密模式")
    parser.add_argument('--config', help="配置文件路径")
    parser.add_argument('--pattern', help="配置文件模式（批量模式）")
    parser.add_argument('--fields', nargs='+', 
                       help="指定密码字段名称（覆盖自动检测）")
    parser.add_argument('--dry-run', action='store_true', 
                       help="预览模式，不实际修改文件")
    
    args = parser.parse_args()
    
    try:
        encryptor = PasswordEncryptor()
        
        if args.mode == 'single':
            encryptor.encrypt_single_password()
            
        elif args.mode == 'config':
            if not args.config:
                print("❌ 请指定配置文件路径: --config path/to/config.yaml")
                sys.exit(1)
            encryptor.encrypt_config_file(args.config, args.fields, args.dry_run)
            
        elif args.mode == 'batch':
            if not args.pattern:
                # 默认处理所有环境的配置文件
                args.pattern = "config/*/*.yaml"
            encryptor.batch_encrypt_configs(args.pattern, 
                                          password_fields=args.fields,
                                          dry_run=args.dry_run)
        
    except KeyboardInterrupt:
        print("\n❌ 操作被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 程序执行出错: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 