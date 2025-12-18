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
    def build_create_character_card(
        skill_limit: int = None,
        occ_limit: int = None,
        non_occ_limit: int = None
    ) -> str:
        """构建创建角色卡的交互卡片"""
        # 构建技能上限说明
        if occ_limit is not None and non_occ_limit is not None:
            limit_text = f"\n⚠️ 技能上限: 本职 **{occ_limit}** / 非本职 **{non_occ_limit}**"
        elif skill_limit is not None:
            limit_text = f"\n⚠️ 技能上限: **{skill_limit}**"
        else:
            limit_text = ""
        
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
                        "content": f"点击下方按钮获取专属创建链接\n链接将通过**私信**发送给你，仅限本人使用{limit_text}"
                    }
                },
                {
                    "type": "action-group",
                    "elements": [
                        {
                            "type": "button",
                            "theme": "primary",
                            "value": json.dumps({
                                "action": "create_character",
                                "skill_limit": skill_limit,
                                "occ_limit": occ_limit,
                                "non_occ_limit": non_occ_limit
                            }),
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

    @staticmethod
    def build_character_review_card(
        char_name: str,
        image_url: str,
        initiator_id: str,
        initiator_name: str,
        kp_id: str = None,
    ) -> str:
        """构建角色卡审核卡片"""
        kp_hint = f"只有 (met){kp_id}(met) 可以审核" if kp_id else "只有 KP 可以审核"
        card = {
            "type": "card",
            "theme": "info",
            "size": "lg",
            "modules": [
                {
                    "type": "header",
                    "text": {"type": "plain-text", "content": f"📋 角色卡审核: {char_name}"},
                },
                {"type": "divider"},
                {
                    "type": "container",
                    "elements": [{"type": "image", "src": image_url}],
                },
                {"type": "divider"},
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "kmarkdown",
                            "content": f"提交者: **{initiator_name}** (met){initiator_id}(met)\n{kp_hint}，审核通过后玩家才能创建角色卡",
                        }
                    ],
                },
                {
                    "type": "action-group",
                    "elements": [
                        {
                            "type": "button",
                            "theme": "success",
                            "value": json.dumps(
                                {
                                    "action": "approve_character",
                                    "char_name": char_name,
                                    "initiator_id": initiator_id,
                                    "kp_id": kp_id,
                                }
                            ),
                            "click": "return-val",
                            "text": {"type": "plain-text", "content": "✅ 审核通过"},
                        },
                        {
                            "type": "button",
                            "theme": "danger",
                            "value": json.dumps(
                                {
                                    "action": "reject_character",
                                    "char_name": char_name,
                                    "initiator_id": initiator_id,
                                    "kp_id": kp_id,
                                }
                            ),
                            "click": "return-val",
                            "text": {"type": "plain-text", "content": "❌ 审核拒绝"},
                        },
                    ],
                },
            ],
        }
        return json.dumps([card])

    @staticmethod
    def build_review_result_card(
        char_name: str,
        approved: bool,
        reviewer_name: str,
        initiator_id: str,
    ) -> str:
        """构建审核结果卡片"""
        if approved:
            theme = "success"
            title = f"✅ 角色卡 {char_name} 审核通过"
            content = f"**{reviewer_name}** 已通过审核\n(met){initiator_id}(met) 现在可以在网页上点击「创建角色卡」按钮完成创建"
        else:
            theme = "danger"
            title = f"❌ 角色卡 {char_name} 审核未通过"
            content = f"**{reviewer_name}** 拒绝了审核\n(met){initiator_id}(met) 请修改后重新提交"

        card = {
            "type": "card",
            "theme": theme,
            "size": "lg",
            "modules": [
                {
                    "type": "header",
                    "text": {"type": "plain-text", "content": title},
                },
                {
                    "type": "section",
                    "text": {"type": "kmarkdown", "content": content},
                },
            ],
        }
        return json.dumps([card])

    @staticmethod
    def build_create_link_card(
        url: str,
        skill_limit: int = None,
        occ_limit: int = None,
        non_occ_limit: int = None
    ) -> str:
        """构建创建角色卡链接卡片（私聊发送）"""
        # 构建技能上限说明
        if occ_limit is not None and non_occ_limit is not None:
            limit_text = f"\n⚠️ 技能上限: 本职 **{occ_limit}** / 非本职 **{non_occ_limit}**"
        elif skill_limit is not None:
            limit_text = f"\n⚠️ 技能上限: **{skill_limit}**"
        else:
            limit_text = ""
        
        card = {
            "type": "card",
            "theme": "info",
            "size": "lg",
            "modules": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain-text",
                        "content": "🎲 角色卡创建链接"
                    }
                },
                {
                    "type": "divider"
                },
                {
                    "type": "section",
                    "text": {
                        "type": "kmarkdown",
                        "content": f"点击下方按钮打开创建页面\n⏰ 链接有效期 10 分钟，仅限本人使用{limit_text}"
                    }
                },
                {
                    "type": "action-group",
                    "elements": [
                        {
                            "type": "button",
                            "theme": "primary",
                            "click": "link",
                            "value": url,
                            "text": {
                                "type": "plain-text",
                                "content": "✨ 打开创建页面"
                            }
                        }
                    ]
                }
            ]
        }
        return json.dumps([card])

    @staticmethod
    def build_grow_link_card(char_name: str, skills: list, url: str) -> str:
        """构建角色成长链接卡片（私聊发送）"""
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
                        "content": f"可成长技能: **{skills_text}**\n⏰ 链接有效期 10 分钟"
                    }
                },
                {
                    "type": "action-group",
                    "elements": [
                        {
                            "type": "button",
                            "theme": "primary",
                            "click": "link",
                            "value": url,
                            "text": {
                                "type": "plain-text",
                                "content": "🎯 打开成长页面"
                            }
                        }
                    ]
                }
            ]
        }
        return json.dumps([card])

    # 技能初始值映射表
    SKILL_INITIAL_VALUES = {
        "侦查": 25, "聆听": 20, "图书馆使用": 20, "心理学": 10, "急救": 30,
        "说服": 10, "话术": 5, "取悦": 15, "恐吓": 15, "信用评级": 0,
        "会计": 5, "人类学": 1, "考古学": 1, "历史": 5, "法律": 5,
        "博物学": 10, "神秘学": 5, "克苏鲁神话": 0,
        "估价": 5, "追踪": 10, "导航": 10, "读唇": 1,
        "攀爬": 20, "跳跃": 20, "游泳": 20, "投掷": 20, "骑术": 5, "潜水": 1, "潜行": 20,
        "汽车驾驶": 20, "电气维修": 10, "机械维修": 10, "操作重型机械": 1,
        "锁匠": 1, "乔装": 5, "计算机使用Ω": 5, "电子学Ω": 1,
        "医学": 1, "精神分析": 1, "催眠": 1,
        "斗殴": 25, "格斗:斗殴": 25, "格斗：斗殴": 25,
        "斧": 15, "格斗:斧": 15, "格斗：斧": 15,
        "剑": 20, "格斗:剑": 20, "格斗：剑": 20,
        "手枪": 20, "射击:手枪": 20, "射击：手枪": 20,
        "步枪/霰弹枪": 25, "射击:步枪/霰弹枪": 25, "射击：步枪/霰弹枪": 25,
        "冲锋枪": 15, "射击:冲锋枪": 15, "射击：冲锋枪": 15,
        "妙手": 10, "驯兽": 5, "炮术": 1, "爆破": 1,
    }

    @classmethod
    def _get_skill_initial(cls, skill_name: str) -> int:
        """获取技能初始值"""
        # 直接匹配
        if skill_name in cls.SKILL_INITIAL_VALUES:
            return cls.SKILL_INITIAL_VALUES[skill_name]
        # 统一冒号格式后匹配
        normalized = skill_name.replace("：", ":")
        if normalized in cls.SKILL_INITIAL_VALUES:
            return cls.SKILL_INITIAL_VALUES[normalized]
        # 默认返回 1（大多数冷门技能的初始值）
        return 1

    @staticmethod
    def build_character_show_card(char) -> str:
        """构建角色卡展示卡片"""
        # 构建属性文本
        attrs = char.attributes
        attr_text = (
            f"**力量**: {attrs.get('STR', 50)} **体质**: {attrs.get('CON', 50)} **体型**: {attrs.get('SIZ', 50)}\n"
            f"**敏捷**: {attrs.get('DEX', 50)} **外貌**: {attrs.get('APP', 50)} **智力**: {attrs.get('INT', 50)}\n"
            f"**意志**: {attrs.get('POW', 50)} **教育**: {attrs.get('EDU', 50)} **幸运**: {attrs.get('LUK', 50)}"
        )
        
        # 构建状态文本
        status_text = (
            f"**HP**: {char.hp}/{char.max_hp} **MP**: {char.mp}/{char.max_mp} **SAN**: {char.san}/{char.max_san}\n"
            f"**MOV**: {char.mov} **体格**: {char.build} **伤害加深**: {char.db}"
        )
        
        # 构建技能文本（只显示非初始值的技能）
        skills_text = ""
        if char.skills:
            skill_items = [
                f"{name}: {value}" 
                for name, value in char.skills.items() 
                if value > 0 and value != CardBuilder._get_skill_initial(name)
            ]
            if skill_items:
                skills_text = "\n**技能**: " + "、".join(skill_items[:15])
                if len(skill_items) > 15:
                    skills_text += f"... (共{len(skill_items)}个技能)"
        
        # 构建武器文本
        weapons_text = ""
        if char.weapons:
            weapon_items = [
                f"{w.get('name', '?')}({w.get('skill', '?')}、{w.get('damage', '?')})"
                for w in char.weapons if w.get('name') and w.get('name').strip()
            ]
            if weapon_items:
                weapons_text = "\n**武器**: " + " | ".join(weapon_items)
        
        # 构建物品文本
        items_text = ""
        if char.items:
            valid_items = [item for item in char.items if item and item.strip()]
            if valid_items:
                items_text = "\n**物品**: " + "、".join(valid_items)
        
        # 构建卡片模块
        modules = [
            {
                "type": "header",
                "text": {
                    "type": "plain-text",
                    "content": f"📋 {char.name}"
                }
            },
            {
                "type": "divider"
            }
        ]
        
        # 如果有图片，添加查看大图按钮
        if char.image_url and char.image_url.strip():
            modules.append({
                "type": "action-group",
                "elements": [
                    {
                        "type": "button",
                        "theme": "info",
                        "click": "link",
                        "value": char.image_url,
                        "text": {
                            "type": "plain-text",
                            "content": "🖼️ 查看角色卡图片"
                        }
                    }
                ]
            })
        
        # 添加属性和状态信息
        modules.extend([
            {
                "type": "section",
                "text": {
                    "type": "kmarkdown",
                    "content": f"**📊 属性**\n{attr_text}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "kmarkdown",
                    "content": f"**💖 状态**\n{status_text}"
                }
            }
        ])
        
        # 添加技能、武器、物品信息（如果有的话）
        detail_content = ""
        if skills_text:
            detail_content += skills_text
        if weapons_text:
            detail_content += weapons_text
        if items_text:
            detail_content += items_text
        
        # 只有当有详细信息时才添加详细信息模块
        if detail_content.strip():
            modules.append({
                "type": "section",
                "text": {
                    "type": "kmarkdown",
                    "content": f"**🎯 详细信息**{detail_content}"
                }
            })
        
        card = {
            "type": "card",
            "theme": "secondary",
            "size": "lg",
            "modules": modules
        }
        
        return json.dumps([card])

    @staticmethod
    def build_schedule_vote_card(
        vote_id: str,
        schedule_time,
        mentioned_users: list[str],
        description: str = "",
        initiator_name: str = ""
    ) -> str:
        """构建预定时间投票卡片"""
        from datetime import datetime
        
        # 格式化时间显示
        time_display = schedule_time.strftime("%Y年%m月%d日 %H:%M")
        
        # 构建提及用户列表（使用KOOK的@格式）
        users_display = "、".join([f"(met){user}(met)" for user in mentioned_users])
        
        # 构建描述内容
        content_lines = [
            f"📅 **预定时间**: {time_display}",
            f"👥 **参与者**: {users_display}",
        ]
        
        if description:
            content_lines.append(f"📝 **说明**: {description}")
        
        content_lines.extend([
            "",
            "请点击下方按钮表示你的选择：",
            "✅ **同意** - 可以参加",
            "❌ **拒绝** - 无法参加"
        ])
        
        card = {
            "type": "card",
            "theme": "info",
            "size": "lg",
            "modules": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain-text",
                        "content": "📅 预定时间投票"
                    }
                },
                {
                    "type": "divider"
                },
                {
                    "type": "section",
                    "text": {
                        "type": "kmarkdown",
                        "content": "\n".join(content_lines)
                    }
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "kmarkdown",
                            "content": f"发起者: **{initiator_name}** | 只有被提及的用户可以投票，每人只能投一次"
                        }
                    ]
                },
                {
                    "type": "action-group",
                    "elements": [
                        {
                            "type": "button",
                            "theme": "success",
                            "value": json.dumps({
                                "action": "schedule_vote",
                                "vote_id": vote_id,
                                "choice": "agree"
                            }),
                            "click": "return-val",
                            "text": {
                                "type": "plain-text",
                                "content": "✅ 同意"
                            }
                        },
                        {
                            "type": "button",
                            "theme": "danger",
                            "value": json.dumps({
                                "action": "schedule_vote",
                                "vote_id": vote_id,
                                "choice": "reject"
                            }),
                            "click": "return-val",
                            "text": {
                                "type": "plain-text",
                                "content": "❌ 拒绝"
                            }
                        }
                    ]
                }
            ]
        }
        
        return json.dumps([card])

    @staticmethod
    def build_schedule_vote_result_card(
        vote_id: str,
        schedule_time,
        description: str,
        initiator_name: str,
        votes: dict,
        mentioned_users: list[str]
    ) -> str:
        """构建预定时间投票结果卡片"""
        from datetime import datetime
        
        # 格式化时间显示
        time_display = schedule_time.strftime("%Y年%m月%d日 %H:%M")
        
        # 统计投票结果
        agree_users = []
        reject_users = []
        no_vote_users = []
        
        for user in mentioned_users:
            if user in votes:
                if votes[user]["choice"] == "agree":
                    agree_users.append(user)
                else:
                    reject_users.append(user)
            else:
                no_vote_users.append(user)
        
        # 构建结果显示
        content_lines = [
            f"📅 **预定时间**: {time_display}",
        ]
        
        if description:
            content_lines.append(f"📝 **说明**: {description}")
        
        content_lines.append("")
        content_lines.append("📊 **投票结果**:")
        
        if agree_users:
            content_lines.append(f"✅ **同意** ({len(agree_users)}人): {', '.join([f'(met){u}(met)' for u in agree_users])}")
        else:
            content_lines.append("✅ **同意** (0人): 暂无")
        
        if reject_users:
            content_lines.append(f"❌ **拒绝** ({len(reject_users)}人): {', '.join([f'(met){u}(met)' for u in reject_users])}")
        else:
            content_lines.append("❌ **拒绝** (0人): 暂无")
        
        if no_vote_users:
            content_lines.append(f"⏳ **未投票** ({len(no_vote_users)}人): {', '.join([f'(met){u}(met)' for u in no_vote_users])}")
        
        # 确定主题颜色
        if len(agree_users) == len(mentioned_users):
            theme = "success"
            status = "🎉 所有人都同意！"
        elif len(reject_users) == len(mentioned_users):
            theme = "danger"
            status = "😔 所有人都拒绝了"
        elif len(no_vote_users) == 0:
            theme = "warning"
            status = "📊 投票已完成"
        else:
            theme = "info"
            status = "⏳ 投票进行中..."
        
        content_lines.extend(["", status])
        
        card = {
            "type": "card",
            "theme": theme,
            "size": "lg",
            "modules": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain-text",
                        "content": "📅 预定时间投票结果"
                    }
                },
                {
                    "type": "divider"
                },
                {
                    "type": "section",
                    "text": {
                        "type": "kmarkdown",
                        "content": "\n".join(content_lines)
                    }
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "kmarkdown",
                            "content": f"发起者: **{initiator_name}**"
                        }
                    ]
                }
            ]
        }
        
        return json.dumps([card])


    @staticmethod
    def build_game_log_list_card(
        logs: list[dict],
        total: int,
        page: int,
        channel_id: str,
    ) -> str:
        """构建游戏日志列表卡片"""
        page_size = 10
        total_pages = (total + page_size - 1) // page_size

        # 构建日志列表
        lines = []
        for log in logs:
            status = "🔴 进行中" if not log.get("ended_at") else "✅ 已结束"
            started = log["started_at"].strftime("%m-%d %H:%M") if log.get("started_at") else "未知"
            lines.append(
                f"{status} `{log['log_name']}`\n"
                f"   📅 {started} | 📝 {log.get('entry_count', 0)}条"
            )

        content = "\n".join(lines) if lines else "暂无日志记录"

        modules = [
            {
                "type": "header",
                "text": {"type": "plain-text", "content": "📋 游戏日志列表"}
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {"type": "kmarkdown", "content": content}
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "kmarkdown",
                        "content": f"第 {page}/{total_pages} 页 · 共 {total} 条记录"
                    }
                ]
            },
        ]

        # 添加翻页按钮
        if total_pages > 1:
            buttons = []
            # 首页
            if page > 1:
                buttons.append({
                    "type": "button",
                    "theme": "secondary",
                    "value": json.dumps({"action": "log_page", "page": 1, "channel_id": channel_id}),
                    "click": "return-val",
                    "text": {"type": "plain-text", "content": "⏮️ 首页"}
                })
            # 上一页
            if page > 1:
                buttons.append({
                    "type": "button",
                    "theme": "secondary",
                    "value": json.dumps({"action": "log_page", "page": page - 1, "channel_id": channel_id}),
                    "click": "return-val",
                    "text": {"type": "plain-text", "content": "⬅️ 上一页"}
                })
            # 下一页
            if page < total_pages:
                buttons.append({
                    "type": "button",
                    "theme": "secondary",
                    "value": json.dumps({"action": "log_page", "page": page + 1, "channel_id": channel_id}),
                    "click": "return-val",
                    "text": {"type": "plain-text", "content": "下一页 ➡️"}
                })
            # 尾页
            if page < total_pages:
                buttons.append({
                    "type": "button",
                    "theme": "secondary",
                    "value": json.dumps({"action": "log_page", "page": total_pages, "channel_id": channel_id}),
                    "click": "return-val",
                    "text": {"type": "plain-text", "content": "尾页 ⏭️"}
                })

            if buttons:
                modules.append({"type": "action-group", "elements": buttons})

        card = {"type": "card", "theme": "info", "size": "lg", "modules": modules}
        return json.dumps([card])

    @staticmethod
    def build_game_log_export_card(
        log_name: str,
        export_url: str,
        total_entries: int,
    ) -> str:
        """构建日志导出卡片"""
        card = {
            "type": "card",
            "theme": "success",
            "size": "lg",
            "modules": [
                {
                    "type": "header",
                    "text": {"type": "plain-text", "content": "📤 日志导出"}
                },
                {"type": "divider"},
                {
                    "type": "section",
                    "text": {
                        "type": "kmarkdown",
                        "content": f"日志名称: `{log_name}`\n共 **{total_entries}** 条记录"
                    }
                },
                {
                    "type": "action-group",
                    "elements": [
                        {
                            "type": "button",
                            "theme": "primary",
                            "click": "link",
                            "value": export_url,
                            "text": {"type": "plain-text", "content": "📥 下载JSON文件"}
                        }
                    ]
                }
            ]
        }
        return json.dumps([card])

    @staticmethod
    def build_game_log_analysis_card(
        log_name: str,
        stats: dict,
    ) -> str:
        """构建日志分析卡片"""
        user_stats = stats.get("user_stats", {})
        total_rolls = stats.get("total_rolls", 0)

        # 构建用户统计表格
        lines = [f"📊 **总骰点次数**: {total_rolls}", ""]

        if user_stats:
            lines.append("**各玩家统计**:")
            for user_id, s in user_stats.items():
                lines.append(
                    f"(met){user_id}(met): "
                    f"🎲{s['total_rolls']} "
                    f"✅{s['success']} "
                    f"❌{s['failure']} "
                    f"🌟{s['critical']} "
                    f"💀{s['fumble']}"
                )

        # 添加最多统计
        lines.append("")
        lines.append("**🏆 排行榜**:")

        most_success = stats.get("most_success")
        most_failure = stats.get("most_failure")
        most_critical = stats.get("most_critical")
        most_fumble = stats.get("most_fumble")

        if most_critical and most_critical["critical"] > 0:
            lines.append(f"🌟 大成功最多: **{most_critical['user_name']}** ({most_critical['critical']}次)")
        if most_fumble and most_fumble["fumble"] > 0:
            lines.append(f"💀 大失败最多: **{most_fumble['user_name']}** ({most_fumble['fumble']}次)")
        if most_success and most_success["success"] > 0:
            lines.append(f"✅ 成功最多: **{most_success['user_name']}** ({most_success['success']}次)")
        if most_failure and most_failure["failure"] > 0:
            lines.append(f"❌ 失败最多: **{most_failure['user_name']}** ({most_failure['failure']}次)")

        card = {
            "type": "card",
            "theme": "info",
            "size": "lg",
            "modules": [
                {
                    "type": "header",
                    "text": {"type": "plain-text", "content": f"📈 日志分析: {log_name}"}
                },
                {"type": "divider"},
                {
                    "type": "section",
                    "text": {"type": "kmarkdown", "content": "\n".join(lines)}
                }
            ]
        }
        return json.dumps([card])
