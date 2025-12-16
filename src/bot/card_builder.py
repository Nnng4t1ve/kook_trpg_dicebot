"""卡片消息构建器"""
import json
from typing import List, Optional


class CardBuilder:
    """卡片消息构建器"""
    
    @staticmethod
    def build_check_card(
        check_id: str,
        skill_name: str,
        description: str = "",
        kp_name: str = ""
    ) -> str:
        """构建检定卡片消息"""
        card = {
            "type": "card",
            "theme": "warning",
            "size": "lg",
            "modules": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain-text",
                        "content": f"🎲 {skill_name} 检定"
                    }
                },
                {
                    "type": "divider"
                },
                {
                    "type": "section",
                    "text": {
                        "type": "kmarkdown",
                        "content": description or f"KP 发起了 **{skill_name}** 检定，点击下方按钮进行骰点"
                    }
                },
                {
                    "type": "action-group",
                    "elements": [
                        {
                            "type": "button",
                            "theme": "primary",
                            "value": json.dumps({
                                "action": "check",
                                "check_id": check_id,
                                "skill": skill_name
                            }),
                            "click": "return-val",
                            "text": {
                                "type": "plain-text",
                                "content": f"🎯 进行 {skill_name} 检定"
                            }
                        }
                    ]
                }
            ]
        }
        
        if kp_name:
            card["modules"].insert(2, {
                "type": "context",
                "elements": [
                    {
                        "type": "kmarkdown",
                        "content": f"发起者: {kp_name}"
                    }
                ]
            })
        
        return json.dumps([card])

    @staticmethod
    def build_check_result_card(
        user_name: str,
        skill_name: str,
        roll: int,
        target: int,
        result_text: str,
        is_success: bool
    ) -> str:
        """构建检定结果卡片"""
        theme = "success" if is_success else "danger"
        emoji = "✅" if is_success else "❌"
        
        card = {
            "type": "card",
            "theme": theme,
            "size": "lg",
            "modules": [
                {
                    "type": "section",
                    "text": {
                        "type": "kmarkdown",
                        "content": f"{emoji} **{user_name}** 的 **{skill_name}** 检定\nD100 = **{roll}** / {target}  【{result_text}】"
                    }
                }
            ]
        }
        
        return json.dumps([card])
    
    @staticmethod
    def build_multi_check_card(
        check_id: str,
        skills: List[str],
        description: str = "",
        kp_name: str = ""
    ) -> str:
        """构建多技能选择检定卡片"""
        buttons = []
        for skill in skills[:4]:  # 最多 4 个按钮
            buttons.append({
                "type": "button",
                "theme": "primary",
                "value": json.dumps({
                    "action": "check",
                    "check_id": check_id,
                    "skill": skill
                }),
                "click": "return-val",
                "text": {
                    "type": "plain-text",
                    "content": skill
                }
            })
        
        card = {
            "type": "card",
            "theme": "warning",
            "size": "lg",
            "modules": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain-text",
                        "content": "🎲 技能检定"
                    }
                },
                {
                    "type": "divider"
                },
                {
                    "type": "section",
                    "text": {
                        "type": "kmarkdown",
                        "content": description or "选择一个技能进行检定"
                    }
                },
                {
                    "type": "action-group",
                    "elements": buttons
                }
            ]
        }
        
        return json.dumps([card])

    @staticmethod
    def build_create_character_card() -> str:
        """构建创建角色卡的交互卡片"""
        card = {
            "type": "card",
            "theme": "info",
            "size": "lg",
            "modules": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain-text",
                        "content": "📋 创建角色卡"
                    }
                },
                {
                    "type": "divider"
                },
                {
                    "type": "section",
                    "text": {
                        "type": "kmarkdown",
                        "content": "点击下方按钮获取专属创建链接\n链接将通过**私信**发送给你，仅限本人使用"
                    }
                },
                {
                    "type": "action-group",
                    "elements": [
                        {
                            "type": "button",
                            "theme": "primary",
                            "value": json.dumps({"action": "create_character"}),
                            "click": "return-val",
                            "text": {
                                "type": "plain-text",
                                "content": "✨ 获取创建链接"
                            }
                        }
                    ]
                }
            ]
        }
        return json.dumps([card])
