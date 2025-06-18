import subprocess
from typing import List, Dict, Any, Optional
import json
import os
from lib.config.config_manager import ConfigManager

class AnsibleClient:
    def __init__(self, config: ConfigManager):
        """
        初始化Ansible客户端
        
        Args:
            config: 配置管理器实例
        """
        self.config = config
        self.inventory_file = config.get('ansible.inventory_file', '/etc/ansible/hosts')
        self.ansible_cfg = config.get('ansible.config_file', '/etc/ansible/ansible.cfg')

    def _run_command(self, command: List[str]) -> Dict[str, Any]:
        """
        运行Ansible命令
        
        Args:
            command: 命令列表
            
        Returns:
            命令执行结果
        """
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True
            )
            return {
                'success': True,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'return_code': result.returncode
            }
        except subprocess.CalledProcessError as e:
            return {
                'success': False,
                'stdout': e.stdout,
                'stderr': e.stderr,
                'return_code': e.returncode
            }

    def run_playbook(self, playbook_path: str, extra_vars: Optional[Dict] = None) -> Dict[str, Any]:
        """
        运行playbook
        
        Args:
            playbook_path: playbook文件路径
            extra_vars: 额外变量
            
        Returns:
            执行结果
        """
        command = [
            'ansible-playbook',
            '-i', self.inventory_file,
            '-c', self.ansible_cfg,
            playbook_path
        ]
        
        if extra_vars:
            command.extend(['--extra-vars', json.dumps(extra_vars)])
            
        return self._run_command(command)

    def run_ad_hoc(self, hosts: str, module: str, args: Optional[Dict] = None) -> Dict[str, Any]:
        """
        运行ad-hoc命令
        
        Args:
            hosts: 目标主机
            module: 模块名
            args: 模块参数
            
        Returns:
            执行结果
        """
        command = [
            'ansible',
            '-i', self.inventory_file,
            '-c', self.ansible_cfg,
            hosts,
            '-m', module
        ]
        
        if args:
            command.extend(['-a', json.dumps(args)])
            
        return self._run_command(command)

    def ping(self, hosts: str) -> Dict[str, Any]:
        """
        ping主机
        
        Args:
            hosts: 目标主机
            
        Returns:
            ping结果
        """
        return self.run_ad_hoc(hosts, 'ping')

    def shell(self, hosts: str, command: str) -> Dict[str, Any]:
        """
        执行shell命令
        
        Args:
            hosts: 目标主机
            command: shell命令
            
        Returns:
            执行结果
        """
        return self.run_ad_hoc(hosts, 'shell', {'cmd': command})

    def copy(self, hosts: str, src: str, dest: str) -> Dict[str, Any]:
        """
        复制文件
        
        Args:
            hosts: 目标主机
            src: 源文件路径
            dest: 目标文件路径
            
        Returns:
            执行结果
        """
        return self.run_ad_hoc(hosts, 'copy', {
            'src': src,
            'dest': dest
        })

    def file(self, hosts: str, path: str, state: str = 'present', **kwargs) -> Dict[str, Any]:
        """
        文件操作
        
        Args:
            hosts: 目标主机
            path: 文件路径
            state: 状态（present/absent/directory/link/hard）
            **kwargs: 其他参数
            
        Returns:
            执行结果
        """
        args = {'path': path, 'state': state, **kwargs}
        return self.run_ad_hoc(hosts, 'file', args)

    def service(self, hosts: str, name: str, state: str, **kwargs) -> Dict[str, Any]:
        """
        服务操作
        
        Args:
            hosts: 目标主机
            name: 服务名
            state: 状态（started/stopped/restarted/reloaded）
            **kwargs: 其他参数
            
        Returns:
            执行结果
        """
        args = {'name': name, 'state': state, **kwargs}
        return self.run_ad_hoc(hosts, 'service', args)

    def yum(self, hosts: str, name: str, state: str = 'present', **kwargs) -> Dict[str, Any]:
        """
        yum包管理
        
        Args:
            hosts: 目标主机
            name: 包名
            state: 状态（present/absent/latest）
            **kwargs: 其他参数
            
        Returns:
            执行结果
        """
        args = {'name': name, 'state': state, **kwargs}
        return self.run_ad_hoc(hosts, 'yum', args) 