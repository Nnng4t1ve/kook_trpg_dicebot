"""骰点命令"""
import re
from .base import BaseCommand, CommandResult
from .registry import command
from ...dice import DiceParser, DiceRoller
from ...dice.rules import get_rule


@command("r", aliases=["rd"], compact=True)
class RollCommand(BaseCommand):
    """基础骰点命令"""
    
    description = "骰点"
    usage = ".r 1d100, .rd100, .rd6+d4+3, .rd r2 d100"
    
    async def execute(self, args: str) -> CommandResult:
        """基础骰点: .r 1d100, .rd100, .rd6+d4+3, .rd r2 d100"""
        args = args.strip() or "1d100"
        
        # 解析奖励骰/惩罚骰: r1, r2, p1, p2 等
        bonus, penalty = 0, 0
        parts = args.split()
        expr_str = args
        
        if len(parts) >= 1:
            bp_match = self._parse_bonus_penalty(parts[0])
            if bp_match:
                bonus, penalty = bp_match
                expr_str = " ".join(parts[1:]) or "d100"
        
        # 处理紧凑格式：如果表达式以数字开头，补上 d
        expr_str = self._normalize_dice_expr(expr_str)
        
        # 如果是 d100 且有奖励/惩罚骰，使用特殊处理
        if (bonus > 0 or penalty > 0) and expr_str.lower() in ("d100", "1d100"):
            result = DiceRoller.roll_d100_with_bonus(bonus, penalty)
            return CommandResult.text(str(result))
        
        # 普通骰点
        expr = DiceParser.parse(expr_str)
        if not expr:
            return CommandResult.text(f"无效的骰点表达式: {expr_str}")
        
        result = DiceRoller.roll(expr)
        return CommandResult.text(str(result))
    
    def _normalize_dice_expr(self, expr: str) -> str:
        """
        规范化骰点表达式，处理紧凑格式
        - "100" -> "d100"
        - "6+d4+3" -> "d6+d4+3"
        - "d6+4" -> "d6+4" (不变)
        """
        expr = expr.strip()
        if not expr:
            return "d100"
        
        # 如果整个表达式就是一个数字，当作 dN
        if expr.isdigit():
            return f"d{expr}"
        
        # 处理表达式开头：如果以数字开头且后面是 +/-，补上 d
        if expr[0].isdigit():
            match = re.match(r"^(\d+)([+-])", expr)
            if match:
                expr = f"d{expr}"
        
        return expr
    
    def _parse_bonus_penalty(self, token: str) -> tuple[int, int] | None:
        """解析奖励骰/惩罚骰标记，返回 (bonus, penalty) 或 None"""
        match = re.match(r"^([rp])(\d*)$", token.lower())
        if not match:
            return None
        bp_type, count_str = match.groups()
        count = int(count_str) if count_str else 1
        count = min(count, 10)  # 限制最多10个
        if bp_type == "r":
            return (count, 0)
        else:
            return (0, count)


@command("ra", compact=True)
class RollAttributeCommand(BaseCommand):
    """技能检定命令"""
    
    description = "技能检定"
    usage = ".ra侦查, .ra侦查50, .rar2侦查, .rap1聆听60, .ra手枪 p1 t3"
    
    async def execute(self, args: str) -> CommandResult:
        """技能检定: .ra侦查, .ra侦查50, .rar2侦查, .rap1聆听60, .ra手枪 p1 t3"""
        args = args.strip()
        if not args:
            return CommandResult.text("请指定技能名称，如: .ra侦查 或 .ra侦查50")
        
        # 先尝试空格分隔的格式（向后兼容）
        parts = args.split()
        bonus, penalty = 0, 0
        times = 1  # 判定次数
        skill_value = None
        skill_name = args
        
        if len(parts) >= 2:
            # 有空格，使用原来的解析逻辑，同时解析 t 参数
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
                return CommandResult.text("请指定技能名称，如: .ra侦查 或 .rar2侦查")
            
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
            return CommandResult.text("请指定技能名称，如: .ra侦查 或 .ra侦查50")
        
        # 如果没有指定值，从角色卡获取
        if skill_value is None:
            char = await self.ctx.char_manager.get_active(self.ctx.user_id)
            if not char:
                return CommandResult.text("请先导入角色卡或指定技能值，如: .ra侦查50")
            
            skill_value = char.get_skill(skill_name)
            if skill_value is None:
                return CommandResult.text(f"未找到技能: {skill_name}，可指定值: .ra{skill_name}50")
        
        # 多次判定
        if times > 1:
            return await self._do_multi_check(skill_name, skill_value, bonus, penalty, times)
        
        return await self._do_check(skill_name, skill_value, bonus, penalty)
    
    def _parse_times(self, token: str) -> int | None:
        """解析判定次数标记，如 t3, t5"""
        match = re.match(r"^t(\d+)$", token.lower())
        if not match:
            return None
        count = int(match.group(1))
        return min(max(count, 1), 10)  # 限制 1-10 次
    
    def _parse_ra_compact(self, args: str) -> tuple[int, int, int, str, int | None]:
        """
        解析紧凑格式的 ra 参数，如 r2侦查50, p1聆听, 侦查50, 侦查, p1t3手枪
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
        """解析奖励骰/惩罚骰标记"""
        match = re.match(r"^([rp])(\d*)$", token.lower())
        if not match:
            return None
        bp_type, count_str = match.groups()
        count = int(count_str) if count_str else 1
        count = min(count, 10)
        if bp_type == "r":
            return (count, 0)
        else:
            return (0, count)
    
    async def _do_check(
        self, skill_name: str, target: int, 
        bonus: int = 0, penalty: int = 0
    ) -> CommandResult:
        """执行检定"""
        rule_settings = await self.ctx.db.get_user_rule(self.ctx.user_id)
        rule = get_rule(
            rule_settings["rule"],
            rule_settings["critical"],
            rule_settings["fumble"]
        )
        
        # 使用奖励骰/惩罚骰
        if bonus > 0 or penalty > 0:
            roll_result = DiceRoller.roll_d100_with_bonus(bonus, penalty)
            roll = roll_result.final
            roll_detail = str(roll_result)
        else:
            roll = DiceRoller.roll_d100()
            roll_detail = f"D100={roll}"
        
        result = rule.check(roll, target)
        
        return CommandResult.text(f"**{skill_name}** 检定 ({rule.name})\n{roll_detail}\n{result}")
    
    async def _do_multi_check(
        self, skill_name: str, target: int,
        bonus: int = 0, penalty: int = 0, times: int = 1
    ) -> CommandResult:
        """执行多次检定，每次都带上奖励骰/惩罚骰"""
        rule_settings = await self.ctx.db.get_user_rule(self.ctx.user_id)
        rule = get_rule(
            rule_settings["rule"],
            rule_settings["critical"],
            rule_settings["fumble"]
        )
        
        # 构建奖励骰/惩罚骰描述
        bp_desc = ""
        if bonus > 0:
            bp_desc = f" (奖励骰×{bonus})" if bonus > 1 else " (奖励骰)"
        elif penalty > 0:
            bp_desc = f" (惩罚骰×{penalty})" if penalty > 1 else " (惩罚骰)"
        
        lines = [f"**{skill_name}** 连续检定 ×{times}{bp_desc} ({rule.name})"]
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


@command("rc", compact=True)
class RollCheckCommand(BaseCommand):
    """指定值检定命令"""
    
    description = "指定值检定"
    usage = ".rc 侦查 60, .rc r2 侦查 60"
    
    async def execute(self, args: str) -> CommandResult:
        """指定值检定: .rc 侦查 60, .rc r2 侦查 60"""
        parts = args.split()
        if len(parts) < 2:
            return CommandResult.text("格式: .rc <技能名> <值> 或 .rc r2 <技能名> <值>")
        
        # 解析奖励骰/惩罚骰
        bonus, penalty = 0, 0
        bp_match = self._parse_bonus_penalty(parts[0])
        if bp_match:
            bonus, penalty = bp_match
            parts = parts[1:]
        
        if len(parts) < 2:
            return CommandResult.text("格式: .rc <技能名> <值>")
        
        skill_name = parts[0]
        try:
            skill_value = int(parts[1])
        except ValueError:
            return CommandResult.text("技能值必须是数字")
        
        return await self._do_check(skill_name, skill_value, bonus, penalty)
    
    def _parse_bonus_penalty(self, token: str) -> tuple[int, int] | None:
        """解析奖励骰/惩罚骰标记"""
        match = re.match(r"^([rp])(\d*)$", token.lower())
        if not match:
            return None
        bp_type, count_str = match.groups()
        count = int(count_str) if count_str else 1
        count = min(count, 10)
        if bp_type == "r":
            return (count, 0)
        else:
            return (0, count)
    
    async def _do_check(
        self, skill_name: str, target: int, 
        bonus: int = 0, penalty: int = 0
    ) -> CommandResult:
        """执行检定"""
        rule_settings = await self.ctx.db.get_user_rule(self.ctx.user_id)
        rule = get_rule(
            rule_settings["rule"],
            rule_settings["critical"],
            rule_settings["fumble"]
        )
        
        if bonus > 0 or penalty > 0:
            roll_result = DiceRoller.roll_d100_with_bonus(bonus, penalty)
            roll = roll_result.final
            roll_detail = str(roll_result)
        else:
            roll = DiceRoller.roll_d100()
            roll_detail = f"D100={roll}"
        
        result = rule.check(roll, target)
        
        return CommandResult.text(f"**{skill_name}** 检定 ({rule.name})\n{roll_detail}\n{result}")


@command("gun", compact=True)
class FullAutoGunCommand(BaseCommand):
    """全自动枪械连发判定命令"""
    
    description = "全自动枪械连发判定"
    usage = ".gun 步枪 r1 t7, .gun冲锋枪 t5, .gun步枪50 r1 t6"
    
    async def execute(self, args: str) -> CommandResult:
        """
        全自动枪械连发判定
        
        规则说明：
        - 第1次：正常判定 + 环境奖励骰
        - 第2次：连发惩罚骰1 + 环境奖励骰（抵消）
        - 第3次：连发惩罚骰2 + 环境奖励骰 = 实际惩罚骰1
        - 第4次：连发惩罚骰2（上限）+ 环境奖励骰 = 困难成功 + 惩罚骰1
        - 第5次：极难成功 + 惩罚骰1
        - 第6次：大成功 + 惩罚骰1
        - 第7次及以后：默认失败
        """
        args = args.strip()
        if not args:
            return CommandResult.text(
                "格式: .gun <技能名> [r奖励骰] t<连发次数>\n"
                "例如: .gun 步枪 r1 t7, .gun冲锋枪 t5, .gun步枪50 r1 t6"
            )
        
        # 解析参数
        env_bonus, env_penalty, times, skill_name, skill_value = self._parse_gun_args(args)
        
        if not skill_name:
            return CommandResult.text("请指定技能名称，如: .gun 步枪 r1 t5")
        
        if times < 1:
            return CommandResult.text("请指定连发次数，如: .gun 步枪 r1 t5")
        
        # 限制最大连发次数
        times = min(times, 10)
        
        # 如果没有指定值，从角色卡获取
        if skill_value is None:
            char = await self.ctx.char_manager.get_active(self.ctx.user_id)
            if not char:
                return CommandResult.text("请先导入角色卡或指定技能值，如: .gun步枪50 r1 t5")
            
            skill_value = char.get_skill(skill_name)
            if skill_value is None:
                return CommandResult.text(f"未找到技能: {skill_name}，可指定值: .gun{skill_name}50 r1 t5")
        
        return await self._do_full_auto_check(skill_name, skill_value, env_bonus, env_penalty, times)
    
    def _parse_gun_args(self, args: str) -> tuple[int, int, int, int, str, int | None]:
        """
        解析全自动枪械参数
        返回: (env_bonus, env_penalty, times, skill_name, skill_value or None)
        """
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
            
            # 解析连发次数 t3, t5, t7
            t_match = re.match(r"^t(\d+)$", part.lower())
            if t_match:
                times = int(t_match.group(1))
                continue
            
            remaining_parts.append(part)
        
        # 处理技能名和技能值
        if remaining_parts:
            skill_str = " ".join(remaining_parts)
            # 检查末尾是否有数字（技能值）
            end_num_match = re.search(r"(\d+)$", skill_str)
            if end_num_match:
                skill_value = int(end_num_match.group(1))
                skill_name = skill_str[:end_num_match.start()].strip()
            else:
                skill_name = skill_str.strip()
        
        # 如果没有空格分隔，尝试紧凑格式解析
        if not skill_name and not remaining_parts:
            # 从原始 args 中提取（去掉 r/p 和 t 参数后）
            compact_args = args
            # 移除 r/p 参数
            compact_args = re.sub(r"\b[rp]\d*\b", "", compact_args, flags=re.IGNORECASE)
            # 移除 t 参数
            compact_args = re.sub(r"\bt\d+\b", "", compact_args, flags=re.IGNORECASE)
            compact_args = compact_args.strip()
            
            if compact_args:
                end_num_match = re.search(r"(\d+)$", compact_args)
                if end_num_match:
                    skill_value = int(end_num_match.group(1))
                    skill_name = compact_args[:end_num_match.start()].strip()
                else:
                    skill_name = compact_args
        
        return (env_bonus, env_penalty, times, skill_name, skill_value)
    
    async def _do_full_auto_check(
        self, skill_name: str, target: int, env_bonus: int, env_penalty: int, times: int
    ) -> CommandResult:
        """执行全自动枪械连发判定"""
        from ...dice.rules import SuccessLevel
        
        rule_settings = await self.ctx.db.get_user_rule(self.ctx.user_id)
        rule = get_rule(
            rule_settings["rule"],
            rule_settings["critical"],
            rule_settings["fumble"]
        )
        
        # 每波弹幕的子弹数 = 技能值 / 10
        bullets_per_burst = target // 10
        
        # 构建标题
        env_desc_parts = []
        if env_bonus > 0:
            env_desc_parts.append(f"环境奖励骰×{env_bonus}")
        if env_penalty > 0:
            env_desc_parts.append(f"环境惩罚骰×{env_penalty}")
        env_desc = f" ({', '.join(env_desc_parts)})" if env_desc_parts else ""
        lines = [f"🔫 **{skill_name}** 全自动连发 ×{times}波{env_desc} ({rule.name})"]
        lines.append(f"基础目标值: {target} | 每波弹幕: {bullets_per_burst}发")
        lines.append("---")
        
        total_hits = 0
        total_penetrate = 0  # 贯穿子弹数
        total_normal = 0     # 普通命中数
        
        for i in range(times):
            burst_num = i + 1
            
            # 计算本波弹幕的参数
            burst_penalty, difficulty_level, is_auto_fail, half_only = self._calc_burst_params(burst_num)
            
            if is_auto_fail:
                lines.append(f"第{burst_num}波: ❌ 不命中 (连发上限)")
                continue
            
            # 计算实际奖励骰/惩罚骰（环境奖励骰 - 连发惩罚骰 - 环境惩罚骰）
            total_penalty = burst_penalty + env_penalty
            net_bonus = env_bonus - total_penalty
            actual_bonus = max(0, net_bonus)
            actual_penalty = max(0, -net_bonus)
            
            # 计算实际目标值（根据难度等级）
            if difficulty_level == 0:
                actual_target = target
                diff_desc = ""
            elif difficulty_level == 1:
                actual_target = target // 2
                diff_desc = "[困难] "
            elif difficulty_level == 2:
                actual_target = target // 5
                diff_desc = "[极难] "
            else:  # difficulty_level == 3
                actual_target = 1  # 只有大成功才算成功
                diff_desc = "[需大成功] "
            
            # 执行骰点
            if actual_bonus > 0 or actual_penalty > 0:
                roll_result = DiceRoller.roll_d100_with_bonus(actual_bonus, actual_penalty)
                roll = roll_result.final
                roll_detail = str(roll_result)
            else:
                roll = DiceRoller.roll_d100()
                roll_detail = f"D100={roll}"
            
            # 判定结果
            result = rule.check(roll, actual_target)
            
            # 对于需要大成功的情况，只有大成功才算成功
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
            penetrate = 0  # 贯穿数
            
            if not is_success:
                hits = 0
            elif half_only:
                # 第5-6波只能命中一半，且难度>=极难不能贯穿
                hits = bullets_per_burst // 2
                # difficulty_level >= 2 表示难度是极难或更高，不能贯穿
            elif result.level in (SuccessLevel.CRITICAL, SuccessLevel.EXTREME):
                # 极难成功及以上：全部命中
                hits = bullets_per_burst
                # 只有难度等级低于极难时才能贯穿
                if difficulty_level < 2:
                    # 前半数（至少1发）造成贯穿
                    penetrate = max(1, hits // 2)
            else:
                # 困难成功及以下：命中一半
                hits = bullets_per_burst // 2
            
            normal_hits = hits - penetrate  # 普通命中数
            total_hits += hits
            total_penetrate += penetrate
            total_normal += normal_hits
            
            # 构建本波弹幕的描述
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
    
    def _calc_burst_params(self, burst_num: int) -> tuple[int, int, bool, bool]:
        """
        计算第 N 波弹幕的参数
        返回: (burst_penalty, difficulty_level, is_auto_fail, half_only)
        - burst_penalty: 连发惩罚骰数量
        - difficulty_level: 难度等级 (0=普通, 1=困难, 2=极难, 3=大成功)
        - is_auto_fail: 是否自动失败（不命中）
        - half_only: 是否只能命中一半
        """
        if burst_num == 1:
            # 第1波：正常判定
            return (0, 0, False, False)
        elif burst_num == 2:
            # 第2波：连发惩罚骰1
            return (1, 0, False, False)
        elif burst_num == 3:
            # 第3波：连发惩罚骰2
            return (2, 0, False, False)
        elif burst_num == 4:
            # 第4波：连发惩罚骰2（上限），困难成功
            return (2, 1, False, False)
        elif burst_num == 5:
            # 第5波：极难成功，只能命中一半
            return (2, 2, False, True)
        elif burst_num == 6:
            # 第6波：需要大成功，只能命中一半
            return (2, 3, False, True)
        else:
            # 第7波及以后：不命中
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
