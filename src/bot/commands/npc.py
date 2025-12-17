"""NPC 命令"""
import re
from loguru import logger
from .base import BaseCommand, CommandResult
from .registry import command
from ..card_builder import CardBuilder
from ...dice import DiceRoller
from ...dice.rules import get_rule, SuccessLevel
from ...character import NPC_TEMPLATES


@command("npc")
class NPCCommand(BaseCommand):
    """NPC 命令"""
    
    description = "NPC 管理"
    usage = ".npc create <名称> [模板], .npc <名称> ra <技能>, .npc list, .npc del <名称>"
    
    async def execute(self, args: str) -> CommandResult:
        """NPC 命令"""
        args = args.strip()
        if not args:
            return CommandResult.text(
                "**NPC 命令**\n"
                "`.npc create <名称> [模板]` - 创建 NPC (模板: 1=普通, 2=困难, 3=极难)\n"
                "`.npc <名称> ra <技能>` - NPC 技能检定\n"
                "`.npc <名称> ad @用户 <技能1> [技能2] [r/p]` - NPC 对抗检定\n"
                "`.npc list` - 列出当前频道 NPC\n"
                "`.npc del <名称>` - 删除 NPC\n"
                "`.npc <名称>` - 查看 NPC 属性"
            )
        
        parts = args.split(maxsplit=1)
        sub_cmd = parts[0].lower()
        sub_args = parts[1] if len(parts) > 1 else ""
        
        if sub_cmd == "create":
            return await self._npc_create(sub_args)
        
        if sub_cmd == "list":
            return await self._npc_list()
        
        if sub_cmd == "del":
            return await self._npc_delete(sub_args)
        
        # 其他情况: .npc <name> [子命令]
        npc_name = sub_cmd
        npc = await self.ctx.npc_manager.get(self.ctx.channel_id, npc_name)
        
        if not npc:
            return CommandResult.text(f"未找到 NPC: {npc_name}\n使用 `.npc create {npc_name} [1/2/3]` 创建")
        
        if not sub_args:
            return self._npc_show(npc)
        
        # 解析子命令
        sub_parts = sub_args.split(maxsplit=1)
        npc_cmd = sub_parts[0].lower()
        npc_args = sub_parts[1] if len(sub_parts) > 1 else ""
        
        if npc_cmd == "ra":
            return await self._npc_ra(npc, npc_args)
        elif npc_cmd == "ad":
            return await self._npc_ad(npc, npc_args)
        else:
            # 可能是紧凑格式
            if sub_args.lower().startswith("ra"):
                return await self._npc_ra(npc, sub_args[2:])
            elif sub_args.lower().startswith("ad"):
                return await self._npc_ad(npc, sub_args[2:])
            else:
                return CommandResult.text(f"未知 NPC 子命令: {npc_cmd}\n可用: ra, ad")
    
    async def _npc_create(self, args: str) -> CommandResult:
        """创建 NPC"""
        parts = args.split()
        if not parts:
            return CommandResult.text("格式: `.npc create <名称> [模板]`\n模板: 1=普通, 2=困难, 3=极难")
        
        name = parts[0]
        template_id = 1
        if len(parts) > 1:
            try:
                template_id = int(parts[1])
            except ValueError:
                return CommandResult.text("模板必须是数字 (1/2/3)")
        
        if template_id not in NPC_TEMPLATES:
            return CommandResult.text(f"无效模板: {template_id}\n可用: 1=普通, 2=困难, 3=极难")
        
        existing = await self.ctx.npc_manager.get(self.ctx.channel_id, name)
        if existing:
            return CommandResult.text(f"NPC **{name}** 已存在，请先删除或使用其他名称")
        
        npc = await self.ctx.npc_manager.create(self.ctx.channel_id, name, template_id)
        if not npc:
            return CommandResult.text("创建失败")
        
        template = NPC_TEMPLATES[template_id]
        attrs = " | ".join(f"{k}:{v}" for k, v in npc.attributes.items())
        skills = " | ".join(f"{k}:{v}" for k, v in npc.skills.items())
        
        return CommandResult.text(
            f"✅ NPC **{name}** 创建成功 (模板: {template['name']})\n"
            f"属性: {attrs}\n"
            f"技能: {skills}"
        )
    
    async def _npc_list(self) -> CommandResult:
        """列出频道 NPC"""
        npcs = await self.ctx.npc_manager.list_all(self.ctx.channel_id)
        if not npcs:
            return CommandResult.text("当前频道没有 NPC")
        
        lines = ["**NPC 列表**"]
        for npc in npcs:
            attrs_brief = f"STR:{npc.attributes.get('STR', '?')} DEX:{npc.attributes.get('DEX', '?')}"
            lines.append(f"• {npc.name} ({attrs_brief})")
        return CommandResult.text("\n".join(lines))
    
    async def _npc_delete(self, args: str) -> CommandResult:
        """删除 NPC"""
        name = args.strip()
        if not name:
            return CommandResult.text("格式: `.npc del <名称>`")
        
        if await self.ctx.npc_manager.delete(self.ctx.channel_id, name):
            return CommandResult.text(f"已删除 NPC: **{name}**")
        return CommandResult.text(f"未找到 NPC: {name}")
    
    def _npc_show(self, npc) -> CommandResult:
        """显示 NPC 信息"""
        attrs = " | ".join(f"{k}:{v}" for k, v in npc.attributes.items())
        skills = " | ".join(f"{k}:{v}" for k, v in npc.skills.items())
        return CommandResult.text(
            f"**{npc.name}**\n"
            f"HP: {npc.hp}/{npc.max_hp} | MP: {npc.mp}/{npc.max_mp} | 体格: {npc.build} | DB: {npc.db}\n"
            f"属性: {attrs}\n"
            f"技能: {skills}"
        )
    
    async def _npc_ra(self, npc, args: str) -> CommandResult:
        """NPC 技能检定"""
        args = args.strip()
        if not args:
            return CommandResult.text("格式: `.npc <名称> ra <技能>`")
        
        bonus, penalty, skill_name, skill_value = self._parse_ra_compact(args)
        
        if not skill_name:
            return CommandResult.text("请指定技能名称")
        
        if skill_value is None:
            skill_value = npc.get_skill(skill_name)
            if skill_value is None:
                return CommandResult.text(f"NPC **{npc.name}** 没有技能: {skill_name}")
        
        rule_settings = await self.ctx.db.get_user_rule(self.ctx.user_id)
        rule = get_rule(rule_settings["rule"], rule_settings["critical"], rule_settings["fumble"])
        
        if bonus > 0 or penalty > 0:
            roll_result = DiceRoller.roll_d100_with_bonus(bonus, penalty)
            roll = roll_result.final
            roll_detail = str(roll_result)
        else:
            roll = DiceRoller.roll_d100()
            roll_detail = f"D100={roll}"
        
        result = rule.check(roll, skill_value)
        
        return CommandResult.text(
            f"**{npc.name}** 的 **{skill_name}** 检定 ({rule.name})\n{roll_detail}/{skill_value}\n{result}"
        )
    
    async def _npc_ad(self, npc, args: str) -> CommandResult:
        """NPC 对抗检定"""
        args = args.strip()
        if not args:
            return CommandResult.text(
                "格式: `.npc <名称> ad @用户 <技能> [r/p]`\n"
                "示例: `.npc 守卫 ad @张三 斗殴 闪避 r1 p1`"
            )
        
        match = re.match(r"\(met\)(\d+)\(met\)\s*(.+)", args)
        if not match:
            return CommandResult.text("格式: `.npc <名称> ad @用户 <技能>`\n请 @ 一个用户")
        
        target_id = match.group(1)
        rest_part = match.group(2).strip()
        
        if not rest_part:
            return CommandResult.text("请指定技能名称")
        
        parts = rest_part.split()
        skills = []
        bp_list = []
        
        for part in parts:
            bp = self._parse_bonus_penalty(part)
            if bp:
                bp_list.append(bp)
            else:
                skills.append(part)
        
        if len(skills) == 0:
            return CommandResult.text("请指定技能名称")
        elif len(skills) == 1:
            npc_skill = skills[0]
            target_skill = skills[0]
        else:
            npc_skill = skills[0]
            target_skill = skills[1]
        
        npc_bonus, npc_penalty = bp_list[0] if len(bp_list) >= 1 else (0, 0)
        target_bonus, target_penalty = bp_list[1] if len(bp_list) >= 2 else (0, 0)
        
        npc_skill_value = npc.get_skill(npc_skill)
        if npc_skill_value is None:
            return CommandResult.text(f"NPC **{npc.name}** 没有技能: {npc_skill}")
        
        check = self.ctx.check_manager.create_opposed_check(
            initiator_id=f"npc:{npc.name}:{self.ctx.channel_id}",
            target_id=target_id,
            initiator_skill=npc_skill,
            target_skill=target_skill,
            channel_id=self.ctx.channel_id,
            initiator_bonus=npc_bonus,
            initiator_penalty=npc_penalty,
            target_bonus=target_bonus,
            target_penalty=target_penalty,
        )
        
        # NPC 立即进行检定
        rule_settings = await self.ctx.db.get_user_rule(target_id)
        rule = get_rule(rule_settings["rule"], rule_settings["critical"], rule_settings["fumble"])
        
        if npc_bonus > 0 or npc_penalty > 0:
            roll_result = DiceRoller.roll_d100_with_bonus(npc_bonus, npc_penalty)
            npc_roll = roll_result.final
        else:
            npc_roll = DiceRoller.roll_d100()
        
        npc_result = rule.check(npc_roll, npc_skill_value)
        
        level_values = {
            SuccessLevel.CRITICAL: 4, SuccessLevel.EXTREME: 3,
            SuccessLevel.HARD: 2, SuccessLevel.REGULAR: 1,
            SuccessLevel.FAILURE: 0, SuccessLevel.FUMBLE: 0,
        }
        npc_level = level_values[npc_result.level]
        
        self.ctx.check_manager.set_opposed_result(
            check.check_id, f"npc:{npc.name}:{self.ctx.channel_id}",
            npc_roll, npc_skill_value, npc_level
        )
        
        card = CardBuilder.build_npc_opposed_check_card(
            check_id=check.check_id,
            npc_name=npc.name,
            target_id=target_id,
            npc_skill=npc_skill,
            target_skill=target_skill,
            npc_roll=npc_roll,
            npc_target=npc_skill_value,
            npc_level=npc_result.level.value,
            npc_bp=(npc_bonus, npc_penalty),
            target_bp=(target_bonus, target_penalty),
        )
        
        logger.info(f"NPC 对抗: {npc.name}({npc_skill}) vs {target_id}({target_skill})")
        return CommandResult.card(card)
    
    def _parse_ra_compact(self, args: str) -> tuple[int, int, str, int | None]:
        """解析紧凑格式的 ra 参数"""
        args = args.strip()
        bonus, penalty = 0, 0
        skill_value = None
        skill_name = args
        
        end_num_match = re.search(r"(\d+)$", args)
        if end_num_match:
            skill_value = int(end_num_match.group(1))
            args = args[: end_num_match.start()]
        
        bp_match = re.match(r"^([rp])(\d*)", args, re.IGNORECASE)
        if bp_match:
            bp_type = bp_match.group(1).lower()
            bp_count = int(bp_match.group(2)) if bp_match.group(2) else 1
            bp_count = min(bp_count, 10)
            if bp_type == "r":
                bonus = bp_count
            else:
                penalty = bp_count
            skill_name = args[bp_match.end():]
        else:
            skill_name = args
        
        return (bonus, penalty, skill_name.strip(), skill_value)
    
    def _parse_bonus_penalty(self, token: str) -> tuple[int, int] | None:
        match = re.match(r"^([rp])(\d*)$", token.lower())
        if not match:
            return None
        bp_type, count_str = match.groups()
        count = int(count_str) if count_str else 1
        count = min(count, 10)
        return (count, 0) if bp_type == "r" else (0, count)
