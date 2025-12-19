"""检定命令"""
import re
from loguru import logger
from .base import BaseCommand, CommandResult
from .registry import command
from ..card_builder import CardBuilder
from ...dice import DiceParser, DiceRoller
from ...dice.rules import get_rule


@command("check")
class KPCheckCommand(BaseCommand):
    """KP 发起检定命令"""
    
    description = "KP 发起检定"
    usage = ".check 侦查 [描述] 或 .check sc0/1d6 [描述]"
    
    async def execute(self, args: str) -> CommandResult:
        """KP 发起检定: .check 侦查 [描述] 或 .check sc1d3/1d10 [描述]"""
        parts = args.split(maxsplit=1)
        if not parts:
            return CommandResult.text(
                "格式: `.check <技能名> [描述]`\n"
                "示例: `.check 侦查 仔细搜索房间`\n"
                "`.check sc0/1d6` - SAN Check"
            )
        
        skill_name = parts[0]
        description = parts[1] if len(parts) > 1 else ""
        
        # 检测 SAN check 格式: sc0/1d6, sc1d3/1d10 等
        san_match = re.match(r"^sc(.+)/(.+)$", skill_name, re.IGNORECASE)
        if san_match:
            success_expr = san_match.group(1).strip()
            fail_expr = san_match.group(2).strip()
            
            # 创建 SAN check
            check = self.ctx.check_manager.create_check(
                skill_name=f"sc:{success_expr}/{fail_expr}",
                channel_id=self.ctx.channel_id,
                kp_id=self.ctx.user_id
            )
            
            # 构建 SAN check 卡片
            card = CardBuilder.build_san_check_card(
                check_id=check.check_id,
                success_expr=success_expr,
                fail_expr=fail_expr,
                description=description,
                kp_name=self.ctx.user_name
            )
            
            logger.info(f"KP {self.ctx.user_id} 发起 SAN Check: {success_expr}/{fail_expr}")
            return CommandResult.card(card)
        
        # 普通技能检定
        check = self.ctx.check_manager.create_check(
            skill_name=skill_name,
            channel_id=self.ctx.channel_id,
            kp_id=self.ctx.user_id
        )
        
        # 构建卡片
        card = CardBuilder.build_check_card(
            check_id=check.check_id,
            skill_name=skill_name,
            description=description,
            kp_name=self.ctx.user_name
        )
        
        logger.info(f"KP {self.ctx.user_id} 发起检定: {skill_name}")
        return CommandResult.card(card)



@command("sc", compact=True)
class SanCheckCommand(BaseCommand):
    """SAN Check 命令"""
    
    description = "SAN Check"
    usage = ".sc 0/1d6, .sc1/1d10, .sc 1d4/2d6"
    
    async def execute(self, args: str) -> CommandResult:
        """SAN Check: .sc 0/1d6, .sc1/1d10, .sc 1d4/2d6"""
        from ...data.madness import roll_temporary_madness
        
        args = args.strip()
        if not args:
            return CommandResult.text(
                "格式: .sc <成功损失>/<失败损失>\n"
                "示例: .sc 0/1d6, .sc 1/1d4+1, .sc 1d4/2d6"
            )
        
        # 解析成功/失败损失表达式
        if "/" not in args:
            return CommandResult.text("格式错误，需要用 / 分隔成功和失败的损失值\n示例: .sc 0/1d6")
        
        success_expr, fail_expr = args.split("/", 1)
        success_expr = success_expr.strip()
        fail_expr = fail_expr.strip()
        
        # 获取角色卡
        char = await self.ctx.char_manager.get_active(self.ctx.user_id)
        if not char:
            return CommandResult.text("请先导入角色卡")
        
        current_san = char.san
        if current_san <= 0:
            return CommandResult.text(f"**{char.name}** 的 SAN 值已经为 0，无法进行 SAN Check")
        
        # 进行 SAN 检定 (d100 <= san 为成功)
        roll = DiceRoller.roll_d100()
        is_success = roll <= current_san
        
        # 计算损失
        loss_expr = success_expr if is_success else fail_expr
        loss = self._calc_san_loss(loss_expr)
        
        if loss is None:
            return CommandResult.text(f"无法解析损失表达式: {loss_expr}")
        
        # 更新 SAN 值
        new_san = max(0, current_san - loss)
        char.san = new_san
        await self.ctx.char_manager.add(char)
        
        # 构建结果
        result_text = "成功" if is_success else "失败"
        lines = [
            f"**{char.name}** 的 SAN Check",
            f"D100={roll}/{current_san} [{result_text}]",
            f"损失: {loss_expr} = {loss}",
            f"SAN: {current_san} → **{new_san}**",
        ]
        
        # 检查是否触发临时疯狂 (单次损失 >= 5)
        if loss >= 5:
            madness = roll_temporary_madness()
            lines.append("")
            lines.append(f"⚠️ **触发临时疯狂！** (单次损失≥5)")
            lines.append(f"🎲 症状骰点: 1D10={madness['roll']}")
            lines.append(f"**{madness['name']}** - 持续 {madness['duration']}")
            lines.append(f"_{madness['description']}_")
        
        # 检查是否陷入永久疯狂 (SAN 归零)
        if new_san == 0:
            lines.append("")
            lines.append("💀 **SAN 值归零，陷入永久疯狂！**")
        
        return CommandResult.text("\n".join(lines))
    
    def _calc_san_loss(self, expr: str) -> int | None:
        """计算 SAN 损失值，支持数字或骰点表达式"""
        expr = expr.strip()
        
        # 纯数字
        if expr.isdigit():
            return int(expr)
        
        # 骰点表达式
        expr = self._normalize_dice_expr(expr)
        parsed = DiceParser.parse(expr)
        if parsed:
            result = DiceRoller.roll(parsed)
            return max(0, result.total)
        
        return None
    
    def _normalize_dice_expr(self, expr: str) -> str:
        """规范化骰点表达式"""
        expr = expr.strip()
        if not expr:
            return "d100"
        if expr.isdigit():
            return f"d{expr}"
        if expr[0].isdigit():
            match = re.match(r"^(\d+)([+-])", expr)
            if match:
                expr = f"d{expr}"
        return expr



@command("ad")
class OpposedCheckCommand(BaseCommand):
    """对抗检定命令"""
    
    description = "对抗检定"
    usage = ".ad @用户 力量 或 .ad npc <npc名> 斗殴 闪避 r1 p1"
    
    async def execute(self, args: str) -> CommandResult:
        """对抗检定: .ad @用户 力量 或 .ad npc <npc名> 斗殴 闪避 r1 p1"""
        args = args.strip()
        if not args:
            return CommandResult.text(
                "格式: `.ad @用户 <技能> [r/p] [r/p]`\n"
                "或: `.ad npc <NPC名> <技能> [r/p] [r/p]`\n"
                "示例: `.ad @张三 力量` 或 `.ad npc 守卫 斗殴 闪避 r1 p1`"
            )
        
        # 检查是否是 NPC 对抗
        if args.lower().startswith("npc "):
            return await self._opposed_check_vs_npc(args[4:].strip())
        
        # 解析 @用户 (KOOK 格式: (met)用户ID(met))
        match = re.match(r"\(met\)(\d+)\(met\)\s*(.+)", args)
        if not match:
            return CommandResult.text("格式: `.ad @用户 <技能>` 或 `.ad npc <NPC名> <技能>`")
        
        target_id = match.group(1)
        rest_part = match.group(2).strip()
        
        if not rest_part:
            return CommandResult.text("请指定技能名称")
        
        if target_id == self.ctx.user_id:
            return CommandResult.text("不能和自己对抗")
        
        # 解析参数
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
            initiator_skill = skills[0]
            target_skill = skills[0]
        else:
            initiator_skill = skills[0]
            target_skill = skills[1]
        
        initiator_bonus, initiator_penalty = bp_list[0] if len(bp_list) >= 1 else (0, 0)
        target_bonus, target_penalty = bp_list[1] if len(bp_list) >= 2 else (0, 0)
        
        # 创建对抗检定
        check = self.ctx.check_manager.create_opposed_check(
            initiator_id=self.ctx.user_id,
            target_id=target_id,
            initiator_skill=initiator_skill,
            target_skill=target_skill,
            channel_id=self.ctx.channel_id,
            initiator_bonus=initiator_bonus,
            initiator_penalty=initiator_penalty,
            target_bonus=target_bonus,
            target_penalty=target_penalty,
        )
        
        card = CardBuilder.build_opposed_check_card(
            check_id=check.check_id,
            initiator_name=self.ctx.user_name,
            target_id=target_id,
            initiator_skill=initiator_skill,
            target_skill=target_skill,
            initiator_bp=(initiator_bonus, initiator_penalty),
            target_bp=(target_bonus, target_penalty),
        )
        
        logger.info(f"对抗检定: {self.ctx.user_id}({initiator_skill}) vs {target_id}({target_skill})")
        return CommandResult.card(card)
    
    async def _opposed_check_vs_npc(self, args: str) -> CommandResult:
        """玩家向 NPC 发起对抗"""
        from ...dice.rules import SuccessLevel
        
        parts = args.split()
        if not parts:
            return CommandResult.text("格式: `.ad npc <NPC名> <技能> [r/p]`")
        
        npc_name = parts[0]
        rest_parts = parts[1:]
        
        npc = await self.ctx.npc_manager.get(self.ctx.channel_id, npc_name)
        if not npc:
            return CommandResult.text(f"未找到 NPC: {npc_name}")
        
        if not rest_parts:
            return CommandResult.text("请指定技能名称")
        
        skills = []
        bp_list = []
        
        for part in rest_parts:
            bp = self._parse_bonus_penalty(part)
            if bp:
                bp_list.append(bp)
            else:
                skills.append(part)
        
        if len(skills) == 0:
            return CommandResult.text("请指定技能名称")
        elif len(skills) == 1:
            player_skill = skills[0]
            npc_skill = skills[0]
        else:
            player_skill = skills[0]
            npc_skill = skills[1]
        
        player_bonus, player_penalty = bp_list[0] if len(bp_list) >= 1 else (0, 0)
        npc_bonus, npc_penalty = bp_list[1] if len(bp_list) >= 2 else (0, 0)
        
        npc_skill_value = npc.get_skill(npc_skill)
        if npc_skill_value is None:
            return CommandResult.text(f"NPC **{npc_name}** 没有技能: {npc_skill}")
        
        check = self.ctx.check_manager.create_opposed_check(
            initiator_id=self.ctx.user_id,
            target_id=f"npc:{npc_name}:{self.ctx.channel_id}",
            initiator_skill=player_skill,
            target_skill=npc_skill,
            channel_id=self.ctx.channel_id,
            initiator_bonus=player_bonus,
            initiator_penalty=player_penalty,
            target_bonus=npc_bonus,
            target_penalty=npc_penalty,
        )
        
        # NPC 立即进行检定
        rule_settings = await self.ctx.db.get_user_rule(self.ctx.user_id)
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
            SuccessLevel.FAILURE: 0, SuccessLevel.FUMBLE: -1,
        }
        npc_level = level_values[npc_result.level]
        
        self.ctx.check_manager.set_opposed_result(
            check.check_id, f"npc:{npc_name}:{self.ctx.channel_id}",
            npc_roll, npc_skill_value, npc_level
        )
        
        card = CardBuilder.build_player_vs_npc_opposed_card(
            check_id=check.check_id,
            player_name=self.ctx.user_name,
            player_id=self.ctx.user_id,
            npc_name=npc_name,
            player_skill=player_skill,
            npc_skill=npc_skill,
            npc_roll=npc_roll,
            npc_target=npc_skill_value,
            npc_level=npc_result.level.value,
            player_bp=(player_bonus, player_penalty),
            npc_bp=(npc_bonus, npc_penalty),
        )
        
        logger.info(f"玩家对抗NPC: {self.ctx.user_id}({player_skill}) vs {npc_name}({npc_skill})")
        return CommandResult.card(card)
    
    def _parse_bonus_penalty(self, token: str) -> tuple[int, int] | None:
        match = re.match(r"^([rp])(\d*)$", token.lower())
        if not match:
            return None
        bp_type, count_str = match.groups()
        count = int(count_str) if count_str else 1
        count = min(count, 10)
        return (count, 0) if bp_type == "r" else (0, count)



@command("dmg")
class DamageCommand(BaseCommand):
    """伤害命令"""
    
    description = "对目标造成伤害"
    usage = ".dmg @用户 <伤害> 或 .dmg npc <名称> <伤害>"
    
    async def execute(self, args: str) -> CommandResult:
        """伤害命令: .dmg @用户 <伤害表达式> 或 .dmg npc <名称> <伤害表达式>"""
        args = args.strip()
        if not args:
            return CommandResult.text(
                "**伤害命令**\n"
                "`.dmg @用户 <伤害>` - 对玩家造成伤害\n"
                "`.dmg npc <名称> <伤害>` - 对 NPC 造成伤害\n"
                "示例: `.dmg @张三 1d6+2`, `.dmg npc 守卫 2d6`"
            )
        
        # 检查是否是 NPC
        if args.lower().startswith("npc "):
            return await self._damage_npc(args[4:].strip())
        
        # 解析 @用户
        match = re.match(r"\(met\)(\d+)\(met\)\s*(.+)", args)
        if not match:
            return CommandResult.text("格式: `.dmg @用户 <伤害>` 或 `.dmg npc <名称> <伤害>`")
        
        target_id = match.group(1)
        damage_expr = match.group(2).strip()
        
        if not damage_expr:
            return CommandResult.text("请指定伤害值，如: `.dmg @用户 1d6+2`")
        
        # 验证伤害表达式
        normalized_expr = self._normalize_dice_expr(damage_expr)
        if not damage_expr.isdigit() and not DiceParser.parse(normalized_expr):
            return CommandResult.text(f"无法解析伤害表达式: {damage_expr}")
        
        # 获取目标角色卡
        char = await self.ctx.char_manager.get_active(target_id)
        if not char:
            return CommandResult.text(f"(met){target_id}(met) 没有激活的角色卡")
        
        # 创建伤害检定
        check = self.ctx.check_manager.create_damage_check(
            initiator_id=self.ctx.user_id,
            target_type="player",
            target_id=target_id,
            channel_id=self.ctx.channel_id,
            damage_expr=damage_expr,
        )
        
        card = CardBuilder.build_damage_card(
            check_id=check.check_id,
            initiator_name=self.ctx.user_name,
            target_name=char.name,
            target_type="player",
            damage_expr=damage_expr,
            target_id=target_id,
        )
        
        logger.info(f"伤害检定: {self.ctx.user_id} -> {target_id}, expr={damage_expr}")
        return CommandResult.card(card)
    
    async def _damage_npc(self, args: str) -> CommandResult:
        """对 NPC 造成伤害"""
        parts = args.split(maxsplit=1)
        if len(parts) < 2:
            return CommandResult.text("格式: `.dmg npc <名称> <伤害>`\n示例: `.dmg npc 守卫 2d6`")
        
        npc_name = parts[0]
        damage_expr = parts[1].strip()
        
        npc = await self.ctx.npc_manager.get(self.ctx.channel_id, npc_name)
        if not npc:
            return CommandResult.text(f"未找到 NPC: {npc_name}")
        
        normalized_expr = self._normalize_dice_expr(damage_expr)
        if not damage_expr.isdigit() and not DiceParser.parse(normalized_expr):
            return CommandResult.text(f"无法解析伤害表达式: {damage_expr}")
        
        check = self.ctx.check_manager.create_damage_check(
            initiator_id=self.ctx.user_id,
            target_type="npc",
            target_id=npc_name,
            channel_id=self.ctx.channel_id,
            damage_expr=damage_expr,
        )
        
        card = CardBuilder.build_damage_card(
            check_id=check.check_id,
            initiator_name=self.ctx.user_name,
            target_name=npc.name,
            target_type="npc",
            damage_expr=damage_expr,
        )
        
        logger.info(f"NPC伤害检定: {self.ctx.user_id} -> {npc_name}, expr={damage_expr}")
        return CommandResult.card(card)
    
    def _normalize_dice_expr(self, expr: str) -> str:
        expr = expr.strip()
        if not expr:
            return "d100"
        if expr.isdigit():
            return f"d{expr}"
        if expr[0].isdigit():
            match = re.match(r"^(\d+)([+-])", expr)
            if match:
                expr = f"d{expr}"
        return expr
