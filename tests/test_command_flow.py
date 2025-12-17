"""命令执行流程集成测试"""
import pytest
from dataclasses import dataclass
from abc import ABC, abstractmethod
from typing import Callable, Dict, List, Optional, Type
from unittest.mock import MagicMock, AsyncMock


# 定义测试所需的类
@dataclass
class CommandResult:
    """命令执行结果"""
    content: Optional[str] = None
    is_card: bool = False
    quote: bool = True
    
    @classmethod
    def text(cls, content: str, quote: bool = True) -> "CommandResult":
        return cls(content=content, is_card=False, quote=quote)
    
    @classmethod
    def card(cls, content: str) -> "CommandResult":
        return cls(content=content, is_card=True, quote=False)
    
    @classmethod
    def empty(cls) -> "CommandResult":
        return cls(content=None)


@dataclass
class CommandContext:
    """命令执行上下文"""
    user_id: str
    user_name: str
    channel_id: str
    channel_type: str
    msg_id: str
    client: object = None
    char_manager: object = None
    npc_manager: object = None
    check_manager: object = None
    db: object = None


class BaseCommand(ABC):
    """命令基类"""
    name: str = ""
    aliases: list = []
    description: str = ""
    usage: str = ""
    
    def __init__(self, ctx: CommandContext):
        self.ctx = ctx
    
    @abstractmethod
    async def execute(self, args: str) -> CommandResult:
        pass
    
    def help(self) -> str:
        lines = [f"**{self.name}** - {self.description}"]
        if self.usage:
            lines.append(f"用法: {self.usage}")
        if self.aliases:
            lines.append(f"别名: {', '.join(self.aliases)}")
        return "\n".join(lines)


class CommandRegistry:
    """命令注册器"""
    
    def __init__(self):
        self._commands: Dict[str, Type[BaseCommand]] = {}
        self._aliases: Dict[str, str] = {}
    
    def register(self, name: str, aliases: Optional[List[str]] = None):
        def decorator(cls: Type[BaseCommand]) -> Type[BaseCommand]:
            cls.name = name
            cls.aliases = aliases or []
            self._commands[name] = cls
            for alias in cls.aliases:
                self._aliases[alias] = name
            return cls
        return decorator
    
    def get_handler(self, command: str) -> Optional[Type[BaseCommand]]:
        if command in self._commands:
            return self._commands[command]
        if command in self._aliases:
            return self._commands.get(self._aliases[command])
        return None
    
    async def execute(self, cmd_str: str, ctx: CommandContext) -> Optional[CommandResult]:
        parts = cmd_str.split(maxsplit=1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        handler_cls = self.get_handler(command)
        if not handler_cls:
            return None
        
        handler = handler_cls(ctx)
        return await handler.execute(args)


class TestCommandExecutionFlow:
    """测试命令执行流程"""

    @pytest.fixture
    def registry(self):
        """创建命令注册器"""
        return CommandRegistry()

    @pytest.fixture
    def context(self):
        """创建命令上下文"""
        return CommandContext(
            user_id="user123",
            user_name="TestUser",
            channel_id="channel456",
            channel_type="GROUP",
            msg_id="msg789",
            client=MagicMock(),
            char_manager=MagicMock(),
            npc_manager=MagicMock(),
            check_manager=MagicMock(),
            db=MagicMock(),
        )

    @pytest.mark.asyncio
    async def test_command_registration_and_execution(self, registry, context):
        """测试命令注册和执行"""
        @registry.register("echo")
        class EchoCommand(BaseCommand):
            async def execute(self, args: str) -> CommandResult:
                return CommandResult.text(f"Echo: {args}")
        
        result = await registry.execute("echo hello world", context)
        
        assert result is not None
        assert result.content == "Echo: hello world"
        assert result.is_card is False

    @pytest.mark.asyncio
    async def test_command_with_alias(self, registry, context):
        """测试命令别名执行"""
        @registry.register("roll", aliases=["r", "rd"])
        class RollCommand(BaseCommand):
            async def execute(self, args: str) -> CommandResult:
                return CommandResult.text(f"Rolling: {args}")
        
        # 使用主命令
        result1 = await registry.execute("roll 1d100", context)
        assert result1.content == "Rolling: 1d100"
        
        # 使用别名
        result2 = await registry.execute("r 2d6", context)
        assert result2.content == "Rolling: 2d6"

    @pytest.mark.asyncio
    async def test_unknown_command(self, registry, context):
        """测试未知命令"""
        result = await registry.execute("unknown arg", context)
        assert result is None

    @pytest.mark.asyncio
    async def test_command_returns_card(self, registry, context):
        """测试命令返回卡片"""
        @registry.register("card")
        class CardCommand(BaseCommand):
            async def execute(self, args: str) -> CommandResult:
                return CommandResult.card('[{"type":"card"}]')
        
        result = await registry.execute("card", context)
        
        assert result is not None
        assert result.is_card is True
        assert result.quote is False

    @pytest.mark.asyncio
    async def test_command_returns_empty(self, registry, context):
        """测试命令返回空响应"""
        @registry.register("silent")
        class SilentCommand(BaseCommand):
            async def execute(self, args: str) -> CommandResult:
                return CommandResult.empty()
        
        result = await registry.execute("silent", context)
        
        assert result is not None
        assert result.content is None

    @pytest.mark.asyncio
    async def test_command_context_access(self, registry, context):
        """测试命令访问上下文"""
        @registry.register("whoami")
        class WhoamiCommand(BaseCommand):
            async def execute(self, args: str) -> CommandResult:
                return CommandResult.text(
                    f"User: {self.ctx.user_name} ({self.ctx.user_id})"
                )
        
        result = await registry.execute("whoami", context)
        
        assert "TestUser" in result.content
        assert "user123" in result.content

    def test_command_help(self, registry):
        """测试命令帮助信息"""
        @registry.register("test", aliases=["t"])
        class TestCommand(BaseCommand):
            description = "测试命令"
            usage = ".test <参数>"
            
            async def execute(self, args: str) -> CommandResult:
                return CommandResult.text("test")
        
        cmd = TestCommand(None)
        help_text = cmd.help()
        
        assert "test" in help_text
        assert "测试命令" in help_text
        assert ".test <参数>" in help_text
        assert "t" in help_text


class TestCommandResultTypes:
    """测试命令结果类型"""

    def test_text_result(self):
        """测试文本结果"""
        result = CommandResult.text("Hello")
        assert result.content == "Hello"
        assert result.is_card is False
        assert result.quote is True

    def test_text_result_no_quote(self):
        """测试不引用的文本结果"""
        result = CommandResult.text("Hello", quote=False)
        assert result.quote is False

    def test_card_result(self):
        """测试卡片结果"""
        result = CommandResult.card('[{"type":"card"}]')
        assert result.is_card is True
        assert result.quote is False

    def test_empty_result(self):
        """测试空结果"""
        result = CommandResult.empty()
        assert result.content is None
