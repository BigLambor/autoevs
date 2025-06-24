import subprocess
import os
from typing import List, Dict, Any, Optional, Tuple
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OSClient:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化OS客户端
        
        Args:
            config: 配置字典，包含以下可选字段：
                - timeout: 命令执行超时时间（秒）
                - work_dir: 工作目录
                - user: 执行命令的用户
                - group: 执行命令的用户组
        """
        self.config = config or {}
        self.timeout = self.config.get('timeout', 300)
        self.work_dir = self.config.get('work_dir', '/tmp')
        self.user = self.config.get('user')
        self.group = self.config.get('group')
        
        # 确保工作目录存在
        if not os.path.exists(self.work_dir):
            os.makedirs(self.work_dir, exist_ok=True)

    def execute_command(self, command: str, shell: bool = True, env: Optional[Dict[str, str]] = None) -> Tuple[int, str, str]:
        """
        执行系统命令
        
        Args:
            command: 要执行的命令
            shell: 是否使用shell执行
            env: 环境变量字典
            
        Returns:
            (返回码, 标准输出, 标准错误)
        """
        try:
            # 合并环境变量
            exec_env = os.environ.copy()
            if env:
                exec_env.update(env)
                
            process = subprocess.Popen(
                command,
                shell=shell,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                env=exec_env
            )
            stdout, stderr = process.communicate()
            return process.returncode, stdout, stderr
        except Exception as e:
            logger.error(f"执行命令失败: {str(e)}")
            raise

    def execute_command_with_timeout(self, command: str, timeout: int, shell: bool = True, env: Optional[Dict[str, str]] = None) -> Tuple[int, str, str]:
        """
        执行系统命令（带超时）
        
        Args:
            command: 要执行的命令
            timeout: 超时时间（秒）
            shell: 是否使用shell执行
            env: 环境变量字典
            
        Returns:
            (返回码, 标准输出, 标准错误)
        """
        try:
            # 合并环境变量
            exec_env = os.environ.copy()
            if env:
                exec_env.update(env)
                
            process = subprocess.Popen(
                command,
                shell=shell,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                env=exec_env
            )
            stdout, stderr = process.communicate(timeout=timeout)
            return process.returncode, stdout, stderr
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            logger.error(f"命令执行超时: {command}")
            return -1, stdout, stderr
        except Exception as e:
            logger.error(f"执行命令失败: {str(e)}")
            raise

    def check_command_exists(self, command: str) -> bool:
        """
        检查命令是否存在
        
        Args:
            command: 要检查的命令
            
        Returns:
            命令是否存在
        """
        try:
            subprocess.run(
                f"which {command}",
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )
            return True
        except subprocess.CalledProcessError:
            return False

    def get_command_output(self, command: str, shell: bool = True) -> str:
        """
        获取命令输出
        
        Args:
            command: 要执行的命令
            shell: 是否使用shell执行
            
        Returns:
            命令输出
        """
        returncode, stdout, stderr = self.execute_command(command, shell)
        if returncode != 0:
            raise RuntimeError(f"命令执行失败: {stderr}")
        return stdout.strip()

    def get_command_output_with_timeout(self, command: str, timeout: int, shell: bool = True) -> str:
        """
        获取命令输出（带超时）
        
        Args:
            command: 要执行的命令
            timeout: 超时时间（秒）
            shell: 是否使用shell执行
            
        Returns:
            命令输出
        """
        returncode, stdout, stderr = self.execute_command_with_timeout(command, timeout, shell)
        if returncode != 0:
            raise RuntimeError(f"命令执行失败: {stderr}")
        return stdout.strip()

    def get_file_info(self, path: str) -> Dict[str, Any]:
        """
        获取文件信息
        
        Args:
            path: 文件路径
            
        Returns:
            文件信息
        """
        try:
            stat = os.stat(path)
            return {
                'success': True,
                'size': stat.st_size,
                'mode': stat.st_mode,
                'uid': stat.st_uid,
                'gid': stat.st_gid,
                'atime': stat.st_atime,
                'mtime': stat.st_mtime,
                'ctime': stat.st_ctime
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def list_dir(self, path: str) -> Dict[str, Any]:
        """
        列出目录内容
        
        Args:
            path: 目录路径
            
        Returns:
            目录内容
        """
        try:
            items = os.listdir(path)
            return {
                'success': True,
                'items': items
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def create_dir(self, path: str, mode: int = 0o755) -> Dict[str, Any]:
        """
        创建目录
        
        Args:
            path: 目录路径
            mode: 目录权限
            
        Returns:
            执行结果
        """
        try:
            os.makedirs(path, mode=mode, exist_ok=True)
            return {'success': True}
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def remove_file(self, path: str) -> Dict[str, Any]:
        """
        删除文件
        
        Args:
            path: 文件路径
            
        Returns:
            执行结果
        """
        try:
            os.remove(path)
            return {'success': True}
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def remove_dir(self, path: str, recursive: bool = False) -> Dict[str, Any]:
        """
        删除目录
        
        Args:
            path: 目录路径
            recursive: 是否递归删除
            
        Returns:
            执行结果
        """
        try:
            if recursive:
                shutil.rmtree(path)
            else:
                os.rmdir(path)
            return {'success': True}
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def copy_file(self, src: str, dst: str) -> Dict[str, Any]:
        """
        复制文件
        
        Args:
            src: 源文件路径
            dst: 目标文件路径
            
        Returns:
            执行结果
        """
        try:
            shutil.copy2(src, dst)
            return {'success': True}
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def move_file(self, src: str, dst: str) -> Dict[str, Any]:
        """
        移动文件
        
        Args:
            src: 源文件路径
            dst: 目标文件路径
            
        Returns:
            执行结果
        """
        try:
            shutil.move(src, dst)
            return {'success': True}
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def get_disk_usage(self, path: str = '/') -> Dict[str, Any]:
        """
        获取磁盘使用情况
        
        Args:
            path: 路径
            
        Returns:
            磁盘使用情况
        """
        try:
            total, used, free = shutil.disk_usage(path)
            return {
                'success': True,
                'total': total,
                'used': used,
                'free': free
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def get_process_info(self, pid: int) -> Dict[str, Any]:
        """
        获取进程信息
        
        Args:
            pid: 进程ID
            
        Returns:
            进程信息
        """
        try:
            with open(f'/proc/{pid}/status', 'r') as f:
                status = f.read()
            return {
                'success': True,
                'status': status
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            } 