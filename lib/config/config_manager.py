import os
import yaml
from typing import Dict, Any, Optional

class ConfigManager:
    def __init__(self, env: Optional[str] = None):
        """
        初始化配置管理器
        :param env: 环境名称 (dev/test/prod)，如果为None则从环境变量获取
        """
        self.env = env or os.getenv('AUTOEVS_ENV', 'prod')
        if self.env not in ['dev', 'test', 'prod']:
            raise ValueError(f"不支持的环境: {self.env}，必须是 dev/test/prod 之一")
            
        self.config_dir = os.path.join("config", self.env)
        self.configs: Dict[str, Dict[str, Any]] = {}
        self._load_configs()

    def _load_configs(self):
        """加载指定环境下的所有配置文件"""
        if not os.path.exists(self.config_dir):
            raise ValueError(f"配置目录不存在: {self.config_dir}")

        for filename in os.listdir(self.config_dir):
            if filename.endswith('.yaml'):
                component_name = filename[:-5]  # 移除.yaml后缀
                config_path = os.path.join(self.config_dir, filename)
                with open(config_path, 'r', encoding='utf-8') as f:
                    self.configs[component_name] = yaml.safe_load(f)

    def get_component_config(self, component_name: str, instance_name: Optional[str] = None) -> Dict[str, Any]:
        """
        获取组件配置
        :param component_name: 组件名称
        :param instance_name: 实例名称（可选）
        :return: 组件配置字典
        """
        if component_name not in self.configs:
            raise ValueError(f"未找到组件配置: {component_name}")

        config = self.configs[component_name]
        
        if instance_name:
            if 'instances' not in config:
                raise ValueError(f"组件 {component_name} 不支持多实例配置")
            if instance_name not in config['instances']:
                raise ValueError(f"未找到组件 {component_name} 的实例: {instance_name}")
            return config['instances'][instance_name]
        
        return config

    def get_all_instances(self, component_name: str) -> Dict[str, Dict[str, Any]]:
        """
        获取组件的所有实例配置
        :param component_name: 组件名称
        :return: 所有实例的配置字典
        """
        if component_name not in self.configs:
            raise ValueError(f"未找到组件配置: {component_name}")
        
        config = self.configs[component_name]
        return config.get('instances', {}) 