"""角色卡命令"""
from .base import BaseCommand, CommandResult
from .registry import command
from ..card_builder import CardBuilder
from ...character import CharacterImporter


@command("pc")
class CharacterCommand(BaseCommand):
    """角色卡命令"""
    
    description = "角色卡管理"
    usage = ".pc <子命令> (new, create, grow, list, switch, show, del)"
    
    async def execute(self, args: str) -> CommandResult:
        """角色卡命令: .pc <子命令>"""
        parts = args.split(maxsplit=1)
        sub_cmd = parts[0].lower() if parts else "show"
        sub_args = parts[1] if len(parts) > 1 else ""
        
        if sub_cmd == "new":
            return await self._pc_new(sub_args)
        elif sub_cmd == "create":
            return await self._pc_create_link()
        elif sub_cmd == "grow":
            return await self._pc_grow(sub_args)
        elif sub_cmd == "list":
            return await self._pc_list()
        elif sub_cmd == "switch":
            return await self._pc_switch(sub_args)
        elif sub_cmd == "show":
            return await self._pc_show()
        elif sub_cmd == "del":
            return await self._pc_delete(sub_args)
        else:
            return CommandResult.text("未知子命令。可用: new, create, grow, list, switch, show, del")
    
    async def _pc_new(self, json_str: str) -> CommandResult:
        """导入角色卡"""
        if not json_str:
            return CommandResult.text("请提供角色卡 JSON 数据，或使用 `.pc create` 在线创建")
        
        char, error = CharacterImporter.from_json(json_str, self.ctx.user_id)
        if error:
            return CommandResult.text(f"导入失败: {error}")
        
        await self.ctx.char_manager.add(char)
        return CommandResult.text(f"角色卡 **{char.name}** 导入成功！")
    
    async def _pc_create_link(self) -> CommandResult:
        """发送创建角色卡的交互卡片"""
        card = CardBuilder.build_create_character_card()
        return CommandResult.card(card)
    
    async def _pc_grow(self, args: str) -> CommandResult:
        """角色卡成长: .pc grow <角色名> <技能1> <技能2> ..."""
        if not self.ctx.web_app:
            return CommandResult.text("Web 服务未启用")
        
        parts = args.split()
        if len(parts) < 2:
            return CommandResult.text(
                "格式: .pc grow <角色名> <技能1> <技能2> ...\n"
                "示例: .pc grow 张三 侦查 聆听 图书馆"
            )
        
        char_name = parts[0]
        skill_names = parts[1:]
        
        # 检查角色是否存在
        char = await self.ctx.char_manager.get(self.ctx.user_id, char_name)
        if not char:
            return CommandResult.text(f"未找到角色: {char_name}")
        
        # 验证技能是否存在于角色卡中
        valid_skills = []
        invalid_skills = []
        for skill in skill_names:
            if skill in char.skills:
                valid_skills.append(skill)
            else:
                # 尝试别名解析
                from ...dice.skill_alias import skill_resolver
                resolved = skill_resolver.resolve(skill)
                if resolved in char.skills:
                    valid_skills.append(resolved)
                else:
                    invalid_skills.append(skill)
        
        if not valid_skills:
            return CommandResult.text(f"角色 {char_name} 没有这些技能: {', '.join(skill_names)}")
        
        # 返回卡片消息
        card = CardBuilder.build_grow_character_card(char_name, valid_skills, self.ctx.user_id)
        return CommandResult.card(card)
    
    async def _pc_list(self) -> CommandResult:
        """列出角色卡"""
        chars = await self.ctx.char_manager.list_all(self.ctx.user_id)
        if not chars:
            return CommandResult.text("暂无角色卡")
        
        active = await self.ctx.char_manager.get_active(self.ctx.user_id)
        active_name = active.name if active else None
        
        lines = ["**角色卡列表**"]
        for char in chars:
            marker = "→ " if char.name == active_name else "  "
            lines.append(f"{marker}{char.name}")
        return CommandResult.text("\n".join(lines))
    
    async def _pc_switch(self, name: str) -> CommandResult:
        """切换角色卡"""
        name = name.strip()
        if not name:
            return CommandResult.text("请指定角色名称")
        
        success = await self.ctx.char_manager.set_active(self.ctx.user_id, name)
        if success:
            return CommandResult.text(f"已切换到角色: **{name}**")
        return CommandResult.text(f"未找到角色: {name}")
    
    async def _pc_show(self) -> CommandResult:
        """显示当前角色"""
        char = await self.ctx.char_manager.get_active(self.ctx.user_id)
        if not char:
            return CommandResult.text("当前没有选中的角色卡")
        
        max_san = self._calc_max_san(char)
        lines = [f"**{char.name}**"]
        lines.append(
            f"HP: {char.hp}/{char.max_hp} | MP: {char.mp}/{char.max_mp} | SAN: {char.san}/{max_san}"
        )
        
        if char.attributes:
            attrs = " | ".join(f"{k}:{v}" for k, v in char.attributes.items())
            lines.append(f"属性: {attrs}")
        
        if char.skills:
            skills = " | ".join(f"{k}:{v}" for k, v in list(char.skills.items())[:10])
            lines.append(f"技能: {skills}")
        
        return CommandResult.text("\n".join(lines))
    
    async def _pc_delete(self, name: str) -> CommandResult:
        """删除角色卡"""
        name = name.strip()
        if not name:
            return CommandResult.text("请指定角色名称")
        
        success = await self.ctx.char_manager.delete(self.ctx.user_id, name)
        if success:
            return CommandResult.text(f"已删除角色: **{name}**")
        return CommandResult.text(f"未找到角色: {name}")
    
    def _calc_max_san(self, char) -> int:
        """计算 SAN 上限: 99 - 克苏鲁神话技能"""
        cthulhu_mythos = char.skills.get("克苏鲁神话", 0)
        if cthulhu_mythos == 0:
            cthulhu_mythos = char.skills.get("CM", 0)
        return 99 - cthulhu_mythos
