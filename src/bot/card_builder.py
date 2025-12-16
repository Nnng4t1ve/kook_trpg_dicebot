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

    @staticmethod
    def build_grow_character_card(char_name: str, skills: List[str]) -> str:
        """构建角色成长的交互卡片"""
        skills_text = "、".join(skills)
        card = {
            "type": "card",
            "theme": "success",
            "size": "lg",
            "modules": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain-text",
                        "content": f"📈 {char_name} 技能成长"
                    }
                },
                {
                    "type": "divider"
                },
                {
                    "type": "section",
                    "text": {
                        "type": "kmarkdown",
                        "content": f"可成长技能: **{skills_text}**\n\n点击下方按钮获取成长链接\n链接将通过**私信**发送给你"
                    }
                },
                {
                    "type": "action-group",
                    "elements": [
                        {
                            "type": "button",
                            "theme": "primary",
                            "value": json.dumps({
                                "action": "grow_character",
                                "char_name": char_name,
                                "skills": skills
                            }),
                            "click": "return-val",
                            "text": {
                                "type": "plain-text",
                                "content": "🎯 获取成长链接"
                            }
                        }
                    ]
                }
            ]
        }
        return json.dumps([card])

    @staticmethod
    def build_san_check_card(
        check_id: str,
        success_expr: str,
        fail_expr: str,
        description: str = "",
        kp_name: str = ""
    ) -> str:
        """构建 SAN Check 卡片消息"""
        card = {
            "type": "card",
            "theme": "danger",
            "size": "lg",
            "modules": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain-text",
                        "content": "🧠 SAN Check"
                    }
                },
                {
                    "type": "divider"
                },
                {
                    "type": "section",
                    "text": {
                        "type": "kmarkdown",
                        "content": f"成功损失: **{success_expr}** | 失败损失: **{fail_expr}**\n{description or '点击下方按钮进行 SAN Check'}"
                    }
                },
                {
                    "type": "action-group",
                    "elements": [
                        {
                            "type": "button",
                            "theme": "danger",
                            "value": json.dumps({
                                "action": "san_check",
                                "check_id": check_id,
                                "success_expr": success_expr,
                                "fail_expr": fail_expr
                            }),
                            "click": "return-val",
                            "text": {
                                "type": "plain-text",
                                "content": "🎲 进行 SAN Check"
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
    def build_san_check_result_card(
        user_name: str,
        char_name: str,
        roll: int,
        san: int,
        is_success: bool,
        loss_expr: str,
        loss: int,
        new_san: int,
        madness_info: list = None
    ) -> str:
        """构建 SAN Check 结果卡片"""
        theme = "warning" if is_success else "danger"
        result_text = "成功" if is_success else "失败"
        
        content = f"**{char_name}** 的 SAN Check\nD100 = **{roll}** / {san}  【{result_text}】\n损失: {loss_expr} = **{loss}**\nSAN: {san} → **{new_san}**"
        
        modules = [
            {
                "type": "section",
                "text": {
                    "type": "kmarkdown",
                    "content": content
                }
            }
        ]
        
        # 添加疯狂信息
        if madness_info:
            modules.append({"type": "divider"})
            modules.append({
                "type": "section",
                "text": {
                    "type": "kmarkdown",
                    "content": "\n".join(madness_info)
                }
            })
        
        card = {
            "type": "card",
            "theme": theme,
            "size": "lg",
            "modules": modules
        }
        
        return json.dumps([card])

    @staticmethod
    def build_opposed_check_card(
        check_id: str,
        initiator_name: str,
        target_id: str,
        initiator_skill: str,
        target_skill: str,
        initiator_bp: tuple = (0, 0),
        target_bp: tuple = (0, 0),
    ) -> str:
        """构建对抗检定卡片"""

        def bp_text(bonus: int, penalty: int) -> str:
            if bonus > 0:
                return f" 奖励骰×{bonus}"
            elif penalty > 0:
                return f" 惩罚骰×{penalty}"
            return ""

        init_bp = bp_text(initiator_bp[0], initiator_bp[1])
        tgt_bp = bp_text(target_bp[0], target_bp[1])

        if initiator_skill == target_skill:
            title = f"⚔️ {initiator_skill} 对抗检定"
            desc = f"**{initiator_name}** 向 (met){target_id}(met) 发起 **{initiator_skill}** 对抗"
        else:
            title = f"⚔️ {initiator_skill} vs {target_skill} 对抗检定"
            desc = f"**{initiator_name}**({initiator_skill}{init_bp}) 向 (met){target_id}(met)({target_skill}{tgt_bp}) 发起对抗"

        if init_bp or tgt_bp:
            if initiator_skill == target_skill:
                desc += f"\n{initiator_name}{init_bp} | 对方{tgt_bp}"

        card = {
            "type": "card",
            "theme": "warning",
            "size": "lg",
            "modules": [
                {
                    "type": "header",
                    "text": {"type": "plain-text", "content": title},
                },
                {"type": "divider"},
                {
                    "type": "section",
                    "text": {
                        "type": "kmarkdown",
                        "content": f"{desc}\n\n双方点击按钮进行检定",
                    },
                },
                {
                    "type": "action-group",
                    "elements": [
                        {
                            "type": "button",
                            "theme": "primary",
                            "value": json.dumps(
                                {
                                    "action": "opposed_check",
                                    "check_id": check_id,
                                }
                            ),
                            "click": "return-val",
                            "text": {"type": "plain-text", "content": "🎲 进行检定"},
                        }
                    ],
                },
            ],
        }
        return json.dumps([card])

    @staticmethod
    def build_opposed_result_card(
        initiator_name: str,
        target_name: str,
        skill_name: str,
        initiator_roll: int,
        initiator_target: int,
        initiator_level: str,
        target_roll: int,
        target_target: int,
        target_level: str,
        winner: str,  # "initiator", "target", "tie"
    ) -> str:
        """构建对抗检定结果卡片"""
        if winner == "initiator":
            theme = "success"
            result_text = f"🏆 **{initiator_name}** 胜出！"
        elif winner == "target":
            theme = "danger"
            result_text = f"🏆 **{target_name}** 胜出！"
        else:
            theme = "secondary"
            result_text = "⚖️ **平局！**"

        card = {
            "type": "card",
            "theme": theme,
            "size": "lg",
            "modules": [
                {
                    "type": "header",
                    "text": {"type": "plain-text", "content": f"⚔️ {skill_name} 对抗结果"},
                },
                {"type": "divider"},
                {
                    "type": "section",
                    "text": {
                        "type": "kmarkdown",
                        "content": f"**{initiator_name}**: D100={initiator_roll}/{initiator_target} 【{initiator_level}】\n**{target_name}**: D100={target_roll}/{target_target} 【{target_level}】",
                    },
                },
                {
                    "type": "section",
                    "text": {"type": "kmarkdown", "content": result_text},
                },
            ],
        }
        return json.dumps([card])
