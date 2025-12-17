"""命令基础类"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional, Any

if TYPE_CHECKING:
    from ..client import KookClient
    from ...character import CharacterManager, NPCManager
    from ..check_manager import CheckManager


@dataclass
class CommandContext:
    """命令执行上下文"""
    user_id: str
    user_name: str
    channel_id: str
    channel_type: str  # "GROUP" or "PERSON"
    msg_id: str
    
    # 服务依赖
    client: "KookClient"
    char_manager: "CharacterManager"
    npc_manager: "NPCManager"
    check_manager: "CheckManager"
    db: Any  # Database instance
    web_app: Optional[Any] = None  # Web application instance


@dataclass
class CommandResult:
    """命令执行结果"""
    content: Optional[str] = None
    is_card: bool = False
    quote: bool = True
    
    @classmethod
    def text(cls, content: str, quote: bool = True) -> "CommandResult":
        """创建文本响应"""
        return cls(content=content, is_card=False, quote=quote)
    
    @classmethod
    def card(cls, content: str) -> "CommandResult":
        """创建卡片响应"""
        return cls(content=content, is_card=True, quote=False)
    
    @classmethod
    def empty(cls) -> "CommandResult":
        """创建空响应（不发送消息）"""
        return cls(content=None)


class BaseCommand(ABC):
    """命令基类 - 所有命令处理器的父类"""
    
    name: str = ""  # 命令名称
    aliases: list[str] = []  # 命令别名
    description: str = ""  # 命令描述
    usage: str = ""  # 使用说明
    
    def __init__(self, ctx: CommandContext):
        self.ctx = ctx
    
    @abstractmethod
    async def execute(self, args: str) -> CommandResult:
        """执行命令，返回结果"""
        pass
    
    def help(self) -> str:
        """返回帮助信息"""
        lines = [f"**{self.name}** - {self.description}"]
        if self.usage:
            lines.append(f"用法: {self.usage}")
        if self.aliases:
            lines.append(f"别名: {', '.join(self.aliases)}")
        return "\n".join(lines)
