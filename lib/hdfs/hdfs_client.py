from typing import List, Dict, Any, Optional, Tuple
import logging
import re
import json
from datetime import datetime

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HDFSClient:
    def __init__(self, config: Dict[str, Any], os_client=None, kerberos_client=None):
        """
        初始化HDFS客户端
        
        Args:
            config: HDFS配置字典，包含以下字段：
                - namenode_url: NameNode URL，例如：hdfs://hdfs-nn:8020
                - username: 用户名，可选
                - enable_kerberos: 是否启用Kerberos认证，默认False
            os_client: OS客户端实例，用于执行命令
            kerberos_client: Kerberos客户端实例，用于认证
        """
        self.namenode_url = config.get('namenode_url', '')
        self.username = config.get('username')
        self.enable_kerberos = config.get('enable_kerberos', False)
        self.os_client = os_client
        self.kerberos_client = kerberos_client
        
        if not self.os_client:
            from lib.os.os_client import OSClient
            self.os_client = OSClient({
                'timeout': 300,
                'work_dir': '/tmp'
            })
            
        # 如果启用Kerberos但没有提供kerberos_client，尝试创建
        if self.enable_kerberos and not self.kerberos_client:
            try:
                from lib.kerberos.kerberos_client import KerberosClient
                kerberos_config = config.get('kerberos', {})
                if kerberos_config:
                    self.kerberos_client = KerberosClient(kerberos_config, self.os_client)
                else:
                    self.logger.warning("启用了Kerberos但未提供Kerberos配置")
                    self.enable_kerberos = False
            except Exception as e:
                self.logger.warning(f"创建Kerberos客户端失败: {str(e)}")
                self.enable_kerberos = False
        
        self.logger = logger

    def set_logger(self, logger):
        """设置日志器"""
        self.logger = logger
        if self.kerberos_client:
            self.kerberos_client.set_logger(logger)

    def _ensure_authenticated(self) -> bool:
        """
        确保Kerberos认证有效（如果启用）
        
        Returns:
            bool: 认证是否成功
        """
        if not self.enable_kerberos:
            return True
            
        if not self.kerberos_client:
            self.logger.error("启用了Kerberos但没有Kerberos客户端")
            return False
            
        return self.kerberos_client.ensure_authenticated()

    def _execute_hdfs_command(self, command: str) -> Tuple[int, str]:
        """
        执行HDFS命令
        
        Args:
            command: 要执行的HDFS命令
            
        Returns:
            Tuple[int, str]: (返回码, 输出)
        """
        try:
            # 确保Kerberos认证有效
            if not self._ensure_authenticated():
                raise Exception("Kerberos认证失败")
            
            # 设置环境变量
            env = {}
            if self.enable_kerberos and self.kerberos_client:
                env.update(self.kerberos_client.get_hadoop_env())
            
            return_code, stdout, stderr = self.os_client.execute_command(command, env=env)
            # 合并标准输出和标准错误
            output = stdout + stderr if stderr else stdout
            return return_code, output
        except Exception as e:
            self.logger.error(f"执行HDFS命令时发生错误: {str(e)}")
            raise

    def list_dir(self, path: str) -> List[Dict[str, Any]]:
        """
        列出目录内容
        
        Args:
            path: 目录路径
            
        Returns:
            目录内容列表
        """
        try:
            command = f"hdfs dfs -ls {path}"
            return_code, output = self._execute_hdfs_command(command)
            
            if return_code != 0:
                raise Exception(f"HDFS命令执行失败，返回码: {return_code}")
            
            return self._parse_ls_output(output)
        except Exception as e:
            self.logger.error(f"列出目录 {path} 失败: {str(e)}")
            raise

    def exists(self, path: str) -> bool:
        """
        检查路径是否存在
        
        Args:
            path: 路径
            
        Returns:
            是否存在
        """
        try:
            command = f"hdfs dfs -test -e {path}"
            return_code, _ = self._execute_hdfs_command(command)
            return return_code == 0
        except Exception as e:
            self.logger.error(f"检查路径 {path} 是否存在失败: {str(e)}")
            return False

    def mkdir(self, path: str, permission: str = '755') -> None:
        """
        创建目录
        
        Args:
            path: 目录路径
            permission: 权限，默认755
        """
        try:
            command = f"hdfs dfs -mkdir -p {path}"
            return_code, output = self._execute_hdfs_command(command)
            
            if return_code != 0:
                raise Exception(f"创建目录失败，返回码: {return_code}")
                
            # 设置权限
            if permission != '755':
                self.set_permission(path, permission)
                
        except Exception as e:
            self.logger.error(f"创建目录 {path} 失败: {str(e)}")
            raise

    def delete(self, path: str, recursive: bool = False) -> None:
        """
        删除文件或目录
        
        Args:
            path: 路径
            recursive: 是否递归删除
        """
        try:
            if recursive:
                command = f"hdfs dfs -rm -r {path}"
            else:
                command = f"hdfs dfs -rm {path}"
                
            return_code, output = self._execute_hdfs_command(command)
            
            if return_code != 0:
                raise Exception(f"删除失败，返回码: {return_code}")
                
        except Exception as e:
            self.logger.error(f"删除 {path} 失败: {str(e)}")
            raise

    def copy(self, src_path: str, dst_path: str, overwrite: bool = False) -> None:
        """
        复制文件或目录
        
        Args:
            src_path: 源路径
            dst_path: 目标路径
            overwrite: 是否覆盖
        """
        try:
            if overwrite:
                command = f"hdfs dfs -cp -f {src_path} {dst_path}"
            else:
                command = f"hdfs dfs -cp {src_path} {dst_path}"
                
            return_code, output = self._execute_hdfs_command(command)
            
            if return_code != 0:
                raise Exception(f"复制失败，返回码: {return_code}")
                
        except Exception as e:
            self.logger.error(f"复制 {src_path} 到 {dst_path} 失败: {str(e)}")
            raise

    def move(self, src_path: str, dst_path: str, overwrite: bool = False) -> None:
        """
        移动文件或目录
        
        Args:
            src_path: 源路径
            dst_path: 目标路径
            overwrite: 是否覆盖
        """
        try:
            if overwrite:
                command = f"hdfs dfs -mv {src_path} {dst_path}"
            else:
                command = f"hdfs dfs -mv {src_path} {dst_path}"
                
            return_code, output = self._execute_hdfs_command(command)
            
            if return_code != 0:
                raise Exception(f"移动失败，返回码: {return_code}")
                
        except Exception as e:
            self.logger.error(f"移动 {src_path} 到 {dst_path} 失败: {str(e)}")
            raise

    def get_file_status(self, path: str) -> Dict[str, Any]:
        """
        获取文件状态
        
        Args:
            path: 文件路径
            
        Returns:
            文件状态信息
        """
        try:
            command = f"hdfs dfs -ls -d {path}"
            return_code, output = self._execute_hdfs_command(command)
            
            if return_code != 0:
                raise Exception(f"获取文件状态失败，返回码: {return_code}")
            
            return self._parse_file_status(output)
        except Exception as e:
            self.logger.error(f"获取文件状态 {path} 失败: {str(e)}")
            raise

    def get_content_summary(self, path: str) -> Dict[str, Any]:
        """
        获取目录内容摘要
        
        Args:
            path: 目录路径
            
        Returns:
            内容摘要信息
        """
        try:
            command = f"hdfs dfs -count {path}"
            return_code, output = self._execute_hdfs_command(command)
            
            if return_code != 0:
                raise Exception(f"获取内容摘要失败，返回码: {return_code}")
            
            return self._parse_count_output(output)
        except Exception as e:
            self.logger.error(f"获取内容摘要 {path} 失败: {str(e)}")
            raise

    def set_owner(self, path: str, owner: str = None, group: str = None) -> None:
        """
        设置文件或目录的所有者
        
        Args:
            path: 路径
            owner: 所有者
            group: 用户组
        """
        try:
            if owner and group:
                command = f"hdfs dfs -chown {owner}:{group} {path}"
            elif owner:
                command = f"hdfs dfs -chown {owner} {path}"
            else:
                return
                
            return_code, output = self._execute_hdfs_command(command)
            
            if return_code != 0:
                raise Exception(f"设置所有者失败，返回码: {return_code}")
                
        except Exception as e:
            self.logger.error(f"设置所有者 {path} 失败: {str(e)}")
            raise

    def set_permission(self, path: str, permission: str) -> None:
        """
        设置文件或目录的权限
        
        Args:
            path: 路径
            permission: 权限
        """
        try:
            command = f"hdfs dfs -chmod {permission} {path}"
            return_code, output = self._execute_hdfs_command(command)
            
            if return_code != 0:
                raise Exception(f"设置权限失败，返回码: {return_code}")
                
        except Exception as e:
            self.logger.error(f"设置权限 {path} 失败: {str(e)}")
            raise

    def set_replication(self, path: str, replication: int) -> None:
        """
        设置文件的副本数
        
        Args:
            path: 文件路径
            replication: 副本数
        """
        try:
            command = f"hdfs dfs -setrep {replication} {path}"
            return_code, output = self._execute_hdfs_command(command)
            
            if return_code != 0:
                raise Exception(f"设置副本数失败，返回码: {return_code}")
                
        except Exception as e:
            self.logger.error(f"设置副本数 {path} 失败: {str(e)}")
            raise

    def upload(self, local_path: str, hdfs_path: str, overwrite: bool = False) -> None:
        """上传文件"""
        try:
            if overwrite:
                command = f"hdfs dfs -put -f {local_path} {hdfs_path}"
            else:
                command = f"hdfs dfs -put {local_path} {hdfs_path}"
                
            return_code, output = self._execute_hdfs_command(command)
            
            if return_code != 0:
                raise Exception(f"上传失败，返回码: {return_code}")
                
        except Exception as e:
            self.logger.error(f"上传 {local_path} 到 {hdfs_path} 失败: {str(e)}")
            raise

    def download(self, hdfs_path: str, local_path: str, overwrite: bool = False) -> None:
        """下载文件"""
        try:
            if overwrite:
                command = f"hdfs dfs -get -f {hdfs_path} {local_path}"
            else:
                command = f"hdfs dfs -get {hdfs_path} {local_path}"
                
            return_code, output = self._execute_hdfs_command(command)
            
            if return_code != 0:
                raise Exception(f"下载失败，返回码: {return_code}")
                
        except Exception as e:
            self.logger.error(f"下载 {hdfs_path} 到 {local_path} 失败: {str(e)}")
            raise

    def read(self, path: str, offset: int = 0, length: Optional[int] = None) -> bytes:
        """读取文件内容"""
        try:
            if length:
                command = f"hdfs dfs -cat {path} | dd bs=1 skip={offset} count={length} 2>/dev/null"
            else:
                command = f"hdfs dfs -cat {path}"
                
            return_code, output = self._execute_hdfs_command(command)
            
            if return_code != 0:
                raise Exception(f"读取文件失败，返回码: {return_code}")
            
            return output.encode('utf-8')
        except Exception as e:
            self.logger.error(f"读取文件 {path} 失败: {str(e)}")
            raise

    def write(self, path: str, data: bytes, overwrite: bool = False) -> None:
        """写入文件内容"""
        try:
            # 创建临时文件
            import tempfile
            import os
            
            with tempfile.NamedTemporaryFile(mode='wb', delete=False) as temp_file:
                temp_file.write(data)
                temp_file_path = temp_file.name
            
            try:
                if overwrite:
                    command = f"hdfs dfs -put -f {temp_file_path} {path}"
                else:
                    command = f"hdfs dfs -put {temp_file_path} {path}"
                    
                return_code, output = self._execute_hdfs_command(command)
                
                if return_code != 0:
                    raise Exception(f"写入文件失败，返回码: {return_code}")
            finally:
                # 清理临时文件
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    
        except Exception as e:
            self.logger.error(f"写入文件 {path} 失败: {str(e)}")
            raise

    def append(self, path: str, data: bytes) -> None:
        """追加文件内容"""
        try:
            # 创建临时文件
            import tempfile
            import os
            
            with tempfile.NamedTemporaryFile(mode='wb', delete=False) as temp_file:
                temp_file.write(data)
                temp_file_path = temp_file.name
            
            try:
                command = f"hdfs dfs -appendToFile {temp_file_path} {path}"
                return_code, output = self._execute_hdfs_command(command)
                
                if return_code != 0:
                    raise Exception(f"追加文件失败，返回码: {return_code}")
            finally:
                # 清理临时文件
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    
        except Exception as e:
            self.logger.error(f"追加文件 {path} 失败: {str(e)}")
            raise

    def get_checksum(self, path: str) -> Dict:
        """获取文件校验和"""
        try:
            command = f"hdfs dfs -checksum {path}"
            return_code, output = self._execute_hdfs_command(command)
            
            if return_code != 0:
                raise Exception(f"获取校验和失败，返回码: {return_code}")
            
            return self._parse_checksum_output(output)
        except Exception as e:
            self.logger.error(f"获取校验和 {path} 失败: {str(e)}")
            raise

    def get_home_directory(self) -> str:
        """获取用户主目录"""
        try:
            command = "hdfs dfs -pwd"
            return_code, output = self._execute_hdfs_command(command)
            
            if return_code != 0:
                raise Exception(f"获取主目录失败，返回码: {return_code}")
            
            return output.strip()
        except Exception as e:
            self.logger.error(f"获取主目录失败: {str(e)}")
            raise

    def _parse_ls_output(self, output: str) -> List[Dict[str, Any]]:
        """解析ls命令输出"""
        try:
            lines = output.strip().split('\n')
            items = []
            
            for line in lines:
                if line.strip() and not line.startswith('Found'):
                    parts = line.split()
                    if len(parts) >= 8:
                        item = {
                            'permission': parts[0],
                            'replication': parts[1],
                            'owner': parts[2],
                            'group': parts[3],
                            'size': int(parts[4]),
                            'date': f"{parts[5]} {parts[6]}",
                            'name': parts[7],
                            'path': parts[7]
                        }
                        items.append(item)
            
            return items
        except Exception as e:
            self.logger.error(f"解析ls输出失败: {str(e)}")
            return []

    def _parse_file_status(self, output: str) -> Dict[str, Any]:
        """解析文件状态输出"""
        try:
            lines = output.strip().split('\n')
            for line in lines:
                if line.strip() and not line.startswith('Found'):
                    parts = line.split()
                    if len(parts) >= 8:
                        return {
                            'permission': parts[0],
                            'replication': parts[1],
                            'owner': parts[2],
                            'group': parts[3],
                            'size': int(parts[4]),
                            'date': f"{parts[5]} {parts[6]}",
                            'name': parts[7],
                            'path': parts[7]
                        }
            return {}
        except Exception as e:
            self.logger.error(f"解析文件状态失败: {str(e)}")
            return {}

    def _parse_count_output(self, output: str) -> Dict[str, Any]:
        """解析count命令输出"""
        try:
            parts = output.strip().split()
            if len(parts) >= 4:
                return {
                    'dir_count': int(parts[0]),
                    'file_count': int(parts[1]),
                    'content_size': int(parts[2]),
                    'path': parts[3]
                }
            return {}
        except Exception as e:
            self.logger.error(f"解析count输出失败: {str(e)}")
            return {}

    def _parse_checksum_output(self, output: str) -> Dict[str, Any]:
        """解析校验和输出"""
        try:
            # 解析校验和输出格式
            lines = output.strip().split('\n')
            for line in lines:
                if 'MD5of' in line:
                    # 提取MD5值
                    md5_match = re.search(r'MD5of[^:]*:\s*([a-fA-F0-9]+)', line)
                    if md5_match:
                        return {'md5': md5_match.group(1)}
            return {}
        except Exception as e:
            self.logger.error(f"解析校验和输出失败: {str(e)}")
            return {} 