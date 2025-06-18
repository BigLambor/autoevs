#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import logging
import sys
import time
from typing import Any, Dict, Optional
import inspect
import signal
import os
import logging.handlers
from lib.config.config_manager import ConfigManager

class ScriptTemplate:
    """脚本模板基类，提供基础功能框架"""
    
    def __init__(self, env: Optional[str] = None):
        """
        初始化脚本模板
        
        Args:
            env: 环境名称 (dev/test/prod)，如果为None则使用默认环境
        """
        # 先创建配置管理器
        self.config_manager = ConfigManager(env=env)
        self.env = self.config_manager.env
            
        # 然后设置日志
        self.logger = self._setup_logger()
        
    def _setup_logger(self) -> logging.Logger:
        """配置日志"""
        logger = logging.getLogger(self.__class__.__name__)
        
        # 避免重复添加处理器
        if not logger.handlers:
            logger.setLevel(logging.INFO)
            
            # 创建日志目录
            log_dir = os.path.join("logs", self.env)
            os.makedirs(log_dir, exist_ok=True)
            
            # 创建文件处理器（带轮转）
            log_file = os.path.join(log_dir, f"{self.__class__.__name__}.log")
            file_handler = logging.handlers.RotatingFileHandler(
                filename=log_file,
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5,          # 保留5个备份文件
                encoding='utf-8'
            )
            file_handler.setLevel(logging.INFO)
            
            # 创建控制台处理器
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            
            # 设置日志格式
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)
            
            # 添加处理器
            logger.addHandler(file_handler)
            logger.addHandler(console_handler)
            
            # 记录日志初始化信息
            logger.info(f"日志系统初始化完成，日志文件: {log_file}")
            logger.info(f"日志轮转配置: 最大文件大小 10MB，保留 5 个备份文件")
        
        return logger
    
    def get_component_config(self, component_name: str, instance_name: Optional[str] = None) -> Dict[str, Any]:
        """
        获取组件配置
        
        Args:
            component_name: 组件名称
            instance_name: 实例名称（可选）
            
        Returns:
            Dict[str, Any]: 组件配置
        """
        try:
            return self.config_manager.get_component_config(component_name, instance_name)
        except Exception as e:
            self.logger.error(f"获取组件 {component_name} 配置失败: {str(e)}")
            raise
    
    def get_all_instances(self, component_name: str) -> Dict[str, Dict[str, Any]]:
        """
        获取组件的所有实例配置
        
        Args:
            component_name: 组件名称
            
        Returns:
            Dict[str, Dict[str, Any]]: 所有实例的配置字典
        """
        try:
            return self.config_manager.get_all_instances(component_name)
        except Exception as e:
            self.logger.error(f"获取组件 {component_name} 的所有实例配置失败: {str(e)}")
            raise
    
    def run_function(self, function_name: str, **kwargs) -> Dict[str, Any]:
        """
        通过反射执行指定的函数
        
        Args:
            function_name: 要执行的函数名
            **kwargs: 传递给函数的参数
            
        Returns:
            Dict[str, Any]: 执行结果
            
        Raises:
            AttributeError: 当指定的函数不存在时
        """
        if not hasattr(self, function_name):
            raise AttributeError(f"函数 {function_name} 不存在")
        
        function = getattr(self, function_name)
        
        # 获取函数签名
        sig = inspect.signature(function)
        
        # 验证参数
        try:
            bound_args = sig.bind(**kwargs)
            bound_args.apply_defaults()
        except TypeError as e:
            raise ValueError(f"函数 {function_name} 参数错误: {str(e)}")
        
        start_time = time.time()
        
        try:
            result = function(**kwargs)
            
            execution_time = time.time() - start_time
            self.logger.info(f"函数 {function_name} 执行完成，耗时: {execution_time:.2f}秒")
            
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"函数 {function_name} 执行失败，耗时: {execution_time:.2f}秒")
            raise

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='脚本模板')
    parser.add_argument('--run', type=str, required=True, metavar='FUNCTION',
                      help='要执行的函数名 (例如: --run=function1)')
    parser.add_argument('--env', type=str, choices=['dev', 'test', 'prod'],
                      help='环境名称 (dev/test/prod)')
    parser.add_argument('--debug', action='store_true',
                      help='启用调试模式')
    
    return parser.parse_args()

def main():
    """主函数"""
    def signal_handler(signum, frame):
        print("\n正在优雅退出...")
        sys.exit(0)
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    args = parse_args()
    
    # 创建脚本实例
    script = ScriptTemplate(env=args.env)
    
    # 如果启用调试模式，设置日志级别为DEBUG
    if args.debug:
        script.logger.setLevel(logging.DEBUG)
    
    try:
        # 执行指定的函数
        result = script.run_function(args.run)
        script.logger.info(f"执行结果: {result}")
    except Exception as e:
        script.logger.error(f"执行失败: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()