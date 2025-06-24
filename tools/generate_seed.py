#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
简化种子生成器
支持生成高质量的随机种子并直接注入到.bashrc实现永久生效
"""

import secrets
import base64
import argparse
import os
import subprocess

def generate_seed(length: int = 32) -> str:
    """
    生成随机种子
    
    Args:
        length: 种子长度（字节）
        
    Returns:
        str: Base64编码的种子
    """
    seed_bytes = secrets.token_bytes(length)
    return base64.b64encode(seed_bytes).decode('utf-8')

def inject_to_bashrc(seed: str) -> bool:
    """
    将种子注入到.bashrc文件中实现永久生效
    
    Args:
        seed: 种子值
        
    Returns:
        bool: 注入是否成功
    """
    try:
        bashrc_path = os.path.expanduser("~/.bashrc")
        env_line = f'export AUTOEVS_CRYPTO_SEED="{seed}"\n'
        
        # 检查是否已存在该环境变量
        existing_found = False
        if os.path.exists(bashrc_path):
            with open(bashrc_path, 'r') as f:
                content = f.read()
                if 'AUTOEVS_CRYPTO_SEED' in content:
                    existing_found = True
        
        if existing_found:
            print("⚠️  检测到.bashrc中已存在AUTOEVS_CRYPTO_SEED环境变量")
            response = input("是否要覆盖现有种子？(y/N): ").strip().lower()
            if response not in ['y', 'yes']:
                print("❌ 操作已取消")
                return False
            
            # 移除旧的环境变量行
            with open(bashrc_path, 'r') as f:
                lines = f.readlines()
            
            with open(bashrc_path, 'w') as f:
                for line in lines:
                    if 'AUTOEVS_CRYPTO_SEED' not in line:
                        f.write(line)
        
        # 添加新的环境变量
        with open(bashrc_path, 'a') as f:
            f.write(env_line)
        
        # 重新加载.bashrc
        try:
            subprocess.run(['source', bashrc_path], shell=True, check=True)
        except:
            # 如果source失败，提示用户手动执行
            pass
        
        # 设置当前Python进程的环境变量
        os.environ['AUTOEVS_CRYPTO_SEED'] = seed
        
        print(f"✅ 种子已成功注入到 {bashrc_path}")
        print("💡 请运行以下命令使环境变量在当前会话中生效:")
        print(f"   source ~/.bashrc")
        print("   或者重新打开终端")
        
        return True
        
    except Exception as e:
        print(f"❌ 注入失败: {e}")
        return False

def set_environment_variable(seed: str) -> bool:
    """
    设置环境变量到当前shell（临时）
    
    Args:
        seed: 种子值
        
    Returns:
        bool: 设置是否成功
    """
    import tempfile
    
    # 设置当前Python进程的环境变量
    os.environ['AUTOEVS_CRYPTO_SEED'] = seed
    
    # 生成shell脚本供用户source
    script_content = f'export AUTOEVS_CRYPTO_SEED="{seed}"\n'
    
    # 写入临时文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
        f.write(script_content)
        script_path = f.name
    
    print(f"📄 已生成环境变量脚本: {script_path}")
    print(f"💡 请运行: source {script_path}")
    print("   或者手动执行:")
    print(f"   export AUTOEVS_CRYPTO_SEED='{seed}'")
    
    return True

def main():
    parser = argparse.ArgumentParser(description="AutoEVS 种子生成器")
    parser.add_argument('--length', type=int, default=32, 
                       help="种子长度（字节），默认32")
    parser.add_argument('--show-only', action='store_true',
                       help="只显示种子，不设置环境变量")
    parser.add_argument('--permanent', action='store_true',
                       help="永久注入到.bashrc文件中")
    
    args = parser.parse_args()
    
    print("🔑 生成加密种子...")
    seed = generate_seed(args.length)
    
    print(f"✅ 种子生成完成:")
    print(f"📋 种子: {seed}")
    print()
    
    if args.show_only:
        print("💡 手动设置环境变量:")
        print(f"   export AUTOEVS_CRYPTO_SEED='{seed}'")
    elif args.permanent:
        print("🔧 永久注入到.bashrc文件...")
        inject_to_bashrc(seed)
    else:
        print("🔧 设置临时环境变量...")
        set_environment_variable(seed)
    
    print()
    print("⚠️  注意事项:")
    print("   1. 请妥善保管此种子")
    print("   2. 种子丢失后可重新生成，然后重新加密密码")
    print("   3. 不同环境建议使用不同种子")

if __name__ == "__main__":
    main() 