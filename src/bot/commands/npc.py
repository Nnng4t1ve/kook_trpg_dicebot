"""NPC 命令"""
import json
import re
from loguru import logger
from .base import BaseCommand, CommandResult
from .registry import command
from ..card_builder import CardBuilder
from ...dice import DiceRoller
from ...dice.rules import get_rule, SuccessLevel
from ...storage.repositories import NPCTemplate


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
                "`.npc create <名称> [模板]` - 创建 NPC\n"
                "`.npc <名称> ra <技能>` - NPC 技能检定\n"
                "`.npc <名称> rha <技能>` - NPC 暗骰检定（结果私聊发送）\n"
                "`.npc <名称> gun <技能> [r奖励骰] t<波数>` - NPC 全自动枪械连发\n"
                "`.npc <名称> ad @用户 <技能1> [技能2] [r/p]` - NPC 对抗检定\n"
                "`.npc list` - 列出当前频道 NPC\n"
                "`.npc del <名称>` - 删除 NPC\n"
                "`.npc <名称>` - 查看 NPC 属性\n"
                "---\n"
                "**模板管理**\n"
                "`.npc add <模板名> <JSON>` - 添加自定义模板\n"
                "`.npc add help` - 查看模板 JSON 格式示例\n"
                "`.npc show <模板名>` - 查看模板详情\n"
                "`.npc templates` - 列出所有模板"
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
        
        if sub_cmd == "add":
            return await self._template_add(sub_args)
        
        if sub_cmd == "show":
            return await self._template_show(sub_args)
        
        if sub_cmd == "templates":
            return await self._template_list()
        
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
        elif npc_cmd == "rha":
            return await self._npc_rha(npc, npc_args)
        elif npc_cmd == "ad":
            return await self._npc_ad(npc, npc_args)
        elif npc_cmd == "gun":
            return await self._npc_gun(npc, npc_args)
        else:
            # 可能是紧凑格式
            if sub_args.lower().startswith("rha"):
                return await self._npc_rha(npc, sub_args[3:])
            elif sub_args.lower().startswith("ra"):
                return await self._npc_ra(npc, sub_args[2:])
            elif sub_args.lower().startswith("ad"):
                return await self._npc_ad(npc, sub_args[2:])
            elif sub_args.lower().startswith("gun"):
                return await self._npc_gun(npc, sub_args[3:])
            else:
                return CommandResult.text(f"未知 NPC 子命令: {npc_cmd}\n可用: ra, rha, ad, gun")
    
    async def _npc_create(self, args: str) -> CommandResult:
        """创建 NPC"""
        parts = args.split()
        if not parts:
            templates = await self.ctx.db.npc_templates.list_all()
            template_list = ", ".join(t.name for t in templates)
            return CommandResult.text(f"格式: `.npc create <名称> [模板名]`\n可用模板: {template_list}")
        
        name = parts[0]
        template_name = parts[1] if len(parts) > 1 else "普通"
        
        # 从数据库获取模板
        template = await self.ctx.db.npc_templates.find_by_name(template_name)
        if not template:
            templates = await self.ctx.db.npc_templates.list_all()
            template_list = ", ".join(t.name for t in templates)
            return CommandResult.text(f"未找到模板: {template_name}\n可用模板: {template_list}")
        
        existing = await self.ctx.npc_manager.get(self.ctx.channel_id, name)
        if existing:
            return CommandResult.text(f"NPC **{name}** 已存在，请先删除或使用其他名称")
        
        npc = await self.ctx.npc_manager.create_from_template(self.ctx.channel_id, name, template)
        if not npc:
            return CommandResult.text("创建失败")
        
        attrs = " | ".join(f"{k}:{v}" for k, v in npc.attributes.items())
        skills = " | ".join(f"{k}:{v}" for k, v in npc.skills.items())
        
        return CommandResult.text(
            f"✅ NPC **{name}** 创建成功 (模板: {template.name})\n"
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
    
    def _parse_times(self, token: str) -> int | None:
        """解析判定次数标记，如 t3, t5"""
        match = re.match(r"^t(\d+)$", token.lower())
        if not match:
            return None
        count = int(match.group(1))
        return min(max(count, 1), 10)

    async def _npc_ra(self, npc, args: str) -> CommandResult:
        """NPC 技能检定"""
        args = args.strip()
        if not args:
            return CommandResult.text("格式: `.npc <名称> ra <技能>` 或 `.npc <名称> ra p1 t3 <技能>`")
        
        # 先尝试空格分隔的格式
        parts = args.split()
        bonus, penalty = 0, 0
        times = 1
        skill_value = None
        skill_name = args
        
        if len(parts) >= 2:
            # 有空格，解析 r/p/t 参数
            remaining_parts = []
            for part in parts:
                bp_match = self._parse_bonus_penalty(part)
                times_match = self._parse_times(part)
                if bp_match:
                    b, p = bp_match
                    bonus += b
                    penalty += p
                elif times_match:
                    times = times_match
                else:
                    remaining_parts.append(part)
            
            parts = remaining_parts
            
            if not parts:
                return CommandResult.text("请指定技能名称")
            
            # 检查最后一个参数是否是数字（指定值）
            if len(parts) >= 2:
                try:
                    skill_value = int(parts[-1])
                    parts = parts[:-1]
                except ValueError:
                    pass
            
            skill_name = " ".join(parts)
        else:
            # 无空格，使用紧凑格式解析
            bonus, penalty, times, skill_name, skill_value = self._parse_ra_compact(args)
        
        if not skill_name:
            return CommandResult.text("请指定技能名称")
        
        if skill_value is None:
            skill_value = npc.get_skill(skill_name)
            if skill_value is None:
                return CommandResult.text(f"NPC **{npc.name}** 没有技能: {skill_name}")
        
        rule_settings = await self.ctx.db.get_user_rule(self.ctx.user_id)
        rule = get_rule(rule_settings["rule"], rule_settings["critical"], rule_settings["fumble"])
        
        # 多次判定
        if times > 1:
            return self._do_npc_multi_check(npc, skill_name, skill_value, bonus, penalty, times, rule)
        
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
    
    def _do_npc_multi_check(
        self, npc, skill_name: str, target: int,
        bonus: int, penalty: int, times: int, rule
    ) -> CommandResult:
        """NPC 执行多次检定"""
        bp_desc = ""
        if bonus > 0:
            bp_desc = f" (奖励骰×{bonus})" if bonus > 1 else " (奖励骰)"
        elif penalty > 0:
            bp_desc = f" (惩罚骰×{penalty})" if penalty > 1 else " (惩罚骰)"
        
        lines = [f"**{npc.name}** 的 **{skill_name}** 连续检定 ×{times}{bp_desc} ({rule.name})"]
        lines.append(f"目标值: {target}")
        lines.append("---")
        
        for i in range(times):
            if bonus > 0 or penalty > 0:
                roll_result = DiceRoller.roll_d100_with_bonus(bonus, penalty)
                roll = roll_result.final
                roll_detail = str(roll_result)
            else:
                roll = DiceRoller.roll_d100()
                roll_detail = f"D100={roll}"
            
            result = rule.check(roll, target)
            lines.append(f"第{i+1}次: {roll_detail} → {result.level.value}")
        
        return CommandResult.text("\n".join(lines))

    async def _npc_rha(self, npc, args: str) -> CommandResult:
        """NPC 暗骰技能检定 - 结果私聊发送给发起者"""
        args = args.strip()
        if not args:
            return CommandResult.text("格式: `.npc <名称> rha <技能>` 或 `.npc <名称> rha p1 t3 <技能>`")
        
        # 先尝试空格分隔的格式
        parts = args.split()
        bonus, penalty = 0, 0
        times = 1
        skill_value = None
        skill_name = args
        
        if len(parts) >= 2:
            remaining_parts = []
            for part in parts:
                bp_match = self._parse_bonus_penalty(part)
                times_match = self._parse_times(part)
                if bp_match:
                    b, p = bp_match
                    bonus += b
                    penalty += p
                elif times_match:
                    times = times_match
                else:
                    remaining_parts.append(part)
            
            parts = remaining_parts
            
            if not parts:
                return CommandResult.text("请指定技能名称")
            
            if len(parts) >= 2:
                try:
                    skill_value = int(parts[-1])
                    parts = parts[:-1]
                except ValueError:
                    pass
            
            skill_name = " ".join(parts)
        else:
            bonus, penalty, times, skill_name, skill_value = self._parse_ra_compact(args)
        
        if not skill_name:
            return CommandResult.text("请指定技能名称")
        
        if skill_value is None:
            skill_value = npc.get_skill(skill_name)
            if skill_value is None:
                return CommandResult.text(f"NPC **{npc.name}** 没有技能: {skill_name}")
        
        rule_settings = await self.ctx.db.get_user_rule(self.ctx.user_id)
        rule = get_rule(rule_settings["rule"], rule_settings["critical"], rule_settings["fumble"])
        
        # 多次判定
        if times > 1:
            return await self._do_npc_multi_check_hidden(npc, skill_name, skill_value, bonus, penalty, times, rule)
        
        # 单次检定
        if bonus > 0 or penalty > 0:
            roll_result = DiceRoller.roll_d100_with_bonus(bonus, penalty)
            roll = roll_result.final
            roll_detail = str(roll_result)
        else:
            roll = DiceRoller.roll_d100()
            roll_detail = f"D100={roll}"
        
        result = rule.check(roll, skill_value)
        
        # 私聊发送详细结果
        private_msg = f"🎲 **{npc.name}** 的 **{skill_name}** 暗骰检定 ({rule.name})\n{roll_detail}/{skill_value}\n{result}"
        await self.ctx.client.send_direct_message(self.ctx.user_id, private_msg, msg_type=9)
        
        # 频道提示
        return CommandResult.text(f"🎲 NPC **{npc.name}** 进行了 **{skill_name}** 暗骰检定", quote=False)
    
    async def _do_npc_multi_check_hidden(
        self, npc, skill_name: str, target: int,
        bonus: int, penalty: int, times: int, rule
    ) -> CommandResult:
        """NPC 执行多次暗骰检定 - 结果私聊发送"""
        bp_desc = ""
        if bonus > 0:
            bp_desc = f" (奖励骰×{bonus})" if bonus > 1 else " (奖励骰)"
        elif penalty > 0:
            bp_desc = f" (惩罚骰×{penalty})" if penalty > 1 else " (惩罚骰)"
        
        lines = [f"🎲 **{npc.name}** 的 **{skill_name}** 暗骰连续检定 ×{times}{bp_desc} ({rule.name})"]
        lines.append(f"目标值: {target}")
        lines.append("---")
        
        for i in range(times):
            if bonus > 0 or penalty > 0:
                roll_result = DiceRoller.roll_d100_with_bonus(bonus, penalty)
                roll = roll_result.final
                roll_detail = str(roll_result)
            else:
                roll = DiceRoller.roll_d100()
                roll_detail = f"D100={roll}"
            
            result = rule.check(roll, target)
            lines.append(f"第{i+1}次: {roll_detail} → {result.level.value}")
        
        # 私聊发送详细结果
        private_msg = "\n".join(lines)
        await self.ctx.client.send_direct_message(self.ctx.user_id, private_msg, msg_type=9)
        
        # 频道提示
        return CommandResult.text(f"🎲 NPC **{npc.name}** 进行了 **{skill_name}** 暗骰连续检定 ×{times}", quote=False)
    
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
    
    def _parse_ra_compact(self, args: str) -> tuple[int, int, int, str, int | None]:
        """
        解析紧凑格式的 ra 参数，支持 t 参数
        返回: (bonus, penalty, times, skill_name, skill_value or None)
        """
        args = args.strip()
        bonus, penalty = 0, 0
        times = 1
        skill_value = None
        skill_name = args
        
        # 先提取末尾的数字（技能值）
        end_num_match = re.search(r"(\d+)$", args)
        if end_num_match:
            skill_value = int(end_num_match.group(1))
            args = args[: end_num_match.start()]
        
        # 解析开头的奖励骰/惩罚骰和次数（可能有多个，如 p1t3 或 r2t2）
        while args:
            # 检查奖励骰/惩罚骰
            bp_match = re.match(r"^([rp])(\d*)", args, re.IGNORECASE)
            if bp_match:
                bp_type = bp_match.group(1).lower()
                bp_count = int(bp_match.group(2)) if bp_match.group(2) else 1
                bp_count = min(bp_count, 10)
                if bp_type == "r":
                    bonus += bp_count
                else:
                    penalty += bp_count
                args = args[bp_match.end():]
                continue
            
            # 检查次数
            times_match = re.match(r"^t(\d+)", args, re.IGNORECASE)
            if times_match:
                times = int(times_match.group(1))
                times = min(max(times, 1), 10)
                args = args[times_match.end():]
                continue
            
            # 没有匹配到，剩余的就是技能名
            break
        
        skill_name = args.strip()
        
        return (bonus, penalty, times, skill_name, skill_value)
    
    def _parse_bonus_penalty(self, token: str) -> tuple[int, int] | None:
        match = re.match(r"^([rp])(\d*)$", token.lower())
        if not match:
            return None
        bp_type, count_str = match.groups()
        count = int(count_str) if count_str else 1
        count = min(count, 10)
        return (count, 0) if bp_type == "r" else (0, count)

    async def _npc_gun(self, npc, args: str) -> CommandResult:
        """NPC 全自动枪械连发判定"""
        args = args.strip()
        if not args:
            return CommandResult.text(
                "格式: `.npc <名称> gun <技能> [r奖励骰] [p惩罚骰] t<波数>`\n"
                "例如: `.npc 守卫 gun 冲锋枪 r1 t5`"
            )
        
        # 解析参数
        env_bonus, env_penalty, times, skill_name, skill_value = self._parse_gun_args(args)
        
        if not skill_name:
            return CommandResult.text("请指定技能名称")
        
        if times < 1:
            return CommandResult.text("请指定连发波数，如: t5")
        
        times = min(times, 10)
        
        if skill_value is None:
            skill_value = npc.get_skill(skill_name)
            if skill_value is None:
                return CommandResult.text(f"NPC **{npc.name}** 没有技能: {skill_name}")
        
        rule_settings = await self.ctx.db.get_user_rule(self.ctx.user_id)
        rule = get_rule(rule_settings["rule"], rule_settings["critical"], rule_settings["fumble"])
        
        # 每波弹幕的子弹数 = 技能值 / 10
        bullets_per_burst = skill_value // 10
        
        env_desc_parts = []
        if env_bonus > 0:
            env_desc_parts.append(f"环境奖励骰×{env_bonus}")
        if env_penalty > 0:
            env_desc_parts.append(f"环境惩罚骰×{env_penalty}")
        env_desc = f" ({', '.join(env_desc_parts)})" if env_desc_parts else ""
        lines = [f"🔫 **{npc.name}** 的 **{skill_name}** 全自动连发 ×{times}波{env_desc} ({rule.name})"]
        lines.append(f"基础目标值: {skill_value} | 每波弹幕: {bullets_per_burst}发")
        lines.append("---")
        
        total_hits = 0
        total_penetrate = 0
        total_normal = 0
        
        for i in range(times):
            burst_num = i + 1
            burst_penalty, difficulty_level, is_auto_fail, half_only = self._calc_burst_params(burst_num)
            
            if is_auto_fail:
                lines.append(f"第{burst_num}波: ❌ 不命中 (连发上限)")
                continue
            
            # 计算实际奖励骰/惩罚骰
            total_penalty = burst_penalty + env_penalty
            net_bonus = env_bonus - total_penalty
            actual_bonus = max(0, net_bonus)
            actual_penalty = max(0, -net_bonus)
            
            if difficulty_level == 0:
                actual_target = skill_value
                diff_desc = ""
            elif difficulty_level == 1:
                actual_target = skill_value // 2
                diff_desc = "[困难] "
            elif difficulty_level == 2:
                actual_target = skill_value // 5
                diff_desc = "[极难] "
            else:
                actual_target = 1
                diff_desc = "[需大成功] "
            
            if actual_bonus > 0 or actual_penalty > 0:
                roll_result = DiceRoller.roll_d100_with_bonus(actual_bonus, actual_penalty)
                roll = roll_result.final
                roll_detail = str(roll_result)
            else:
                roll = DiceRoller.roll_d100()
                roll_detail = f"D100={roll}"
            
            result = rule.check(roll, actual_target)
            
            if difficulty_level == 3:
                if result.level == SuccessLevel.CRITICAL:
                    is_success = True
                    result_text = "大成功"
                else:
                    is_success = False
                    result_text = "失败"
            else:
                is_success = result.is_success
                result_text = result.level.value
            
            # 计算命中子弹数和贯穿数
            hits = 0
            penetrate = 0
            
            if not is_success:
                hits = 0
            elif half_only:
                hits = bullets_per_burst // 2
            elif result.level in (SuccessLevel.CRITICAL, SuccessLevel.EXTREME):
                hits = bullets_per_burst
                if difficulty_level < 2:
                    penetrate = max(1, hits // 2)
            else:
                hits = bullets_per_burst // 2
            
            normal_hits = hits - penetrate
            total_hits += hits
            total_penetrate += penetrate
            total_normal += normal_hits
            
            bp_info = self._build_bp_info(burst_penalty, env_bonus, env_penalty, actual_bonus, actual_penalty)
            if not is_success:
                hit_mark = "未命中"
            elif penetrate > 0:
                hit_mark = f"命中 {hits}发 (贯穿{penetrate}发)"
            else:
                hit_mark = f"命中 {hits}/{bullets_per_burst}发"
            
            lines.append(
                f"第{burst_num}波: {diff_desc}{roll_detail} → {result_text} | {hit_mark}"
                f"\n　　　{bp_info}"
            )
        
        lines.append("---")
        if total_penetrate > 0:
            lines.append(f"**总命中: {total_hits}发** (贯穿{total_penetrate}发 + 普通{total_normal}发)")
        else:
            lines.append(f"**总命中: {total_hits}发**")
        
        return CommandResult.text("\n".join(lines))
    
    def _parse_gun_args(self, args: str) -> tuple[int, int, int, str, int | None]:
        """解析全自动枪械参数"""
        parts = args.split()
        env_bonus = 0
        env_penalty = 0
        times = 0
        skill_value = None
        skill_name = ""
        
        remaining_parts = []
        for part in parts:
            # 解析环境奖励骰/惩罚骰 r1, r2, p1, p2
            bp_match = re.match(r"^([rp])(\d*)$", part.lower())
            if bp_match:
                bp_type = bp_match.group(1)
                bp_count = int(bp_match.group(2)) if bp_match.group(2) else 1
                bp_count = min(bp_count, 5)
                if bp_type == "r":
                    env_bonus += bp_count
                else:
                    env_penalty += bp_count
                continue
            
            t_match = re.match(r"^t(\d+)$", part.lower())
            if t_match:
                times = int(t_match.group(1))
                continue
            
            remaining_parts.append(part)
        
        if remaining_parts:
            skill_str = " ".join(remaining_parts)
            end_num_match = re.search(r"(\d+)$", skill_str)
            if end_num_match:
                skill_value = int(end_num_match.group(1))
                skill_name = skill_str[:end_num_match.start()].strip()
            else:
                skill_name = skill_str.strip()
        
        return (env_bonus, env_penalty, times, skill_name, skill_value)
    
    def _calc_burst_params(self, burst_num: int) -> tuple[int, int, bool, bool]:
        """计算第 N 波弹幕的参数"""
        if burst_num == 1:
            return (0, 0, False, False)
        elif burst_num == 2:
            return (1, 0, False, False)
        elif burst_num == 3:
            return (2, 0, False, False)
        elif burst_num == 4:
            return (2, 1, False, False)
        elif burst_num == 5:
            return (2, 2, False, True)
        elif burst_num == 6:
            return (2, 3, False, True)
        else:
            return (2, 3, True, True)
    
    def _build_bp_info(
        self, burst_penalty: int, env_bonus: int, env_penalty: int,
        actual_bonus: int, actual_penalty: int
    ) -> str:
        """构建奖励骰/惩罚骰信息描述"""
        parts = []
        if burst_penalty > 0:
            parts.append(f"连发惩罚骰×{burst_penalty}")
        if env_bonus > 0:
            parts.append(f"环境奖励骰×{env_bonus}")
        if env_penalty > 0:
            parts.append(f"环境惩罚骰×{env_penalty}")
        if not parts:
            return "无修正"
        calc = ", ".join(parts)
        if actual_bonus > 0:
            result = f"实际奖励骰×{actual_bonus}"
        elif actual_penalty > 0:
            result = f"实际惩罚骰×{actual_penalty}"
        else:
            result = "抵消"
        return f"({calc} → {result})"

    # ===== 模板管理 =====
    
    # 基础属性名称（用于自动识别）
    BASE_ATTR_NAMES = {
        "力量": "STR", "str": "STR", "STR": "STR",
        "体质": "CON", "con": "CON", "CON": "CON",
        "体型": "SIZ", "siz": "SIZ", "SIZ": "SIZ",
        "敏捷": "DEX", "dex": "DEX", "DEX": "DEX",
        "外貌": "APP", "app": "APP", "APP": "APP",
        "智力": "INT", "int": "INT", "INT": "INT", "灵感": "INT",
        "意志": "POW", "pow": "POW", "POW": "POW", "精神": "POW",
        "教育": "EDU", "edu": "EDU", "EDU": "EDU",
        "幸运": "LUK", "luk": "LUK", "LUK": "LUK", "运气": "LUK",
    }
    
    def _parse_template_text(self, text: str) -> tuple[dict, dict]:
        """
        解析模板文本，自动识别属性和技能
        
        格式: 名称 值表达式 名称 值表达式 ...
        值表达式: 骰子公式(3d6+6) 或 范围(20-30) 或 固定值(50)
        
        返回: (attributes, skills)
        """
        attributes = {}
        skills = {}
        
        # 按空格分割，每两个为一组（名称 + 值）
        parts = text.split()
        i = 0
        while i < len(parts) - 1:
            name = parts[i]
            value_expr = parts[i + 1]
            
            # 检查是否是属性名
            if name in self.BASE_ATTR_NAMES:
                attr_key = self.BASE_ATTR_NAMES[name]
                attributes[attr_key] = value_expr
            else:
                # 否则视为技能
                skills[name] = value_expr
            
            i += 2
        
        return attributes, skills
    
    async def _template_add(self, args: str) -> CommandResult:
        """添加 NPC 模板"""
        args = args.strip()
        
        if not args or args.lower() == "help":
            return CommandResult.text(
                "**添加 NPC 模板**\n"
                "格式: `.npc add <模板名> <属性/技能定义>`\n\n"
                "**值表达式:**\n"
                "• 骰子公式: `3d6+6` → 结果×5\n"
                "• 范围: `20-30` → 随机整数\n"
                "• 固定值: `50`\n\n"
                "**示例:**\n"
                "`.npc add 深潜者 力量 3d6+6 体质 3d6+20 敏捷 3d6 格斗 3d6 闪避 20-30`\n\n"
                "**支持的属性名:**\n"
                "力量/STR, 体质/CON, 体型/SIZ, 敏捷/DEX, 外貌/APP, 智力/INT, 意志/POW, 教育/EDU\n\n"
                "其他名称自动识别为技能"
            )
        
        # 解析模板名和定义
        parts = args.split(maxsplit=1)
        if len(parts) < 2:
            return CommandResult.text("格式: `.npc add <模板名> <属性/技能定义>`\n使用 `.npc add help` 查看示例")
        
        template_name = parts[0]
        definition = parts[1].strip()
        
        # 检查是否为内置模板
        existing = await self.ctx.db.npc_templates.find_by_name(template_name)
        if existing and existing.is_builtin:
            return CommandResult.text(f"❌ 无法覆盖内置模板: {template_name}")
        
        # 解析属性和技能
        try:
            attributes, skills = self._parse_template_text(definition)
        except Exception as e:
            return CommandResult.text(f"❌ 解析失败: {e}")
        
        if not attributes and not skills:
            return CommandResult.text("❌ 未识别到任何属性或技能\n使用 `.npc add help` 查看格式")
        
        # 创建模板
        template = NPCTemplate(
            name=template_name,
            attributes=attributes,
            skills=skills,
            description="",
            is_builtin=False,
        )
        
        await self.ctx.db.npc_templates.save(template)
        
        action = "更新" if existing else "添加"
        attr_list = ", ".join(f"{k}={v}" for k, v in attributes.items()) if attributes else "无"
        skill_list = ", ".join(f"{k}={v}" for k, v in skills.items()) if skills else "无"
        
        return CommandResult.text(
            f"✅ 模板 **{template_name}** {action}成功\n"
            f"属性: {attr_list}\n"
            f"技能: {skill_list}"
        )
    
    async def _template_show(self, args: str) -> CommandResult:
        """查看模板详情"""
        template_name = args.strip()
        if not template_name:
            return CommandResult.text("格式: `.npc show <模板名>`")
        
        template = await self.ctx.db.npc_templates.find_by_name(template_name)
        if not template:
            return CommandResult.text(f"未找到模板: {template_name}")
        
        lines = [f"**模板: {template.name}**"]
        if template.is_builtin:
            lines.append("(内置模板)")
        if template.description:
            lines.append(f"描述: {template.description}")
        
        # 新格式模板
        if template.attributes:
            attr_list = ", ".join(f"{k}={v}" for k, v in template.attributes.items())
            lines.append(f"属性: {attr_list}")
        elif template.is_legacy_format():
            lines.append(f"属性范围: {template.attr_min}-{template.attr_max}")
        
        if template.skills:
            skill_list = ", ".join(f"{k}={v}" for k, v in template.skills.items())
            lines.append(f"技能: {skill_list}")
        elif template.is_legacy_format():
            lines.append(f"技能范围: {template.skill_min}-{template.skill_max}")
        
        return CommandResult.text("\n".join(lines))
    
    async def _template_list(self) -> CommandResult:
        """列出所有模板"""
        templates = await self.ctx.db.npc_templates.list_all()
        if not templates:
            return CommandResult.text("暂无模板")
        
        lines = ["**NPC 模板列表**"]
        for t in templates:
            builtin_mark = " (内置)" if t.is_builtin else ""
            if t.attributes:
                # 新格式
                attr_count = len(t.attributes)
                skill_count = len(t.skills)
                lines.append(f"• **{t.name}**{builtin_mark}: {attr_count}属性, {skill_count}技能")
            else:
                # 旧格式
                lines.append(f"• **{t.name}**{builtin_mark}: 属性 {t.attr_min}-{t.attr_max}, 技能 {t.skill_min}-{t.skill_max}")
        
        lines.append("\n使用 `.npc show <模板名>` 查看详情")
        return CommandResult.text("\n".join(lines))
