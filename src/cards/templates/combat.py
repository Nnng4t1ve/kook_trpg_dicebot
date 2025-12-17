"""战斗相关卡片模板

包含伤害、先攻等战斗相关卡片模板。
"""

from typing import List, Optional, Tuple

from ..builder import CardBuilder
from ..components import CardComponents


class CombatCardTemplates:
    """战斗相关卡片模板"""

    @staticmethod
    def damage_confirm(
        check_id: str,
        initiator_name: str,
        target_name: str,
        target_type: str,
        damage_expr: str,
        target_id: str = None
    ) -> str:
        """
        构建伤害确认卡片
        
        Args:
            check_id: 检定 ID
            initiator_name: 攻击者名称
            target_name: 目标名称
            target_type: 目标类型 ("npc" 或 "player")
            damage_expr: 伤害表达式
            target_id: 目标用户 ID（玩家时需要）
            
        Returns:
            卡片消息 JSON 字符串
        """
        if target_type == "npc":
            target_display = f"**{target_name}** (NPC)"
        else:
            target_display = f"**{target_name}** (met){target_id}(met)"

        builder = CardBuilder(theme="danger")
        builder.header("⚔️ 伤害确认")
        builder.divider()
        builder.section(
            f"**{initiator_name}** 对 {target_display} 造成伤害\n"
            f"伤害: **{damage_expr}**"
        )
        builder.context(f"只有 **{initiator_name}** 可以确认伤害")
        builder.buttons(
            CardComponents.button(
                "🎲 确认伤害",
                {"action": "confirm_damage", "check_id": check_id},
                theme="danger"
            )
        )
        
        return builder.build()

    @staticmethod
    def damage_result(
        target_name: str,
        target_type: str,
        damage_expr: str,
        damage: int,
        old_hp: int = None,
        new_hp: int = None,
        max_hp: int = None,
        hp_bar: str = None,
        status_level: str = None,
        status_desc: str = None
    ) -> str:
        """
        构建伤害结果卡片
        
        Args:
            target_name: 目标名称
            target_type: 目标类型 ("npc" 或 "player")
            damage_expr: 伤害表达式
            damage: 伤害值
            old_hp: 原 HP（玩家）
            new_hp: 新 HP
            max_hp: 最大 HP（玩家）
            hp_bar: HP 条显示
            status_level: 状态等级（玩家）
            status_desc: 状态描述（NPC）
            
        Returns:
            卡片消息 JSON 字符串
        """
        if target_type == "npc":
            content = (
                f"⚔️ **{target_name}** 受到攻击\n"
                f"伤害: {damage_expr} = **{damage}**\n"
                f"[{hp_bar}]\n"
                f"状态: _{status_desc}_"
            )
            if new_hp == 0:
                content += f"\n\n💀 **{target_name}** {status_desc}"
        else:
            content = (
                f"⚔️ **{target_name}** 受到伤害\n"
                f"伤害: {damage_expr} = **{damage}**\n"
                f"HP: {old_hp} → **{new_hp}** / {max_hp}\n"
                f"[{hp_bar}] {status_level}"
            )
            if new_hp == 0:
                content += "\n\n💀 **角色倒下了！**"

        builder = CardBuilder(theme="danger")
        builder.section(content)
        
        return builder.build()

    @staticmethod
    def initiative_order(participants: List[Tuple[str, int, str, Optional[str]]]) -> str:
        """
        构建先攻顺序卡片
        
        Args:
            participants: 参与者列表 [(name, dex, type, user_id), ...]
                         已按 DEX 排序
                         type: "player", "npc", "unknown"
            
        Returns:
            卡片消息 JSON 字符串
        """
        lines = []
        for i, (name, dex, p_type, user_id) in enumerate(participants, 1):
            if p_type == "npc":
                lines.append(f"**{i}.** {name} (NPC) - DEX: **{dex}**")
            elif p_type == "unknown":
                lines.append(f"**{i}.** {name} - DEX: **?**")
            else:
                if user_id:
                    lines.append(f"**{i}.** {name} (met){user_id}(met) - DEX: **{dex}**")
                else:
                    lines.append(f"**{i}.** {name} - DEX: **{dex}**")
        
        content = "\n".join(lines)
        
        builder = CardBuilder(theme="info")
        builder.header("⚡ 先攻顺序表")
        builder.divider()
        builder.section(content)
        builder.context("按 DEX 从高到低排序")
        
        return builder.build()

    @staticmethod
    def attack_roll(
        attacker_name: str,
        target_name: str,
        skill_name: str,
        roll: int,
        target_value: int,
        result_text: str,
        is_success: bool,
        damage_expr: str = None
    ) -> str:
        """
        构建攻击骰点结果卡片
        
        Args:
            attacker_name: 攻击者名称
            target_name: 目标名称
            skill_name: 技能名称
            roll: 骰点结果
            target_value: 目标值
            result_text: 结果文本
            is_success: 是否成功
            damage_expr: 伤害表达式（成功时显示）
            
        Returns:
            卡片消息 JSON 字符串
        """
        theme = "success" if is_success else "danger"
        emoji = "⚔️" if is_success else "🛡️"
        
        content = (
            f"{emoji} **{attacker_name}** 对 **{target_name}** 的攻击\n"
            f"**{skill_name}**: D100 = **{roll}** / {target_value} 【{result_text}】"
        )
        
        if is_success and damage_expr:
            content += f"\n伤害: **{damage_expr}**"
        
        builder = CardBuilder(theme=theme)
        builder.section(content)
        
        return builder.build()

    @staticmethod
    def dodge_roll(
        defender_name: str,
        attacker_name: str,
        roll: int,
        target_value: int,
        result_text: str,
        is_success: bool
    ) -> str:
        """
        构建闪避骰点结果卡片
        
        Args:
            defender_name: 防御者名称
            attacker_name: 攻击者名称
            roll: 骰点结果
            target_value: 目标值
            result_text: 结果文本
            is_success: 是否成功
            
        Returns:
            卡片消息 JSON 字符串
        """
        theme = "success" if is_success else "danger"
        emoji = "🛡️" if is_success else "💥"
        
        if is_success:
            result_desc = "成功闪避！"
        else:
            result_desc = "闪避失败！"
        
        content = (
            f"{emoji} **{defender_name}** 尝试闪避 **{attacker_name}** 的攻击\n"
            f"**闪避**: D100 = **{roll}** / {target_value} 【{result_text}】\n"
            f"{result_desc}"
        )
        
        builder = CardBuilder(theme=theme)
        builder.section(content)
        
        return builder.build()

    @staticmethod
    def combat_round(
        round_num: int,
        current_actor: str,
        actor_type: str,
        actor_id: str = None,
        remaining_actors: List[str] = None
    ) -> str:
        """
        构建战斗回合提示卡片
        
        Args:
            round_num: 回合数
            current_actor: 当前行动者名称
            actor_type: 行动者类型 ("player" 或 "npc")
            actor_id: 行动者用户 ID（玩家时需要）
            remaining_actors: 剩余行动者列表
            
        Returns:
            卡片消息 JSON 字符串
        """
        if actor_type == "npc":
            actor_display = f"**{current_actor}** (NPC)"
        else:
            actor_display = f"**{current_actor}** (met){actor_id}(met)"
        
        content = f"当前行动: {actor_display}"
        
        if remaining_actors:
            content += f"\n\n等待行动: {', '.join(remaining_actors)}"
        
        builder = CardBuilder(theme="warning")
        builder.header(f"⚔️ 第 {round_num} 回合")
        builder.divider()
        builder.section(content)
        
        return builder.build()

    @staticmethod
    def hp_status(
        name: str,
        hp: int,
        max_hp: int,
        hp_bar: str = None,
        is_npc: bool = False
    ) -> str:
        """
        构建 HP 状态卡片
        
        Args:
            name: 角色名称
            hp: 当前 HP
            max_hp: 最大 HP
            hp_bar: HP 条显示
            is_npc: 是否为 NPC
            
        Returns:
            卡片消息 JSON 字符串
        """
        npc_tag = " (NPC)" if is_npc else ""
        
        # 根据 HP 百分比选择主题
        hp_percent = hp / max_hp if max_hp > 0 else 0
        if hp_percent > 0.5:
            theme = "success"
        elif hp_percent > 0.25:
            theme = "warning"
        else:
            theme = "danger"
        
        if hp_bar:
            content = f"**{name}**{npc_tag}\nHP: **{hp}** / {max_hp}\n[{hp_bar}]"
        else:
            content = f"**{name}**{npc_tag}\nHP: **{hp}** / {max_hp}"
        
        builder = CardBuilder(theme=theme)
        builder.section(content)
        
        return builder.build()

    @staticmethod
    def heal_result(
        target_name: str,
        heal_expr: str,
        heal_amount: int,
        old_hp: int,
        new_hp: int,
        max_hp: int,
        is_npc: bool = False
    ) -> str:
        """
        构建治疗结果卡片
        
        Args:
            target_name: 目标名称
            heal_expr: 治疗表达式
            heal_amount: 治疗量
            old_hp: 原 HP
            new_hp: 新 HP
            max_hp: 最大 HP
            is_npc: 是否为 NPC
            
        Returns:
            卡片消息 JSON 字符串
        """
        npc_tag = " (NPC)" if is_npc else ""
        
        content = (
            f"💚 **{target_name}**{npc_tag} 恢复了生命值\n"
            f"治疗: {heal_expr} = **{heal_amount}**\n"
            f"HP: {old_hp} → **{new_hp}** / {max_hp}"
        )
        
        builder = CardBuilder(theme="success")
        builder.section(content)
        
        return builder.build()
