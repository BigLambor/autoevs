import logging
from typing import List, Dict, Any, Optional, Tuple, Union
import re
import tempfile
import os

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HBaseClient:
    def __init__(self, config: Dict[str, Any], os_client=None):
        """
        初始化HBase客户端（基于hbase shell命令）
        
        Args:
            config: HBase配置字典，包含以下字段：
                - zookeeper_url: ZooKeeper URL，例如：zk1:2181,zk2:2181,zk3:2181
                - zookeeper_znode_parent: ZooKeeper根节点，默认/hbase
            os_client: OS客户端实例
        """
        self.zookeeper_url = config.get('zookeeper_url', '')
        self.znode_parent = config.get('zookeeper_znode_parent', '/hbase')
        self.logger = logger
        if os_client is None:
            from lib.os.os_client import OSClient
            self.os_client = OSClient({'timeout': 300, 'work_dir': '/tmp'})
        else:
            self.os_client = os_client

    def _execute_hbase_shell(self, shell_commands: str) -> Tuple[int, str]:
        """
        执行hbase shell命令
        Args:
            shell_commands: HBase shell命令字符串（可多行）
        Returns:
            (return_code, output)
        """
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write(shell_commands)
            temp_path = f.name
        try:
            command = f"hbase shell {temp_path}"
            return_code, stdout, stderr = self.os_client.execute_command(command)
            output = stdout + stderr if stderr else stdout
            return return_code, output
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def list_tables(self) -> List[str]:
        """获取所有表名"""
        shell = "list"
        code, out = self._execute_hbase_shell(shell)
        if code != 0:
            raise Exception(f"hbase shell list命令失败: {out}")
        # 解析表名
        tables = re.findall(r'\"([\w\-:]+)\"', out)
        return tables

    def create_table(self, table_name: str, families: Dict[str, Dict]) -> None:
        """
        创建表
        Args:
            table_name: 表名
            families: 列族配置
        """
        # families: {cf1: {}, cf2: {VERSIONS => 3}}
        fam_str = ', '.join([f'\"{cf}\"' + (f', {self._dict_to_hbase_opts(opts)}' if opts else '') for cf, opts in families.items()])
        shell = f"create '{table_name}', {fam_str}"
        code, out = self._execute_hbase_shell(shell)
        if code != 0:
            raise Exception(f"hbase shell create命令失败: {out}")

    def delete_table(self, table_name: str, disable: bool = True) -> None:
        """
        删除表
        Args:
            table_name: 表名
            disable: 是否先禁用表
        """
        shell = ''
        if disable:
            shell += f"disable '{table_name}'\n"
        shell += f"drop '{table_name}'"
        code, out = self._execute_hbase_shell(shell)
        if code != 0:
            raise Exception(f"hbase shell drop命令失败: {out}")

    def put(self, table_name: str, row_key: str, data: Dict[str, Dict[str, Union[str, bytes]]]) -> None:
        """
        插入数据
        Args:
            table_name: 表名
            row_key: 行键
            data: {family: {qualifier: value}}
        """
        shell = ''
        for family, cols in data.items():
            for qualifier, value in cols.items():
                if isinstance(value, bytes):
                    value = value.decode('utf-8')
                shell += f"put '{table_name}', '{row_key}', '{family}:{qualifier}', '{value}'\n"
        code, out = self._execute_hbase_shell(shell)
        if code != 0:
            raise Exception(f"hbase shell put命令失败: {out}")

    def get(self, table_name: str, row_key: str, columns: Optional[List[str]] = None) -> Dict:
        """
        获取数据
        Args:
            table_name: 表名
            row_key: 行键
            columns: 要获取的列
        Returns:
            行数据
        """
        col_str = ''
        if columns:
            col_str = ', ' + ', '.join([f'\"{c}\"' for c in columns])
        shell = f"get '{table_name}', '{row_key}'{col_str}"
        code, out = self._execute_hbase_shell(shell)
        if code != 0:
            raise Exception(f"hbase shell get命令失败: {out}")
        # 解析输出
        result = {}
        for line in out.splitlines():
            m = re.match(r'COLUMN=([\w\-:]+), value=(.*)', line)
            if m:
                col, val = m.group(1), m.group(2)
                fam, qual = col.split(':', 1)
                if fam not in result:
                    result[fam] = {}
                result[fam][qual] = val
        return result

    def delete(self, table_name: str, row_key: str, columns: Optional[List[str]] = None) -> None:
        """
        删除数据
        Args:
            table_name: 表名
            row_key: 行键
            columns: 要删除的列
        """
        shell = ''
        if columns:
            for col in columns:
                shell += f"delete '{table_name}', '{row_key}', '{col}'\n"
        else:
            shell = f"deleteall '{table_name}', '{row_key}'"
        code, out = self._execute_hbase_shell(shell)
        if code != 0:
            raise Exception(f"hbase shell delete命令失败: {out}")

    def scan(self, table_name: str, row_start: Optional[str] = None, row_stop: Optional[str] = None,
             columns: Optional[List[str]] = None, limit: Optional[int] = None) -> List[Tuple[str, Dict]]:
        """
        扫描表
        Args:
            table_name: 表名
            row_start: 起始行键
            row_stop: 结束行键
            columns: 要获取的列
            limit: 返回的最大行数
        Returns:
            扫描结果列表
        """
        opts = []
        if row_start:
            opts.append(f"STARTROW => '{row_start}'")
        if row_stop:
            opts.append(f"STOPROW => '{row_stop}'")
        if columns:
            opts.append(f"COLUMNS => [{', '.join([f'\"{c}\"' for c in columns])}]")
        if limit:
            opts.append(f"LIMIT => {limit}")
        opt_str = ', '.join(opts)
        shell = f"scan '{table_name}'" + (f", {opt_str}" if opt_str else '')
        code, out = self._execute_hbase_shell(shell)
        if code != 0:
            raise Exception(f"hbase shell scan命令失败: {out}")
        # 解析输出
        results = []
        row_key = None
        row_data = {}
        for line in out.splitlines():
            m = re.match(r'ROW=([\w\-:]+),', line)
            if m:
                if row_key and row_data:
                    results.append((row_key, row_data))
                row_key = m.group(1)
                row_data = {}
            m2 = re.match(r'COLUMN=([\w\-:]+), value=(.*)', line)
            if m2:
                col, val = m2.group(1), m2.group(2)
                fam, qual = col.split(':', 1)
                if fam not in row_data:
                    row_data[fam] = {}
                row_data[fam][qual] = val
        if row_key and row_data:
            results.append((row_key, row_data))
        return results

    def batch_put(self, table_name: str, data: List[Tuple[str, Dict[str, Dict[str, Any]]]]) -> None:
        """
        批量插入数据
        Args:
            table_name: 表名
            data: 数据列表，每项为 (row_key, data) 元组
        """
        for row_key, row_data in data:
            self.put(table_name, row_key, row_data)

    def batch_delete(self, table_name: str, row_keys: List[str], columns: Optional[List[str]] = None) -> None:
        """
        批量删除数据
        Args:
            table_name: 表名
            row_keys: 行键列表
            columns: 要删除的列
        """
        for row_key in row_keys:
            self.delete(table_name, row_key, columns=columns)

    def _dict_to_hbase_opts(self, opts: Dict) -> str:
        """将Python字典转为HBase shell参数字符串"""
        if not opts:
            return ''
        return ', '.join([f'{k} => {repr(v)}' for k, v in opts.items()]) 