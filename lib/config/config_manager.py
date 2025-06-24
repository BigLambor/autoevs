import os
import yaml
from typing import Dict, Any, Optional
from copy import deepcopy

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

    def _merge_config(self, common_config: Dict[str, Any], instance_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        合并common配置和实例配置
        :param common_config: 公共配置
        :param instance_config: 实例配置
        :return: 合并后的配置
        """
        merged_config = deepcopy(common_config)
        merged_config.update(instance_config)
        return merged_config

    def get_component_config(self, component_name: str, instance_name: Optional[str] = None) -> Dict[str, Any]:
        """
        获取组件配置
        :param component_name: 组件名称
        :param instance_name: 实例名称（可选），如果为None则使用default_instance
        :return: 组件配置字典
        """
        if component_name not in self.configs:
            raise ValueError(f"未找到组件配置: {component_name}")

        config = self.configs[component_name]
        
        # 如果没有指定实例名，使用默认实例
        if instance_name is None:
            instance_name = config.get('default_instance')
            if not instance_name:
                # 如果没有default_instance，但有instances，使用第一个实例
                if 'instances' in config and config['instances']:
                    instance_name = list(config['instances'].keys())[0]
                else:
                    # 如果没有instances结构，返回整个配置（向后兼容）
                    return config
        
        # 检查instances结构
        if 'instances' not in config:
            raise ValueError(f"组件 {component_name} 不支持多实例配置")
        if instance_name not in config['instances']:
            raise ValueError(f"未找到组件 {component_name} 的实例: {instance_name}")
        
        # 获取实例配置
        instance_config = config['instances'][instance_name]
        
        # 如果有common配置，合并到实例配置中
        if 'common' in config:
            instance_config = self._merge_config(config['common'], instance_config)
        
        return instance_config

    def get_all_instances(self, component_name: str) -> Dict[str, Dict[str, Any]]:
        """
        获取组件的所有实例配置
        :param component_name: 组件名称
        :return: 所有实例的配置字典
        """
        if component_name not in self.configs:
            raise ValueError(f"未找到组件配置: {component_name}")
        
        config = self.configs[component_name]
        instances = config.get('instances', {})
        
        # 如果有common配置，合并到每个实例配置中
        if 'common' in config:
            merged_instances = {}
            for instance_name, instance_config in instances.items():
                merged_instances[instance_name] = self._merge_config(config['common'], instance_config)
            return merged_instances
        
        return instances

    def get_default_instance_name(self, component_name: str) -> Optional[str]:
        """
        获取组件的默认实例名称
        :param component_name: 组件名称
        :return: 默认实例名称
        """
        if component_name not in self.configs:
            raise ValueError(f"未找到组件配置: {component_name}")
        
        config = self.configs[component_name]
        return config.get('default_instance')

    def list_instances(self, component_name: str) -> list:
        """
        列出组件的所有实例名称
        :param component_name: 组件名称
        :return: 实例名称列表
        """
        if component_name not in self.configs:
            raise ValueError(f"未找到组件配置: {component_name}")
        
        config = self.configs[component_name]
        return list(config.get('instances', {}).keys()) 