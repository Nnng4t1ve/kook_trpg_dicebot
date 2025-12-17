"""卡片构建器

提供链式调用的卡片构建器，用于方便地构建 KOOK 卡片消息。
"""

import json
from typing import Any, Dict, List, Optional, Union

from .components import CardComponents


# 有效的卡片主题
VALID_THEMES = {"primary", "success", "danger", "warning", "info", "secondary"}

# 有效的卡片大小
VALID_SIZES = {"sm", "lg"}

# 有效的模块类型
VALID_MODULE_TYPES = {
    "header", "section", "divider", "action-group", "context",
    "container", "image-group", "countdown", "invite", "file", "audio", "video"
}


class CardBuilder:
    """
    卡片构建器 - 链式调用构建卡片
    
    Example:
        card = (CardBuilder(theme="warning")
            .header("🎲 技能检定")
            .divider()
            .section("点击按钮进行检定")
            .buttons(
                CardComponents.button("进行检定", {"action": "check"})
            )
            .build())
    """

    def __init__(self, theme: str = "primary", size: str = "lg"):
        """
        初始化卡片构建器
        
        Args:
            theme: 卡片主题，可选 "primary", "success", "danger", "warning", "info", "secondary"
            size: 卡片大小，"sm" 或 "lg"
        """
        if theme not in VALID_THEMES:
            raise ValueError(f"Invalid theme: {theme}. Must be one of {VALID_THEMES}")
        if size not in VALID_SIZES:
            raise ValueError(f"Invalid size: {size}. Must be one of {VALID_SIZES}")
        
        self._theme = theme
        self._size = size
        self._modules: List[Dict[str, Any]] = []

    def header(self, text: str) -> "CardBuilder":
        """
        添加标题
        
        Args:
            text: 标题文本
            
        Returns:
            self，支持链式调用
        """
        self._modules.append(CardComponents.header(text))
        return self

    def section(
        self,
        content: str,
        mode: str = "kmarkdown",
        accessory: Optional[Dict[str, Any]] = None
    ) -> "CardBuilder":
        """
        添加文本段落
        
        Args:
            content: 文本内容
            mode: 文本类型，"kmarkdown" 或 "plain-text"
            accessory: 附件元素
            
        Returns:
            self，支持链式调用
        """
        self._modules.append(CardComponents.section(content, mode, accessory))
        return self

    def divider(self) -> "CardBuilder":
        """
        添加分隔线
        
        Returns:
            self，支持链式调用
        """
        self._modules.append(CardComponents.divider())
        return self

    def buttons(self, *buttons: Dict[str, Any]) -> "CardBuilder":
        """
        添加按钮组
        
        Args:
            *buttons: 按钮组件（最多 4 个）
            
        Returns:
            self，支持链式调用
        """
        self._modules.append(CardComponents.action_group(list(buttons)))
        return self

    def button(
        self,
        text: str,
        value: Union[str, Dict[str, Any]],
        theme: str = "primary"
    ) -> "CardBuilder":
        """
        添加单个按钮（作为按钮组）
        
        Args:
            text: 按钮文本
            value: 按钮返回值
            theme: 按钮主题
            
        Returns:
            self，支持链式调用
        """
        btn = CardComponents.button(text, value, theme)
        self._modules.append(CardComponents.action_group([btn]))
        return self

    def context(self, text: str, mode: str = "kmarkdown") -> "CardBuilder":
        """
        添加上下文（小字提示）
        
        Args:
            text: 上下文文本
            mode: 文本类型
            
        Returns:
            self，支持链式调用
        """
        self._modules.append(CardComponents.context(text, mode))
        return self

    def image(self, url: str, alt: str = "") -> "CardBuilder":
        """
        添加图片容器
        
        Args:
            url: 图片 URL
            alt: 替代文本
            
        Returns:
            self，支持链式调用
        """
        img = CardComponents.image(url, alt)
        self._modules.append(CardComponents.container([img]))
        return self

    def images(self, *urls: str) -> "CardBuilder":
        """
        添加图片组
        
        Args:
            *urls: 图片 URL 列表
            
        Returns:
            self，支持链式调用
        """
        imgs = [CardComponents.image(url) for url in urls]
        self._modules.append(CardComponents.image_group(imgs))
        return self

    def countdown(
        self,
        end_time: int,
        mode: str = "day",
        start_time: int = None
    ) -> "CardBuilder":
        """
        添加倒计时
        
        Args:
            end_time: 结束时间戳（毫秒）
            mode: 显示模式
            start_time: 开始时间戳
            
        Returns:
            self，支持链式调用
        """
        self._modules.append(CardComponents.countdown(end_time, mode, start_time))
        return self

    def file(self, url: str, title: str, size: int = None) -> "CardBuilder":
        """
        添加文件
        
        Args:
            url: 文件 URL
            title: 文件名
            size: 文件大小
            
        Returns:
            self，支持链式调用
        """
        self._modules.append(CardComponents.file(url, title, size))
        return self

    def audio(self, url: str, title: str, cover: str = None) -> "CardBuilder":
        """
        添加音频
        
        Args:
            url: 音频 URL
            title: 音频标题
            cover: 封面图
            
        Returns:
            self，支持链式调用
        """
        self._modules.append(CardComponents.audio(url, title, cover))
        return self

    def video(self, url: str, title: str) -> "CardBuilder":
        """
        添加视频
        
        Args:
            url: 视频 URL
            title: 视频标题
            
        Returns:
            self，支持链式调用
        """
        self._modules.append(CardComponents.video(url, title))
        return self

    def module(self, module: Dict[str, Any]) -> "CardBuilder":
        """
        添加自定义模块
        
        Args:
            module: 模块字典
            
        Returns:
            self，支持链式调用
        """
        self._modules.append(module)
        return self

    def validate(self) -> bool:
        """
        验证卡片结构是否符合 KOOK 卡片消息格式
        
        Returns:
            验证是否通过
            
        Raises:
            ValueError: 验证失败时抛出异常
        """
        if not self._modules:
            raise ValueError("Card must have at least one module")
        
        if len(self._modules) > 50:
            raise ValueError("Card cannot have more than 50 modules")
        
        for i, module in enumerate(self._modules):
            if "type" not in module:
                raise ValueError(f"Module {i} missing 'type' field")
            
            module_type = module["type"]
            if module_type not in VALID_MODULE_TYPES:
                raise ValueError(f"Module {i} has invalid type: {module_type}")
            
            # 验证 header 模块
            if module_type == "header":
                if "text" not in module:
                    raise ValueError(f"Header module {i} missing 'text' field")
                if module["text"].get("type") != "plain-text":
                    raise ValueError(f"Header module {i} text must be plain-text")
            
            # 验证 section 模块
            if module_type == "section":
                if "text" not in module:
                    raise ValueError(f"Section module {i} missing 'text' field")
            
            # 验证 action-group 模块
            if module_type == "action-group":
                if "elements" not in module:
                    raise ValueError(f"Action-group module {i} missing 'elements' field")
                if len(module["elements"]) > 4:
                    raise ValueError(f"Action-group module {i} cannot have more than 4 buttons")
            
            # 验证 context 模块
            if module_type == "context":
                if "elements" not in module:
                    raise ValueError(f"Context module {i} missing 'elements' field")
        
        return True

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为卡片字典
        
        Returns:
            卡片字典
        """
        return {
            "type": "card",
            "theme": self._theme,
            "size": self._size,
            "modules": self._modules
        }

    def build(self, validate: bool = True) -> str:
        """
        构建并返回 JSON 字符串
        
        Args:
            validate: 是否验证卡片结构
            
        Returns:
            卡片消息 JSON 字符串（包含在数组中）
        """
        if validate:
            self.validate()
        return json.dumps([self.to_dict()])

    def build_raw(self, validate: bool = True) -> str:
        """
        构建并返回单个卡片的 JSON 字符串（不包含数组）
        
        Args:
            validate: 是否验证卡片结构
            
        Returns:
            单个卡片的 JSON 字符串
        """
        if validate:
            self.validate()
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, card_dict: Dict[str, Any]) -> "CardBuilder":
        """
        从字典创建 CardBuilder
        
        Args:
            card_dict: 卡片字典
            
        Returns:
            CardBuilder 实例
        """
        builder = cls(
            theme=card_dict.get("theme", "primary"),
            size=card_dict.get("size", "lg")
        )
        builder._modules = card_dict.get("modules", [])
        return builder


class MultiCardBuilder:
    """
    多卡片构建器 - 用于构建包含多个卡片的消息
    """

    def __init__(self):
        self._cards: List[CardBuilder] = []

    def add(self, card: CardBuilder) -> "MultiCardBuilder":
        """
        添加卡片
        
        Args:
            card: CardBuilder 实例
            
        Returns:
            self，支持链式调用
        """
        self._cards.append(card)
        return self

    def build(self, validate: bool = True) -> str:
        """
        构建并返回 JSON 字符串
        
        Args:
            validate: 是否验证卡片结构
            
        Returns:
            多卡片消息 JSON 字符串
        """
        cards = []
        for card in self._cards:
            if validate:
                card.validate()
            cards.append(card.to_dict())
        return json.dumps(cards)
