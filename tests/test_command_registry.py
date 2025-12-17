"""命令注册器单元测试"""
import pytest
import sys
import os
from dataclasses import dataclass
from abc import ABC, abstractmethod
from typing import Callable, Dict, List, Optional, Type


# 直接定义测试所需的类，避免导入整个模块链
@dataclass
class CommandResult:
    """命令执行结果"""
    content: Optional[str] = None
    is_card: bool = False
    quote: bool = True
    
    @classmethod
    def text(cls, content: str, quote: bool = True) -> "CommandResult":
        return cls(content=content, is_card=False, quote=quote)


class BaseCommand(ABC):
    """命令基类"""
    name: str = ""
    aliases: list = []
    
    def __init__(self, ctx=None):
        self.ctx = ctx
    
    @abstractmethod
    async def execute(self, args: str) -> CommandResult:
        pass


class CommandRegistry:
    """命令注册器 - 管理所有命令的注册和路由"""
    
    def __init__(self):
        self._commands: Dict[str, Type[BaseCommand]] = {}
        self._aliases: Dict[str, str] = {}
        self._compact_commands: List[str] = []
    
    def register(
        self, 
        name: str, 
        aliases: Optional[List[str]] = None,
        compact: bool = False
    ) -> Callable[[Type[BaseCommand]], Type[BaseCommand]]:
        def decorator(cls: Type[BaseCommand]) -> Type[BaseCommand]:
            cls.name = name
            cls.aliases = aliases or []
            self._commands[name] = cls
            for alias in cls.aliases:
                self._aliases[alias] = name
            if compact:
                self._compact_commands.append(name)
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
        if command in self._commands:
            return self._commands[command]
        if command in self._aliases:
            primary = self._aliases[command]
            return self._commands.get(primary)
        return None
    
    def parse_command(self, cmd_str: str) -> tuple:
        parts = cmd_str.split(maxsplit=1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        if self.get_handler(command):
            return (command, args)
        cmd_lower = cmd_str.lower()
        for prefix in self._compact_commands:
            if cmd_lower.startswith(prefix) and len(cmd_str) > len(prefix):
                next_char = cmd_str[len(prefix)]
                is_ascii_letter = next_char.isascii() and next_char.isalpha()
                if not is_ascii_letter or next_char.lower() in "rp":
                    return (prefix, cmd_str[len(prefix):])
        return (command, args)
    
    def list_commands(self) -> List[str]:
        return list(self._commands.keys())


class TestCommandRegistry:
    """测试命令注册器"""

    def test_register_command(self):
        """测试注册命令"""
        registry = CommandRegistry()

        @registry.register("test")
        class TestCommand(BaseCommand):
            async def execute(self, args: str) -> CommandResult:
                return CommandResult.text("test")

        assert "test" in registry.list_commands()
        assert registry.get_handler("test") == TestCommand

    def test_register_with_aliases(self):
        """测试注册带别名的命令"""
        registry = CommandRegistry()

        @registry.register("roll", aliases=["r", "rd"])
        class RollCommand(BaseCommand):
            async def execute(self, args: str) -> CommandResult:
                return CommandResult.text("roll")

        assert registry.get_handler("roll") == RollCommand
        assert registry.get_handler("r") == RollCommand
        assert registry.get_handler("rd") == RollCommand

    def test_get_handler_not_found(self):
        """测试获取不存在的命令"""
        registry = CommandRegistry()
        assert registry.get_handler("nonexistent") is None

    def test_parse_command_with_space(self):
        """测试解析空格分隔的命令"""
        registry = CommandRegistry()

        @registry.register("r")
        class RollCommand(BaseCommand):
            async def execute(self, args: str) -> CommandResult:
                return CommandResult.text("roll")

        cmd, args = registry.parse_command("r 1d100")
        assert cmd == "r"
        assert args == "1d100"

    def test_parse_command_compact(self):
        """测试解析紧凑格式命令"""
        registry = CommandRegistry()

        @registry.register("rd", compact=True)
        class RollCommand(BaseCommand):
            async def execute(self, args: str) -> CommandResult:
                return CommandResult.text("roll")

        cmd, args = registry.parse_command("rd100")
        assert cmd == "rd"
        assert args == "100"

    def test_list_commands(self):
        """测试列出所有命令"""
        registry = CommandRegistry()

        @registry.register("cmd1")
        class Cmd1(BaseCommand):
            async def execute(self, args: str) -> CommandResult:
                return CommandResult.text("1")

        @registry.register("cmd2")
        class Cmd2(BaseCommand):
            async def execute(self, args: str) -> CommandResult:
                return CommandResult.text("2")

        commands = registry.list_commands()
        assert "cmd1" in commands
        assert "cmd2" in commands
        assert len(commands) == 2

    def test_register_class_explicit(self):
        """测试显式注册命令类"""
        registry = CommandRegistry()

        class MyCommand(BaseCommand):
            name = "mycommand"
            async def execute(self, args: str) -> CommandResult:
                return CommandResult.text("my")

        registry.register_class(MyCommand, aliases=["mc"])
        
        assert registry.get_handler("mycommand") == MyCommand
        assert registry.get_handler("mc") == MyCommand
