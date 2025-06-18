from logger_manager import get_logger, default_logger
import logging

def example_basic_usage():
    """基本使用示例"""
    # 使用默认日志记录器
    default_logger.info("这是一条信息日志")
    default_logger.warning("这是一条警告日志")
    default_logger.error("这是一条错误日志")
    
    # 使用自定义日志记录器
    logger = get_logger(
        name="custom",
        log_dir="custom_logs",
        level=logging.DEBUG,
        format="text"
    )
    
    logger.debug("这是一条调试日志")
    logger.info("这是一条信息日志")

def example_with_extra():
    """使用额外信息的示例"""
    logger = get_logger("extra_example")
    
    # 添加额外信息
    logger.info(
        "用户登录成功",
        extra={
            "user_id": "12345",
            "ip": "192.168.1.1",
            "action": "login"
        }
    )

def example_with_exception():
    """异常日志示例"""
    logger = get_logger("exception_example")
    
    try:
        # 模拟一个异常
        1 / 0
    except Exception as e:
        logger.exception(
            "发生异常",
            extra={
                "error_type": type(e).__name__,
                "error_code": "DIVISION_BY_ZERO"
            }
        )

if __name__ == "__main__":
    example_basic_usage()
    example_with_extra()
    example_with_exception() 