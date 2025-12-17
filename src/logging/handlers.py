"""日志处理器和装饰器

实现命令日志装饰器，记录命令执行、用户信息、执行结果。
Requirements: 4.4, 4.5, 4.6
"""
import time
from functools import wraps
from typing import Callable, Any
from loguru import logger


def log_command(func: Callable) -> Callable:
    """命令执行日志装饰器
    
    记录命令执行的用户信息、命令内容和执行结果。
    用于装饰 BaseCommand.execute 方法。
    
    日志格式:
    - 开始: CMD | user=xxx | channel=xxx | cmd=xxx | args=xxx
    - 成功: CMD_OK | user=xxx | cmd=xxx | duration=xxxms
    - 失败: CMD_ERR | user=xxx | cmd=xxx | error=xxx
    """
    @wraps(func)
    async def wrapper(self, args: str, *extra_args, **kwargs) -> Any:
        start_time = time.perf_counter()
        user_id = getattr(self.ctx, 'user_id', 'unknown')
        user_name = getattr(self.ctx, 'user_name', 'unknown')
        channel_id = getattr(self.ctx, 'channel_id', 'unknown')
        channel_type = getattr(self.ctx, 'channel_type', 'unknown')
        cmd_name = getattr(self, 'name', func.__name__)
        
        # 记录命令开始
        logger.info(
            f"CMD | user={user_id}({user_name}) | "
            f"channel={channel_id}({channel_type}) | "
            f"cmd={cmd_name} | args={args}"
        )
        
        try:
            result = await func(self, args, *extra_args, **kwargs)
            duration = (time.perf_counter() - start_time) * 1000
            
            # 记录命令成功
            logger.info(
                f"CMD_OK | user={user_id} | cmd={cmd_name} | "
                f"duration={duration:.2f}ms"
            )
            return result
            
        except Exception as e:
            duration = (time.perf_counter() - start_time) * 1000
            
            # 记录命令失败（包含完整堆栈）
            logger.exception(
                f"CMD_ERR | user={user_id} | cmd={cmd_name} | "
                f"duration={duration:.2f}ms | error={type(e).__name__}: {e}"
            )
            raise
    
    return wrapper


def log_message(direction: str = "OUT") -> Callable:
    """消息日志装饰器
    
    记录发送/接收的消息。
    
    Args:
        direction: 消息方向 ("IN" 或 "OUT")
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            start_time = time.perf_counter()
            
            try:
                result = await func(*args, **kwargs)
                duration = (time.perf_counter() - start_time) * 1000
                
                # 尝试从参数中提取目标信息
                target_id = kwargs.get('target_id') or kwargs.get('channel_id', 'unknown')
                msg_type = kwargs.get('type', 'unknown')
                
                logger.debug(
                    f"MSG_{direction} | target={target_id} | "
                    f"type={msg_type} | duration={duration:.2f}ms"
                )
                return result
                
            except Exception as e:
                logger.exception(
                    f"MSG_{direction}_ERR | error={type(e).__name__}: {e}"
                )
                raise
        
        return wrapper
    return decorator


class CommandLogger:
    """命令日志记录器类
    
    提供更细粒度的日志记录方法。
    """
    
    def __init__(self, name: str = "command"):
        self._logger = logger.bind(name=name)
    
    def log_start(
        self,
        user_id: str,
        user_name: str,
        channel_id: str,
        channel_type: str,
        command: str,
        args: str
    ) -> None:
        """记录命令开始"""
        self._logger.info(
            f"CMD | user={user_id}({user_name}) | "
            f"channel={channel_id}({channel_type}) | "
            f"cmd={command} | args={args}"
        )
    
    def log_success(
        self,
        user_id: str,
        command: str,
        duration_ms: float
    ) -> None:
        """记录命令成功"""
        self._logger.info(
            f"CMD_OK | user={user_id} | cmd={command} | "
            f"duration={duration_ms:.2f}ms"
        )
    
    def log_error(
        self,
        user_id: str,
        command: str,
        error: Exception,
        duration_ms: float
    ) -> None:
        """记录命令错误"""
        self._logger.exception(
            f"CMD_ERR | user={user_id} | cmd={command} | "
            f"duration={duration_ms:.2f}ms | error={type(error).__name__}: {error}"
        )
    
    def log_outgoing(
        self,
        target_id: str,
        msg_type: str,
        is_card: bool = False
    ) -> None:
        """记录发送的消息"""
        self._logger.debug(
            f"MSG_OUT | target={target_id} | type={msg_type} | "
            f"is_card={is_card}"
        )


# 全局命令日志记录器实例
command_logger = CommandLogger()
