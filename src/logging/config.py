"""日志配置模块

实现结构化日志格式、轮转和保留策略。
Requirements: 4.1, 4.2, 4.3
"""
import sys
import os
from pathlib import Path
from typing import Optional
from loguru import logger


# 默认日志格式 - 结构化格式包含时间戳、级别、模块名和消息
DEFAULT_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level:<8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level>"
)

# 文件日志格式 - 纯文本结构化格式
FILE_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
    "{level:<8} | "
    "{name}:{function}:{line} | "
    "{message}"
)


def setup_logging(
    level: str = "INFO",
    log_path: Optional[Path] = None,
    rotation: str = "10 MB",
    retention: str = "7 days",
    console_format: Optional[str] = None,
    file_format: Optional[str] = None,
    enable_console: bool = True,
    enable_file: bool = True,
) -> None:
    """配置日志系统
    
    Args:
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_path: 日志文件目录路径
        rotation: 日志轮转策略 (如 "10 MB", "1 day", "00:00")
        retention: 日志保留策略 (如 "7 days", "1 week")
        console_format: 控制台日志格式
        file_format: 文件日志格式
        enable_console: 是否启用控制台输出
        enable_file: 是否启用文件输出
    """
    # 移除默认处理器
    logger.remove()
    
    # 从环境变量获取日志级别（优先级最高）
    env_level = os.environ.get("LOG_LEVEL", level).upper()
    
    # 控制台输出
    if enable_console:
        logger.add(
            sys.stderr,
            level=env_level,
            format=console_format or DEFAULT_FORMAT,
            colorize=True,
            backtrace=True,
            diagnose=True,
        )
    
    # 文件输出
    if enable_file and log_path:
        log_path = Path(log_path)
        log_path.mkdir(parents=True, exist_ok=True)
        
        # 主日志文件 - 按大小轮转
        logger.add(
            log_path / "bot_{time:YYYY-MM-DD}.log",
            level="DEBUG",
            format=file_format or FILE_FORMAT,
            rotation=rotation,
            retention=retention,
            compression="zip",
            encoding="utf-8",
            backtrace=True,
            diagnose=True,
        )
        
        # 错误日志文件 - 单独记录 ERROR 及以上级别
        logger.add(
            log_path / "error_{time:YYYY-MM-DD}.log",
            level="ERROR",
            format=file_format or FILE_FORMAT,
            rotation=rotation,
            retention=retention,
            compression="zip",
            encoding="utf-8",
            backtrace=True,
            diagnose=True,
        )


def get_logger(name: str = None):
    """获取日志记录器
    
    Args:
        name: 模块名称，用于日志标识
        
    Returns:
        配置好的 logger 实例
    """
    if name:
        return logger.bind(name=name)
    return logger
