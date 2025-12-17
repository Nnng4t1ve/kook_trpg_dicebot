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
    def build_grow_character_card(char_name: str, skills: List[str], initiator_id: str) -> str:
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
                    "type": "context",
                    "elements": [
                        {
                            "type": "kmarkdown",
                            "content": f"只有 (met){initiator_id}(met) 可以获取链接"
                        }
                    ]
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
                                "skills": skills,
                                "initiator_id": initiator_id
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

    @staticmethod
    def build_npc_opposed_check_card(
        check_id: str,
        npc_name: str,
        target_id: str,
        npc_skill: str,
        target_skill: str,
        npc_roll: int,
        npc_target: int,
        npc_level: str,
        npc_bp: tuple = (0, 0),
        target_bp: tuple = (0, 0),
    ) -> str:
        """构建 NPC 对抗检定卡片 (NPC 已完成检定)"""

        def bp_text(bonus: int, penalty: int) -> str:
            if bonus > 0:
                return f" 奖励骰×{bonus}"
            elif penalty > 0:
                return f" 惩罚骰×{penalty}"
            return ""

        tgt_bp = bp_text(target_bp[0], target_bp[1])

        if npc_skill == target_skill:
            title = f"⚔️ {npc_skill} 对抗检定"
        else:
            title = f"⚔️ {npc_skill} vs {target_skill} 对抗检定"

        desc = (
            f"**{npc_name}** (NPC) 向 (met){target_id}(met) 发起对抗\n\n"
            f"**{npc_name}**: D100={npc_roll}/{npc_target} 【{npc_level}】\n\n"
            f"(met){target_id}(met) 点击按钮进行 **{target_skill}**{tgt_bp} 检定"
        )

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
                        "content": desc,
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
    def build_player_vs_npc_opposed_card(
        check_id: str,
        player_name: str,
        player_id: str,
        npc_name: str,
        player_skill: str,
        npc_skill: str,
        npc_roll: int,
        npc_target: int,
        npc_level: str,
        player_bp: tuple = (0, 0),
        npc_bp: tuple = (0, 0),
    ) -> str:
        """构建玩家 vs NPC 对抗检定卡片 (NPC 已完成检定，等待玩家)"""

        def bp_text(bonus: int, penalty: int) -> str:
            if bonus > 0:
                return f" 奖励骰×{bonus}"
            elif penalty > 0:
                return f" 惩罚骰×{penalty}"
            return ""

        player_bp_text = bp_text(player_bp[0], player_bp[1])

        if player_skill == npc_skill:
            title = f"⚔️ {player_skill} 对抗检定"
        else:
            title = f"⚔️ {player_skill} vs {npc_skill} 对抗检定"

        desc = (
            f"**{player_name}** 向 **{npc_name}** (NPC) 发起对抗\n\n"
            f"**{npc_name}**: D100={npc_roll}/{npc_target} 【{npc_level}】\n\n"
            f"(met){player_id}(met) 点击按钮进行 **{player_skill}**{player_bp_text} 检定"
        )

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
                        "content": desc,
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
    def build_damage_card(
        check_id: str,
        initiator_name: str,
        target_name: str,
        target_type: str,
        damage_expr: str,
        target_id: str = None,
    ) -> str:
        """构建伤害确认卡片"""
        if target_type == "npc":
            target_display = f"**{target_name}** (NPC)"
        else:
            target_display = f"**{target_name}** (met){target_id}(met)"

        card = {
            "type": "card",
            "theme": "danger",
            "size": "lg",
            "modules": [
                {
                    "type": "header",
                    "text": {"type": "plain-text", "content": "⚔️ 伤害确认"},
                },
                {"type": "divider"},
                {
                    "type": "section",
                    "text": {
                        "type": "kmarkdown",
                        "content": f"**{initiator_name}** 对 {target_display} 造成伤害\n伤害: **{damage_expr}**",
                    },
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "kmarkdown",
                            "content": f"只有 **{initiator_name}** 可以确认伤害",
                        }
                    ],
                },
                {
                    "type": "action-group",
                    "elements": [
                        {
                            "type": "button",
                            "theme": "danger",
                            "value": json.dumps(
                                {
                                    "action": "confirm_damage",
                                    "check_id": check_id,
                                }
                            ),
                            "click": "return-val",
                            "text": {"type": "plain-text", "content": "🎲 确认伤害"},
                        }
                    ],
                },
            ],
        }
        return json.dumps([card])

    @staticmethod
    def build_damage_result_card(
        target_name: str,
        target_type: str,
        damage_expr: str,
        damage: int,
        old_hp: int = None,
        new_hp: int = None,
        max_hp: int = None,
        hp_bar: str = None,
        status_level: str = None,
        status_desc: str = None,
    ) -> str:
        """构建伤害结果卡片"""
        theme = "danger"

        if target_type == "npc":
            # NPC 不显示具体 HP 数值
            content = (
                f"⚔️ **{target_name}** 受到攻击\n"
                f"伤害: {damage_expr} = **{damage}**\n"
                f"[{hp_bar}]\n"
                f"状态: _{status_desc}_"
            )
            if new_hp == 0:
                content += f"\n\n💀 **{target_name}** {status_desc}"
        else:
            # 玩家显示具体 HP 数值
            content = (
                f"⚔️ **{target_name}** 受到伤害\n"
                f"伤害: {damage_expr} = **{damage}**\n"
                f"HP: {old_hp} → **{new_hp}** / {max_hp}\n"
                f"[{hp_bar}] {status_level}"
            )
            if new_hp == 0:
                content += "\n\n💀 **角色倒下了！**"

        card = {
            "type": "card",
            "theme": theme,
            "size": "lg",
            "modules": [
                {
                    "type": "section",
                    "text": {
                        "type": "kmarkdown",
                        "content": content,
                    },
                },
            ],
        }
        return json.dumps([card])

    @staticmethod
    def build_initiative_card(participants: List[tuple]) -> str:
        """
        构建先攻顺序卡片
        
        Args:
            participants: [(name, dex, type, user_id), ...] 已按 DEX 排序
        """
        # 构建顺序列表
        lines = []
        for i, (name, dex, p_type, user_id) in enumerate(participants, 1):
            if p_type == "npc":
                lines.append(f"**{i}.** {name} (NPC) - DEX: **{dex}**")
            elif p_type == "unknown":
                lines.append(f"**{i}.** {name} - DEX: **?**")
            else:
                # 玩家
                if user_id:
                    lines.append(f"**{i}.** {name} (met){user_id}(met) - DEX: **{dex}**")
                else:
                    lines.append(f"**{i}.** {name} - DEX: **{dex}**")
        
        content = "\n".join(lines)
        
        card = {
            "type": "card",
            "theme": "info",
            "size": "lg",
            "modules": [
                {
                    "type": "header",
                    "text": {"type": "plain-text", "content": "⚡ 先攻顺序表"},
                },
                {"type": "divider"},
                {
                    "type": "section",
                    "text": {
                        "type": "kmarkdown",
                        "content": content,
                    },
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "kmarkdown",
                            "content": "按 DEX 从高到低排序",
                        }
                    ],
                },
            ],
        }
        return json.dumps([card])

    @staticmethod
    def build_con_check_card(
        check_id: str,
        target_name: str,
        target_id: str,
        damage: int,
        max_hp: int,
    ) -> str:
        """构建体质检定卡片 (重伤昏迷检定)"""
        card = {
            "type": "card",
            "theme": "warning",
            "size": "lg",
            "modules": [
                {
                    "type": "header",
                    "text": {"type": "plain-text", "content": "💫 重伤昏迷检定"},
                },
                {"type": "divider"},
                {
                    "type": "section",
                    "text": {
                        "type": "kmarkdown",
                        "content": (
                            f"**{target_name}** 受到了 **{damage}** 点伤害 (≥ HP上限的一半: {max_hp // 2})\n"
                            f"需要进行 **体质(CON)** 检定\n"
                            f"成功: 保持清醒 | 失败: 陷入昏迷"
                        ),
                    },
                },
                {
                    "type": "action-group",
                    "elements": [
                        {
                            "type": "button",
                            "theme": "warning",
                            "value": json.dumps(
                                {
                                    "action": "con_check",
                                    "check_id": check_id,
                                }
                            ),
                            "click": "return-val",
                            "text": {"type": "plain-text", "content": "🎲 进行体质检定"},
                        }
                    ],
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "kmarkdown",
                            "content": f"(met){target_id}(met) 点击按钮进行检定",
                        }
                    ],
                },
            ],
        }
        return json.dumps([card])

    @staticmethod
    def build_con_check_result_card(
        target_name: str,
        roll: int,
        con_value: int,
        is_success: bool,
        is_npc: bool = False,
    ) -> str:
        """构建体质检定结果卡片"""
        theme = "success" if is_success else "danger"
        result_text = "成功" if is_success else "失败"
        status = "保持清醒" if is_success else "陷入昏迷"
        emoji = "✅" if is_success else "💫"

        npc_tag = " (NPC)" if is_npc else ""

        card = {
            "type": "card",
            "theme": theme,
            "size": "lg",
            "modules": [
                {
                    "type": "section",
                    "text": {
                        "type": "kmarkdown",
                        "content": (
                            f"{emoji} **{target_name}**{npc_tag} 的体质检定\n"
                            f"D100 = **{roll}** / {con_value} 【{result_text}】\n"
                            f"结果: **{status}**"
                        ),
                    },
                },
            ],
        }
        return json.dumps([card])
