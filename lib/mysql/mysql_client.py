import pymysql
from typing import List, Dict, Any, Optional, Union
import logging
from contextlib import contextmanager
import time

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MySQLClient:
    def __init__(self, config: Dict[str, Any]):
        """
        初始化MySQL客户端
        
        Args:
            config: MySQL配置字典，包含以下字段：
                - host: 数据库主机
                - port: 数据库端口
                - username: 用户名
                - password: 密码
                - database: 数据库名
                - pool_size: 连接池大小（可选，默认5）
                - retry_times: 重试次数（可选，默认3）
                - retry_interval: 重试间隔（秒，可选，默认1）
        """
        self.config = config
        self.retry_times = config.get('retry_times', 3)
        self.retry_interval = config.get('retry_interval', 1)
        self.pool_size = config.get('pool_size', 5)
        self._pool = []
        self._init_pool()

    def _init_pool(self):
        for _ in range(self.pool_size):
            conn = pymysql.connect(
                host=self.config.get('host', 'localhost'),
                port=self.config.get('port', 3306),
                user=self.config.get('username'),
                password=self.config.get('password'),
                database=self.config.get('database'),
                charset='utf8mb4',
                autocommit=False,
                cursorclass=pymysql.cursors.DictCursor
            )
            self._pool.append(conn)

    @contextmanager
    def _get_connection(self):
        conn = None
        try:
            if self._pool:
                conn = self._pool.pop()
            else:
                conn = pymysql.connect(
                    host=self.config.get('host', 'localhost'),
                    port=self.config.get('port', 3306),
                    user=self.config.get('username'),
                    password=self.config.get('password'),
                    database=self.config.get('database'),
                    charset='utf8mb4',
                    autocommit=False,
                    cursorclass=pymysql.cursors.DictCursor
                )
            yield conn
        except Exception as e:
            logger.error(f"获取数据库连接失败: {str(e)}")
            raise
        finally:
            if conn:
                try:
                    if len(self._pool) < self.pool_size:
                        self._pool.append(conn)
                    else:
                        conn.close()
                except Exception as e:
                    logger.warning(f"关闭数据库连接失败: {str(e)}")

    def _execute_with_retry(self, func, *args, **kwargs):
        """
        带重试的执行函数
        
        Args:
            func: 要执行的函数
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            函数执行结果
        """
        last_error = None
        for i in range(self.retry_times):
            try:
                return func(*args, **kwargs)
            except pymysql.MySQLError as e:
                last_error = e
                logger.warning(f"执行失败，第{i+1}次重试: {str(e)}")
                if i < self.retry_times - 1:
                    time.sleep(self.retry_interval)
        
        logger.error(f"执行失败，已达到最大重试次数: {str(last_error)}")
        raise last_error

    def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """
        执行查询
        
        Args:
            query: SQL查询语句
            params: 查询参数
            
        Returns:
            查询结果列表
        """
        def _query():
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, params or ())
                    return cursor.fetchall()
        
        return self._execute_with_retry(_query)

    def execute_update(self, query: str, params: Optional[tuple] = None) -> int:
        """
        执行更新操作
        
        Args:
            query: SQL更新语句
            params: 更新参数
            
        Returns:
            影响的行数
        """
        def _update():
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, params or ())
                    conn.commit()
                    return cursor.rowcount
        
        return self._execute_with_retry(_update)

    def insert(self, table: str, data: Dict[str, Any]) -> int:
        """
        插入单条数据
        
        Args:
            table: 表名
            data: 要插入的数据
            
        Returns:
            影响的行数
        """
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['%s'] * len(data))
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        return self.execute_update(query, tuple(data.values()))

    def update(self, table: str, data: Dict[str, Any], condition: str, params: Optional[tuple] = None) -> int:
        """
        更新数据
        
        Args:
            table: 表名
            data: 要更新的数据
            condition: 更新条件
            params: 条件参数
            
        Returns:
            影响的行数
        """
        set_clause = ', '.join([f"{k} = %s" for k in data.keys()])
        query = f"UPDATE {table} SET {set_clause} WHERE {condition}"
        return self.execute_update(query, tuple(data.values()) + (params or ()))

    def delete(self, table: str, condition: str, params: Optional[tuple] = None) -> int:
        """
        删除数据
        
        Args:
            table: 表名
            condition: 删除条件
            params: 条件参数
            
        Returns:
            影响的行数
        """
        query = f"DELETE FROM {table} WHERE {condition}"
        return self.execute_update(query, params)

    def batch_insert(self, table: str, data_list: List[Dict[str, Any]]) -> int:
        """
        批量插入数据
        
        Args:
            table: 表名
            data_list: 要插入的数据列表
            
        Returns:
            影响的行数
        """
        if not data_list:
            return 0
            
        def _batch_insert():
            # 从第一条数据中获取列名
            columns = list(data_list[0].keys())
            columns_str = ', '.join(columns)
            placeholders = ', '.join(['%s'] * len(columns))
            query = f"INSERT INTO {table} ({columns_str}) VALUES ({placeholders})"
            
            # 准备批量插入的数据
            values = [tuple(item[col] for col in columns) for item in data_list]
            
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.executemany(query, values)
                    conn.commit()
                    return cursor.rowcount
        
        return self._execute_with_retry(_batch_insert)

    @contextmanager
    def transaction(self):
        """
        事务上下文管理器
        
        Usage:
            with client.transaction():
                client.execute_update("INSERT INTO ...")
                client.execute_update("UPDATE ...")
        """
        with self._get_connection() as conn:
            try:
                yield conn
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.error(f"事务执行失败: {str(e)}")
                raise 