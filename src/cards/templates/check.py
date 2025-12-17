"""检定相关卡片模板

包含技能检定、SAN Check、对抗检定等卡片模板。
"""

from typing import List, Optional, Tuple

from ..builder import CardBuilder
from ..components import CardComponents


class CheckCardTemplates:
    """检定相关卡片模板"""

    @staticmethod
    def skill_check(
        check_id: str,
        skill_name: str,
        description: str = "",
        kp_name: str = ""
    ) -> str:
        """
        构建技能检定卡片
        
        Args:
            check_id: 检定 ID
            skill_name: 技能名称
            description: 检定描述
            kp_name: KP 名称
            
        Returns:
            卡片消息 JSON 字符串
        """
        builder = CardBuilder(theme="warning")
        builder.header(f"🎲 {skill_name} 检定")
        builder.divider()
        
        if kp_name:
            builder.context(f"发起者: {kp_name}")
        
        builder.section(description or f"KP 发起了 **{skill_name}** 检定，点击下方按钮进行骰点")
        builder.buttons(
            CardComponents.button(
                f"🎯 进行 {skill_name} 检定",
                {"action": "check", "check_id": check_id, "skill": skill_name},
                theme="primary"
            )
        )
        
        return builder.build()

    @staticmethod
    def skill_check_result(
        user_name: str,
        skill_name: str,
        roll: int,
        target: int,
        result_text: str,
        is_success: bool
    ) -> str:
        """
        构建检定结果卡片
        
        Args:
            user_name: 用户名
            skill_name: 技能名称
            roll: 骰点结果
            target: 目标值
            result_text: 结果文本（如"成功"、"大成功"等）
            is_success: 是否成功
            
        Returns:
            卡片消息 JSON 字符串
        """
        theme = "success" if is_success else "danger"
        emoji = "✅" if is_success else "❌"
        
        builder = CardBuilder(theme=theme)
        builder.section(
            f"{emoji} **{user_name}** 的 **{skill_name}** 检定\n"
            f"D100 = **{roll}** / {target}  【{result_text}】"
        )
        
        return builder.build()

    @staticmethod
    def multi_skill_check(
        check_id: str,
        skills: List[str],
        description: str = "",
        kp_name: str = ""
    ) -> str:
        """
        构建多技能选择检定卡片
        
        Args:
            check_id: 检定 ID
            skills: 可选技能列表
            description: 检定描述
            kp_name: KP 名称
            
        Returns:
            卡片消息 JSON 字符串
        """
        builder = CardBuilder(theme="warning")
        builder.header("🎲 技能检定")
        builder.divider()
        builder.section(description or "选择一个技能进行检定")
        
        buttons = [
            CardComponents.button(
                skill,
                {"action": "check", "check_id": check_id, "skill": skill},
                theme="primary"
            )
            for skill in skills[:4]
        ]
        builder.buttons(*buttons)
        
        return builder.build()

    @staticmethod
    def san_check(
        check_id: str,
        success_expr: str,
        fail_expr: str,
        description: str = "",
        kp_name: str = ""
    ) -> str:
        """
        构建 SAN Check 卡片
        
        Args:
            check_id: 检定 ID
            success_expr: 成功损失表达式
            fail_expr: 失败损失表达式
            description: 检定描述
            kp_name: KP 名称
            
        Returns:
            卡片消息 JSON 字符串
        """
        builder = CardBuilder(theme="danger")
        builder.header("🧠 SAN Check")
        builder.divider()
        
        if kp_name:
            builder.context(f"发起者: {kp_name}")
        
        builder.section(
            f"成功损失: **{success_expr}** | 失败损失: **{fail_expr}**\n"
            f"{description or '点击下方按钮进行 SAN Check'}"
        )
        builder.buttons(
            CardComponents.button(
                "🎲 进行 SAN Check",
                {
                    "action": "san_check",
                    "check_id": check_id,
                    "success_expr": success_expr,
                    "fail_expr": fail_expr
                },
                theme="danger"
            )
        )
        
        return builder.build()

    @staticmethod
    def san_check_result(
        user_name: str,
        char_name: str,
        roll: int,
        san: int,
        is_success: bool,
        loss_expr: str,
        loss: int,
        new_san: int,
        madness_info: List[str] = None
    ) -> str:
        """
        构建 SAN Check 结果卡片
        
        Args:
            user_name: 用户名
            char_name: 角色名
            roll: 骰点结果
            san: 当前 SAN 值
            is_success: 是否成功
            loss_expr: 损失表达式
            loss: 损失值
            new_san: 新 SAN 值
            madness_info: 疯狂信息列表
            
        Returns:
            卡片消息 JSON 字符串
        """
        theme = "warning" if is_success else "danger"
        result_text = "成功" if is_success else "失败"
        
        builder = CardBuilder(theme=theme)
        builder.section(
            f"**{char_name}** 的 SAN Check\n"
            f"D100 = **{roll}** / {san}  【{result_text}】\n"
            f"损失: {loss_expr} = **{loss}**\n"
            f"SAN: {san} → **{new_san}**"
        )
        
        if madness_info:
            builder.divider()
            builder.section("\n".join(madness_info))
        
        return builder.build()

    @staticmethod
    def opposed_check(
        check_id: str,
        initiator_name: str,
        target_id: str,
        initiator_skill: str,
        target_skill: str,
        initiator_bp: Tuple[int, int] = (0, 0),
        target_bp: Tuple[int, int] = (0, 0)
    ) -> str:
        """
        构建对抗检定卡片
        
        Args:
            check_id: 检定 ID
            initiator_name: 发起者名称
            target_id: 目标用户 ID
            initiator_skill: 发起者技能
            target_skill: 目标技能
            initiator_bp: 发起者奖惩骰 (bonus, penalty)
            target_bp: 目标奖惩骰 (bonus, penalty)
            
        Returns:
            卡片消息 JSON 字符串
        """
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

        builder = CardBuilder(theme="warning")
        builder.header(title)
        builder.divider()
        builder.section(f"{desc}\n\n双方点击按钮进行检定")
        builder.buttons(
            CardComponents.button(
                "🎲 进行检定",
                {"action": "opposed_check", "check_id": check_id},
                theme="primary"
            )
        )
        
        return builder.build()

    @staticmethod
    def opposed_check_result(
        initiator_name: str,
        target_name: str,
        skill_name: str,
        initiator_roll: int,
        initiator_target: int,
        initiator_level: str,
        target_roll: int,
        target_target: int,
        target_level: str,
        winner: str  # "initiator", "target", "tie"
    ) -> str:
        """
        构建对抗检定结果卡片
        
        Args:
            initiator_name: 发起者名称
            target_name: 目标名称
            skill_name: 技能名称
            initiator_roll: 发起者骰点
            initiator_target: 发起者目标值
            initiator_level: 发起者成功等级
            target_roll: 目标骰点
            target_target: 目标目标值
            target_level: 目标成功等级
            winner: 胜者 ("initiator", "target", "tie")
            
        Returns:
            卡片消息 JSON 字符串
        """
        if winner == "initiator":
            theme = "success"
            result_text = f"🏆 **{initiator_name}** 胜出！"
        elif winner == "target":
            theme = "danger"
            result_text = f"🏆 **{target_name}** 胜出！"
        else:
            theme = "secondary"
            result_text = "⚖️ **平局！**"

        builder = CardBuilder(theme=theme)
        builder.header(f"⚔️ {skill_name} 对抗结果")
        builder.divider()
        builder.section(
            f"**{initiator_name}**: D100={initiator_roll}/{initiator_target} 【{initiator_level}】\n"
            f"**{target_name}**: D100={target_roll}/{target_target} 【{target_level}】"
        )
        builder.section(result_text)
        
        return builder.build()

    @staticmethod
    def npc_opposed_check(
        check_id: str,
        npc_name: str,
        target_id: str,
        npc_skill: str,
        target_skill: str,
        npc_roll: int,
        npc_target: int,
        npc_level: str,
        npc_bp: Tuple[int, int] = (0, 0),
        target_bp: Tuple[int, int] = (0, 0)
    ) -> str:
        """
        构建 NPC 对抗检定卡片（NPC 已完成检定）
        
        Args:
            check_id: 检定 ID
            npc_name: NPC 名称
            target_id: 目标用户 ID
            npc_skill: NPC 技能
            target_skill: 目标技能
            npc_roll: NPC 骰点结果
            npc_target: NPC 目标值
            npc_level: NPC 成功等级
            npc_bp: NPC 奖惩骰
            target_bp: 目标奖惩骰
            
        Returns:
            卡片消息 JSON 字符串
        """
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

        builder = CardBuilder(theme="warning")
        builder.header(title)
        builder.divider()
        builder.section(desc)
        builder.buttons(
            CardComponents.button(
                "🎲 进行检定",
                {"action": "opposed_check", "check_id": check_id},
                theme="primary"
            )
        )
        
        return builder.build()

    @staticmethod
    def player_vs_npc_opposed(
        check_id: str,
        player_name: str,
        player_id: str,
        npc_name: str,
        player_skill: str,
        npc_skill: str,
        npc_roll: int,
        npc_target: int,
        npc_level: str,
        player_bp: Tuple[int, int] = (0, 0),
        npc_bp: Tuple[int, int] = (0, 0)
    ) -> str:
        """
        构建玩家 vs NPC 对抗检定卡片（NPC 已完成检定，等待玩家）
        
        Args:
            check_id: 检定 ID
            player_name: 玩家名称
            player_id: 玩家用户 ID
            npc_name: NPC 名称
            player_skill: 玩家技能
            npc_skill: NPC 技能
            npc_roll: NPC 骰点结果
            npc_target: NPC 目标值
            npc_level: NPC 成功等级
            player_bp: 玩家奖惩骰
            npc_bp: NPC 奖惩骰
            
        Returns:
            卡片消息 JSON 字符串
        """
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

        builder = CardBuilder(theme="warning")
        builder.header(title)
        builder.divider()
        builder.section(desc)
        builder.buttons(
            CardComponents.button(
                "🎲 进行检定",
                {"action": "opposed_check", "check_id": check_id},
                theme="primary"
            )
        )
        
        return builder.build()

    @staticmethod
    def con_check(
        check_id: str,
        target_name: str,
        target_id: str,
        damage: int,
        max_hp: int
    ) -> str:
        """
        构建体质检定卡片（重伤昏迷检定）
        
        Args:
            check_id: 检定 ID
            target_name: 目标名称
            target_id: 目标用户 ID
            damage: 受到的伤害
            max_hp: HP 上限
            
        Returns:
            卡片消息 JSON 字符串
        """
        builder = CardBuilder(theme="warning")
        builder.header("💫 重伤昏迷检定")
        builder.divider()
        builder.section(
            f"**{target_name}** 受到了 **{damage}** 点伤害 (≥ HP上限的一半: {max_hp // 2})\n"
            f"需要进行 **体质(CON)** 检定\n"
            f"成功: 保持清醒 | 失败: 陷入昏迷"
        )
        builder.buttons(
            CardComponents.button(
                "🎲 进行体质检定",
                {"action": "con_check", "check_id": check_id},
                theme="warning"
            )
        )
        builder.context(f"(met){target_id}(met) 点击按钮进行检定")
        
        return builder.build()

    @staticmethod
    def con_check_result(
        target_name: str,
        roll: int,
        con_value: int,
        is_success: bool,
        is_npc: bool = False
    ) -> str:
        """
        构建体质检定结果卡片
        
        Args:
            target_name: 目标名称
            roll: 骰点结果
            con_value: 体质值
            is_success: 是否成功
            is_npc: 是否为 NPC
            
        Returns:
            卡片消息 JSON 字符串
        """
        theme = "success" if is_success else "danger"
        result_text = "成功" if is_success else "失败"
        status = "保持清醒" if is_success else "陷入昏迷"
        emoji = "✅" if is_success else "💫"
        npc_tag = " (NPC)" if is_npc else ""

        builder = CardBuilder(theme=theme)
        builder.section(
            f"{emoji} **{target_name}**{npc_tag} 的体质检定\n"
            f"D100 = **{roll}** / {con_value} 【{result_text}】\n"
            f"结果: **{status}**"
        )
        
        return builder.build()
