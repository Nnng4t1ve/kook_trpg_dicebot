"""卡片基础组件构建器

提供 KOOK 卡片消息的基础组件构建方法，用于组合构建各种卡片模板。
"""

import json
from typing import Any, Dict, List, Optional, Union


class CardComponents:
    """卡片基础组件构建器"""

    @staticmethod
    def header(text: str) -> Dict[str, Any]:
        """
        标题组件
        
        Args:
            text: 标题文本
            
        Returns:
            标题组件字典
        """
        return {
            "type": "header",
            "text": {
                "type": "plain-text",
                "content": text
            }
        }

    @staticmethod
    def section(
        content: str,
        mode: str = "kmarkdown",
        accessory: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        文本段落组件
        
        Args:
            content: 文本内容
            mode: 文本类型，"kmarkdown" 或 "plain-text"
            accessory: 附件元素（如图片、按钮）
            
        Returns:
            段落组件字典
        """
        section = {
            "type": "section",
            "text": {
                "type": mode,
                "content": content
            }
        }
        if accessory:
            section["accessory"] = accessory
        return section

    @staticmethod
    def divider() -> Dict[str, Any]:
        """
        分隔线组件
        
        Returns:
            分隔线组件字典
        """
        return {"type": "divider"}

    @staticmethod
    def button(
        text: str,
        value: Union[str, Dict[str, Any]],
        theme: str = "primary",
        click: str = "return-val"
    ) -> Dict[str, Any]:
        """
        按钮组件
        
        Args:
            text: 按钮文本
            value: 按钮点击返回值，可以是字符串或字典（会自动序列化为 JSON）
            theme: 按钮主题，可选 "primary", "success", "danger", "warning", "info", "secondary"
            click: 点击行为，"return-val" 返回值，"link" 跳转链接
            
        Returns:
            按钮组件字典
        """
        if isinstance(value, dict):
            value = json.dumps(value)
        return {
            "type": "button",
            "theme": theme,
            "value": value,
            "click": click,
            "text": {
                "type": "plain-text",
                "content": text
            }
        }

    @staticmethod
    def action_group(buttons: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        按钮组组件
        
        Args:
            buttons: 按钮组件列表（最多 4 个）
            
        Returns:
            按钮组组件字典
        """
        return {
            "type": "action-group",
            "elements": buttons[:4]  # KOOK 限制最多 4 个按钮
        }

    @staticmethod
    def context(text: str, mode: str = "kmarkdown") -> Dict[str, Any]:
        """
        上下文组件（小字提示）
        
        Args:
            text: 上下文文本
            mode: 文本类型，"kmarkdown" 或 "plain-text"
            
        Returns:
            上下文组件字典
        """
        return {
            "type": "context",
            "elements": [
                {
                    "type": mode,
                    "content": text
                }
            ]
        }

    @staticmethod
    def context_with_elements(elements: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        带多个元素的上下文组件
        
        Args:
            elements: 元素列表（文本或图片）
            
        Returns:
            上下文组件字典
        """
        return {
            "type": "context",
            "elements": elements
        }

    @staticmethod
    def image(url: str, alt: str = "", size: str = "lg", circle: bool = False) -> Dict[str, Any]:
        """
        图片组件（用于 accessory）
        
        Args:
            url: 图片 URL
            alt: 替代文本
            size: 图片大小，"sm" 或 "lg"
            circle: 是否圆形
            
        Returns:
            图片组件字典
        """
        img = {
            "type": "image",
            "src": url,
            "size": size,
            "circle": circle
        }
        if alt:
            img["alt"] = alt
        return img

    @staticmethod
    def container(images: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        图片容器组件（用于展示大图）
        
        Args:
            images: 图片组件列表
            
        Returns:
            图片容器组件字典
        """
        return {
            "type": "container",
            "elements": images
        }

    @staticmethod
    def image_group(images: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        图片组组件（多图并排）
        
        Args:
            images: 图片组件列表
            
        Returns:
            图片组组件字典
        """
        return {
            "type": "image-group",
            "elements": images
        }

    @staticmethod
    def countdown(end_time: int, mode: str = "day", start_time: int = None) -> Dict[str, Any]:
        """
        倒计时组件
        
        Args:
            end_time: 结束时间戳（毫秒）
            mode: 显示模式，"day", "hour", "second"
            start_time: 开始时间戳（毫秒），仅 second 模式需要
            
        Returns:
            倒计时组件字典
        """
        countdown = {
            "type": "countdown",
            "mode": mode,
            "endTime": end_time
        }
        if start_time and mode == "second":
            countdown["startTime"] = start_time
        return countdown

    @staticmethod
    def invite(code: str) -> Dict[str, Any]:
        """
        邀请组件
        
        Args:
            code: 邀请码
            
        Returns:
            邀请组件字典
        """
        return {
            "type": "invite",
            "code": code
        }

    @staticmethod
    def file(url: str, title: str, size: int = None) -> Dict[str, Any]:
        """
        文件组件
        
        Args:
            url: 文件 URL
            title: 文件名
            size: 文件大小（字节）
            
        Returns:
            文件组件字典
        """
        file_comp = {
            "type": "file",
            "src": url,
            "title": title
        }
        if size:
            file_comp["size"] = size
        return file_comp

    @staticmethod
    def audio(url: str, title: str, cover: str = None) -> Dict[str, Any]:
        """
        音频组件
        
        Args:
            url: 音频 URL
            title: 音频标题
            cover: 封面图 URL
            
        Returns:
            音频组件字典
        """
        audio = {
            "type": "audio",
            "src": url,
            "title": title
        }
        if cover:
            audio["cover"] = cover
        return audio

    @staticmethod
    def video(url: str, title: str) -> Dict[str, Any]:
        """
        视频组件
        
        Args:
            url: 视频 URL
            title: 视频标题
            
        Returns:
            视频组件字典
        """
        return {
            "type": "video",
            "src": url,
            "title": title
        }

    @staticmethod
    def kmarkdown_text(content: str) -> Dict[str, Any]:
        """
        KMarkdown 文本元素（用于 context 等）
        
        Args:
            content: KMarkdown 内容
            
        Returns:
            文本元素字典
        """
        return {
            "type": "kmarkdown",
            "content": content
        }

    @staticmethod
    def plain_text(content: str) -> Dict[str, Any]:
        """
        纯文本元素
        
        Args:
            content: 文本内容
            
        Returns:
            文本元素字典
        """
        return {
            "type": "plain-text",
            "content": content
        }
