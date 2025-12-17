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
