"""命令系统模块"""
from .registry import CommandRegistry, command, get_registry
from .base import BaseCommand, CommandContext, CommandResult

# 导入所有命令模块以触发注册
from . import roll
from . import character
from . import check
from . import rule
from . import npc
from . import misc
from . import notebook

__all__ = [
    "CommandRegistry",
    "command",
    "get_registry",
    "BaseCommand",
    "CommandContext",
    "CommandResult",
]
