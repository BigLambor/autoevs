import logging
import logging.handlers
import os
from datetime import datetime
from typing import Optional, Dict, Any
import json
from pathlib import Path

class LoggerManager:
    """日志管理器"""
    
    def __init__(
        self,
        name: str,
        log_dir: str = "logs",
        level: int = logging.INFO,
        format: str = "json",
        max_bytes: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5,
        console: bool = True
    ):
        """
        初始化日志管理器
        
        Args:
            name: 日志名称
            log_dir: 日志目录
            level: 日志级别
            format: 日志格式（json/text）
            max_bytes: 单个日志文件最大大小
            backup_count: 保留的日志文件数量
            console: 是否输出到控制台
        """
        self.name = name
        self.log_dir = log_dir
        self.level = level
        self.format = format
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self.console = console
        
        # 创建日志目录
        os.makedirs(log_dir, exist_ok=True)
        
        # 创建日志记录器
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        # 清除已有的处理器
        self.logger.handlers.clear()
        
        # 添加文件处理器
        self._add_file_handler()
        
        # 添加控制台处理器
        if console:
            self._add_console_handler()
    
    def _get_formatter(self) -> logging.Formatter:
        """
        获取日志格式化器
        
        Returns:
            日志格式化器
        """
        if self.format == "json":
            return JsonFormatter()
        else:
            return logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
    
    def _add_file_handler(self):
        """添加文件处理器"""
        log_file = os.path.join(
            self.log_dir,
            f"{self.name}_{datetime.now().strftime('%Y%m%d')}.log"
        )
        
        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_file,
            maxBytes=self.max_bytes,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        
        file_handler.setFormatter(self._get_formatter())
        self.logger.addHandler(file_handler)
    
    def _add_console_handler(self):
        """添加控制台处理器"""
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(self._get_formatter())
        self.logger.addHandler(console_handler)
    
    def _log(
        self,
        level: int,
        message: str,
        extra: Optional[Dict[str, Any]] = None
    ):
        """
        记录日志
        
        Args:
            level: 日志级别
            message: 日志消息
            extra: 额外信息
        """
        if extra is None:
            extra = {}
        
        # 添加通用字段
        extra.update({
            'timestamp': datetime.now().isoformat(),
            'logger': self.name
        })
        
        self.logger.log(level, message, extra=extra)
    
    def debug(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """记录调试日志"""
        self._log(logging.DEBUG, message, extra)
    
    def info(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """记录信息日志"""
        self._log(logging.INFO, message, extra)
    
    def warning(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """记录警告日志"""
        self._log(logging.WARNING, message, extra)
    
    def error(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """记录错误日志"""
        self._log(logging.ERROR, message, extra)
    
    def critical(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """记录严重错误日志"""
        self._log(logging.CRITICAL, message, extra)
    
    def exception(self, message: str, exc_info: bool = True, extra: Optional[Dict[str, Any]] = None):
        """
        记录异常日志
        
        Args:
            message: 日志消息
            exc_info: 是否包含异常信息
            extra: 额外信息
        """
        if extra is None:
            extra = {}
        
        self.logger.exception(message, exc_info=exc_info, extra=extra)

class JsonFormatter(logging.Formatter):
    """JSON格式的日志格式化器"""
    
    def format(self, record: logging.LogRecord) -> str:
        """
        格式化日志记录
        
        Args:
            record: 日志记录
            
        Returns:
            格式化后的日志字符串
        """
        # 基本字段
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage()
        }
        
        # 添加额外字段
        if hasattr(record, 'extra'):
            log_data.update(record.extra)
        
        # 添加异常信息
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # 添加堆栈信息
        if hasattr(record, 'stack_info') and record.stack_info:
            log_data['stack_info'] = self.formatStack(record.stack_info)
        
        return json.dumps(log_data, ensure_ascii=False)

# 创建默认日志管理器实例
default_logger = LoggerManager(
    name="autoevs",
    log_dir="logs",
    level=logging.INFO,
    format="json",
    console=True
)

def get_logger(
    name: str,
    log_dir: Optional[str] = None,
    level: Optional[int] = None,
    format: Optional[str] = None,
    console: Optional[bool] = None
) -> LoggerManager:
    """
    获取日志管理器实例
    
    Args:
        name: 日志名称
        log_dir: 日志目录
        level: 日志级别
        format: 日志格式
        console: 是否输出到控制台
        
    Returns:
        日志管理器实例
    """
    return LoggerManager(
        name=name,
        log_dir=log_dir or "logs",
        level=level or logging.INFO,
        format=format or "json",
        console=console if console is not None else True
    ) 