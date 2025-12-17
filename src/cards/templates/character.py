"""角色卡相关卡片模板

包含角色创建、审核、成长等卡片模板。
"""

from typing import List, Optional

from ..builder import CardBuilder
from ..components import CardComponents


class CharacterCardTemplates:
    """角色卡相关卡片模板"""

    @staticmethod
    def create_character() -> str:
        """
        构建创建角色卡的交互卡片
        
        Returns:
            卡片消息 JSON 字符串
        """
        builder = CardBuilder(theme="info")
        builder.header("📋 创建角色卡")
        builder.divider()
        builder.section(
            "点击下方按钮获取专属创建链接\n"
            "链接将通过**私信**发送给你，仅限本人使用"
        )
        builder.buttons(
            CardComponents.button(
                "✨ 获取创建链接",
                {"action": "create_character"},
                theme="primary"
            )
        )
        
        return builder.build()

    @staticmethod
    def grow_character(
        char_name: str,
        skills: List[str],
        initiator_id: str
    ) -> str:
        """
        构建角色成长的交互卡片
        
        Args:
            char_name: 角色名称
            skills: 可成长技能列表
            initiator_id: 发起者用户 ID
            
        Returns:
            卡片消息 JSON 字符串
        """
        skills_text = "、".join(skills)
        
        builder = CardBuilder(theme="success")
        builder.header(f"📈 {char_name} 技能成长")
        builder.divider()
        builder.section(
            f"可成长技能: **{skills_text}**\n\n"
            f"点击下方按钮获取成长链接\n"
            f"链接将通过**私信**发送给你"
        )
        builder.context(f"只有 (met){initiator_id}(met) 可以获取链接")
        builder.buttons(
            CardComponents.button(
                "🎯 获取成长链接",
                {
                    "action": "grow_character",
                    "char_name": char_name,
                    "skills": skills,
                    "initiator_id": initiator_id
                },
                theme="primary"
            )
        )
        
        return builder.build()

    @staticmethod
    def character_review(
        char_name: str,
        image_url: str,
        initiator_id: str,
        initiator_name: str,
        kp_id: str = None
    ) -> str:
        """
        构建角色卡审核卡片
        
        Args:
            char_name: 角色名称
            image_url: 角色卡图片 URL
            initiator_id: 提交者用户 ID
            initiator_name: 提交者名称
            kp_id: KP 用户 ID（可选）
            
        Returns:
            卡片消息 JSON 字符串
        """
        kp_hint = f"只有 (met){kp_id}(met) 可以审核" if kp_id else "只有 KP 可以审核"
        
        builder = CardBuilder(theme="info")
        builder.header(f"📋 角色卡审核: {char_name}")
        builder.divider()
        
        # 添加图片容器
        builder.module(CardComponents.container([CardComponents.image(image_url)]))
        
        builder.divider()
        builder.context(
            f"提交者: **{initiator_name}** (met){initiator_id}(met)\n"
            f"{kp_hint}，审核通过后玩家才能创建角色卡"
        )
        builder.buttons(
            CardComponents.button(
                "✅ 审核通过",
                {
                    "action": "approve_character",
                    "char_name": char_name,
                    "initiator_id": initiator_id,
                    "kp_id": kp_id
                },
                theme="success"
            ),
            CardComponents.button(
                "❌ 审核拒绝",
                {
                    "action": "reject_character",
                    "char_name": char_name,
                    "initiator_id": initiator_id,
                    "kp_id": kp_id
                },
                theme="danger"
            )
        )
        
        return builder.build()

    @staticmethod
    def review_result(
        char_name: str,
        approved: bool,
        reviewer_name: str,
        initiator_id: str
    ) -> str:
        """
        构建审核结果卡片
        
        Args:
            char_name: 角色名称
            approved: 是否通过
            reviewer_name: 审核者名称
            initiator_id: 提交者用户 ID
            
        Returns:
            卡片消息 JSON 字符串
        """
        if approved:
            theme = "success"
            title = f"✅ 角色卡 {char_name} 审核通过"
            content = (
                f"**{reviewer_name}** 已通过审核\n"
                f"(met){initiator_id}(met) 现在可以在网页上点击「创建角色卡」按钮完成创建"
            )
        else:
            theme = "danger"
            title = f"❌ 角色卡 {char_name} 审核未通过"
            content = (
                f"**{reviewer_name}** 拒绝了审核\n"
                f"(met){initiator_id}(met) 请修改后重新提交"
            )

        builder = CardBuilder(theme=theme)
        builder.header(title)
        builder.section(content)
        
        return builder.build()

    @staticmethod
    def character_info(
        char_name: str,
        user_name: str,
        attributes: dict,
        skills: dict = None,
        hp: int = None,
        max_hp: int = None,
        mp: int = None,
        max_mp: int = None,
        san: int = None,
        max_san: int = None,
        luck: int = None
    ) -> str:
        """
        构建角色信息展示卡片
        
        Args:
            char_name: 角色名称
            user_name: 用户名
            attributes: 属性字典
            skills: 技能字典
            hp: 当前 HP
            max_hp: 最大 HP
            mp: 当前 MP
            max_mp: 最大 MP
            san: 当前 SAN
            max_san: 最大 SAN
            luck: 幸运值
            
        Returns:
            卡片消息 JSON 字符串
        """
        builder = CardBuilder(theme="info")
        builder.header(f"📋 {char_name}")
        builder.divider()
        
        # 基础属性
        attr_lines = []
        for attr, value in attributes.items():
            attr_lines.append(f"**{attr}**: {value}")
        builder.section(" | ".join(attr_lines))
        
        # 状态值
        if hp is not None and max_hp is not None:
            status_lines = []
            status_lines.append(f"HP: **{hp}**/{max_hp}")
            if mp is not None and max_mp is not None:
                status_lines.append(f"MP: **{mp}**/{max_mp}")
            if san is not None and max_san is not None:
                status_lines.append(f"SAN: **{san}**/{max_san}")
            if luck is not None:
                status_lines.append(f"幸运: **{luck}**")
            builder.section(" | ".join(status_lines))
        
        # 技能
        if skills:
            skill_lines = []
            for skill, value in skills.items():
                skill_lines.append(f"{skill}: {value}")
            builder.divider()
            builder.section("\n".join(skill_lines))
        
        builder.context(f"玩家: {user_name}")
        
        return builder.build()

    @staticmethod
    def character_list(
        user_name: str,
        characters: List[dict],
        active_char: str = None
    ) -> str:
        """
        构建角色列表卡片
        
        Args:
            user_name: 用户名
            characters: 角色列表 [{"name": str, "hp": int, "max_hp": int, "san": int}, ...]
            active_char: 当前激活的角色名
            
        Returns:
            卡片消息 JSON 字符串
        """
        builder = CardBuilder(theme="info")
        builder.header(f"📋 {user_name} 的角色列表")
        builder.divider()
        
        if not characters:
            builder.section("暂无角色卡")
        else:
            lines = []
            for char in characters:
                name = char.get("name", "未知")
                hp = char.get("hp", 0)
                max_hp = char.get("max_hp", 0)
                san = char.get("san", 0)
                
                active_mark = " ⭐" if name == active_char else ""
                lines.append(f"**{name}**{active_mark} - HP: {hp}/{max_hp} | SAN: {san}")
            
            builder.section("\n".join(lines))
        
        if active_char:
            builder.context(f"当前激活: {active_char}")
        
        return builder.build()
