"""命令注册器"""
import time
from typing import Callable, Dict, List, Optional, Type
from loguru import logger
from .base import BaseCommand, CommandContext, CommandResult


class CommandRegistry:
    """命令注册器 - 管理所有命令的注册和路由"""
    
    def __init__(self):
        self._commands: Dict[str, Type[BaseCommand]] = {}
        self._aliases: Dict[str, str] = {}  # alias -> primary name
        # 支持紧凑格式的命令（可以不带空格）
        self._compact_commands: List[str] = []
    
    def register(
        self, 
        name: str, 
        aliases: Optional[List[str]] = None,
        compact: bool = False
    ) -> Callable[[Type[BaseCommand]], Type[BaseCommand]]:
        """
        装饰器：注册命令处理器
        
        Args:
            name: 命令名称
            aliases: 命令别名列表
            compact: 是否支持紧凑格式（如 .rd100 而不是 .rd 100）
        """
        def decorator(cls: Type[BaseCommand]) -> Type[BaseCommand]:
            # 设置命令元数据
            cls.name = name
            cls.aliases = aliases or []
            
            # 注册主命令
            self._commands[name] = cls
            logger.debug(f"注册命令: {name}")
            
            # 注册别名
            for alias in cls.aliases:
                self._aliases[alias] = name
                logger.debug(f"注册别名: {alias} -> {name}")
            
            # 标记紧凑格式命令
            if compact:
                self._compact_commands.append(name)
                # 按长度降序排列，优先匹配长的命令
                self._compact_commands.sort(key=len, reverse=True)
            
            return cls
        return decorator
    
    def register_class(
        self, 
        cls: Type[BaseCommand],
        name: Optional[str] = None,
        aliases: Optional[List[str]] = None,
        compact: bool = False
    ) -> None:
        """
        显式注册命令类
        
        Args:
            cls: 命令类
            name: 命令名称（如果不指定则使用类的 name 属性）
            aliases: 命令别名列表
            compact: 是否支持紧凑格式
        """
        cmd_name = name or cls.name
        if not cmd_name:
            raise ValueError(f"命令类 {cls.__name__} 必须指定名称")
        
        cls.name = cmd_name
        if aliases:
            cls.aliases = aliases
        
        self._commands[cmd_name] = cls
        
        for alias in cls.aliases:
            self._aliases[alias] = cmd_name
        
        if compact:
            self._compact_commands.append(cmd_name)
            self._compact_commands.sort(key=len, reverse=True)
    
    def get_handler(self, command: str) -> Optional[Type[BaseCommand]]:
        """根据命令名获取处理器类"""
        # 先尝试直接匹配
        if command in self._commands:
            return self._commands[command]
        
        # 尝试别名匹配
        if command in self._aliases:
            primary = self._aliases[command]
            return self._commands.get(primary)
        
        return None
    
    def parse_command(self, cmd_str: str) -> tuple[Optional[str], str]:
        """
        解析命令字符串，返回 (命令名, 参数)
        
        支持两种格式：
        1. 空格分隔: ".r 1d100" -> ("r", "1d100")
        2. 紧凑格式: ".rd100" -> ("rd", "100")
        """
        # 先尝试空格分隔
        parts = cmd_str.split(maxsplit=1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        # 检查是否是已知命令
        if self.get_handler(command):
            return (command, args)
        
        # 尝试紧凑格式解析
        cmd_lower = cmd_str.lower()
        for prefix in self._compact_commands:
            if cmd_lower.startswith(prefix) and len(cmd_str) > len(prefix):
                # 检查前缀后面不是ASCII字母（避免 "rule" 被解析为 "r" + "ule"）
                # 但允许中文、数字、rp（奖励骰/惩罚骰前缀）
                next_char = cmd_str[len(prefix)]
                is_ascii_letter = next_char.isascii() and next_char.isalpha()
                if not is_ascii_letter or next_char.lower() in "rp":
                    return (prefix, cmd_str[len(prefix):])
        
        # 未找到匹配的命令
        return (command, args)
    
    def list_commands(self) -> List[str]:
        """列出所有已注册命令"""
        return list(self._commands.keys())
    
    def get_all_handlers(self) -> Dict[str, Type[BaseCommand]]:
        """获取所有命令处理器"""
        return self._commands.copy()
    
    async def execute(
        self, 
        cmd_str: str, 
        ctx: CommandContext
    ) -> Optional[CommandResult]:
        """
        执行命令
        
        Args:
            cmd_str: 命令字符串（不含前缀）
            ctx: 命令上下文
        
        Returns:
            命令执行结果，如果命令不存在返回 None
        """
        command, args = self.parse_command(cmd_str)
        
        handler_cls = self.get_handler(command)
        if not handler_cls:
            return None
        
        start_time = time.perf_counter()
        
        # 记录命令开始
        logger.info(
            f"CMD | user={ctx.user_id}({ctx.user_name}) | "
            f"channel={ctx.channel_id}({ctx.channel_type}) | "
            f"cmd={command} | args={args}"
        )
        
        try:
            handler = handler_cls(ctx)
            result = await handler.execute(args)
            
            duration = (time.perf_counter() - start_time) * 1000
            logger.info(
                f"CMD_OK | user={ctx.user_id} | cmd={command} | "
                f"duration={duration:.2f}ms"
            )
            return result
            
        except Exception as e:
            duration = (time.perf_counter() - start_time) * 1000
            logger.exception(
                f"CMD_ERR | user={ctx.user_id} | cmd={command} | "
                f"duration={duration:.2f}ms | error={type(e).__name__}: {e}"
            )
            return CommandResult.text(f"命令执行出错: {e}")


# 全局命令注册器实例
_registry = CommandRegistry()


def command(
    name: str, 
    aliases: Optional[List[str]] = None,
    compact: bool = False
) -> Callable[[Type[BaseCommand]], Type[BaseCommand]]:
    """
    命令装饰器（使用全局注册器）
    
    用法:
        @command("r", aliases=["rd"], compact=True)
        class RollCommand(BaseCommand):
            ...
    """
    return _registry.register(name, aliases, compact)


def get_registry() -> CommandRegistry:
    """获取全局命令注册器"""
    return _registry
