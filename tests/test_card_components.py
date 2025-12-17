"""卡片组件构建单元测试"""
import pytest
import json
import sys
import os

# Add src to path for cards module (it has no complex dependencies)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from cards.components import CardComponents
from cards.builder import CardBuilder, MultiCardBuilder, VALID_THEMES, VALID_SIZES


class TestCardComponents:
    """测试卡片基础组件"""

    def test_header(self):
        """测试标题组件"""
        header = CardComponents.header("测试标题")
        assert header["type"] == "header"
        assert header["text"]["type"] == "plain-text"
        assert header["text"]["content"] == "测试标题"

    def test_section_kmarkdown(self):
        """测试 KMarkdown 段落组件"""
        section = CardComponents.section("**粗体**文本")
        assert section["type"] == "section"
        assert section["text"]["type"] == "kmarkdown"
        assert section["text"]["content"] == "**粗体**文本"

    def test_section_plain_text(self):
        """测试纯文本段落组件"""
        section = CardComponents.section("纯文本", mode="plain-text")
        assert section["text"]["type"] == "plain-text"

    def test_section_with_accessory(self):
        """测试带附件的段落组件"""
        img = CardComponents.image("http://example.com/img.png")
        section = CardComponents.section("文本", accessory=img)
        assert "accessory" in section
        assert section["accessory"]["type"] == "image"

    def test_divider(self):
        """测试分隔线组件"""
        divider = CardComponents.divider()
        assert divider["type"] == "divider"

    def test_button(self):
        """测试按钮组件"""
        btn = CardComponents.button("点击", {"action": "test"}, theme="success")
        assert btn["type"] == "button"
        assert btn["theme"] == "success"
        assert btn["text"]["content"] == "点击"
        # value should be JSON string
        assert json.loads(btn["value"]) == {"action": "test"}

    def test_button_string_value(self):
        """测试字符串值按钮"""
        btn = CardComponents.button("点击", "simple_value")
        assert btn["value"] == "simple_value"

    def test_action_group(self):
        """测试按钮组组件"""
        buttons = [
            CardComponents.button("按钮1", "v1"),
            CardComponents.button("按钮2", "v2"),
        ]
        group = CardComponents.action_group(buttons)
        assert group["type"] == "action-group"
        assert len(group["elements"]) == 2

    def test_action_group_max_buttons(self):
        """测试按钮组最多4个按钮"""
        buttons = [CardComponents.button(f"按钮{i}", f"v{i}") for i in range(6)]
        group = CardComponents.action_group(buttons)
        assert len(group["elements"]) == 4  # 限制为4个

    def test_context(self):
        """测试上下文组件"""
        ctx = CardComponents.context("小字提示")
        assert ctx["type"] == "context"
        assert ctx["elements"][0]["content"] == "小字提示"

    def test_image(self):
        """测试图片组件"""
        img = CardComponents.image("http://example.com/img.png", alt="图片", size="sm", circle=True)
        assert img["type"] == "image"
        assert img["src"] == "http://example.com/img.png"
        assert img["alt"] == "图片"
        assert img["size"] == "sm"
        assert img["circle"] is True


class TestCardBuilder:
    """测试卡片构建器"""

    def test_builder_chain(self):
        """测试链式调用"""
        card = (CardBuilder()
            .header("标题")
            .divider()
            .section("内容")
            .context("提示"))
        
        assert len(card._modules) == 4

    def test_builder_theme(self):
        """测试卡片主题"""
        for theme in VALID_THEMES:
            card = CardBuilder(theme=theme)
            assert card._theme == theme

    def test_builder_invalid_theme(self):
        """测试无效主题"""
        with pytest.raises(ValueError):
            CardBuilder(theme="invalid")

    def test_builder_invalid_size(self):
        """测试无效大小"""
        with pytest.raises(ValueError):
            CardBuilder(size="invalid")

    def test_build_json(self):
        """测试构建 JSON"""
        card = CardBuilder().header("测试").build()
        parsed = json.loads(card)
        assert isinstance(parsed, list)
        assert parsed[0]["type"] == "card"
        assert parsed[0]["modules"][0]["type"] == "header"

    def test_validate_empty_card(self):
        """测试验证空卡片"""
        card = CardBuilder()
        with pytest.raises(ValueError, match="at least one module"):
            card.validate()

    def test_validate_too_many_modules(self):
        """测试验证模块过多"""
        card = CardBuilder()
        for i in range(51):
            card.section(f"内容{i}")
        with pytest.raises(ValueError, match="more than 50 modules"):
            card.validate()

    def test_buttons_method(self):
        """测试添加按钮组"""
        btn1 = CardComponents.button("按钮1", "v1")
        btn2 = CardComponents.button("按钮2", "v2")
        card = CardBuilder().buttons(btn1, btn2)
        
        assert card._modules[0]["type"] == "action-group"
        assert len(card._modules[0]["elements"]) == 2

    def test_to_dict(self):
        """测试转换为字典"""
        card = CardBuilder(theme="success", size="sm").header("标题")
        d = card.to_dict()
        
        assert d["type"] == "card"
        assert d["theme"] == "success"
        assert d["size"] == "sm"
        assert len(d["modules"]) == 1


class TestMultiCardBuilder:
    """测试多卡片构建器"""

    def test_multi_card_build(self):
        """测试构建多卡片"""
        card1 = CardBuilder(theme="primary").header("卡片1")
        card2 = CardBuilder(theme="success").header("卡片2")
        
        multi = MultiCardBuilder().add(card1).add(card2)
        result = json.loads(multi.build())
        
        assert len(result) == 2
        assert result[0]["theme"] == "primary"
        assert result[1]["theme"] == "success"
