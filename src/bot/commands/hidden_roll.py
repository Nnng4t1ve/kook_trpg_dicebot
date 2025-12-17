"""暗骰命令 - 骰点结果私聊发送给发起者"""
import re
from .base import BaseCommand, CommandResult
from .registry import command
from ...dice import DiceParser, DiceRoller
from ...dice.rules import get_rule


@command("rhd", compact=True)
class HiddenRollCommand(BaseCommand):
    """暗骰命令 - 结果私聊发送"""
    
    description = "暗骰（结果私聊发送）"
    usage = ".rhd 1d100, .rhd100, .rhd6+d4+3"
    
    async def execute(self, args: str) -> CommandResult:
        """暗骰: .rhd 1d100, .rhd100, .rhd6+d4+3"""
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
            roll_text = str(result)
        else:
            # 普通骰点
            expr = DiceParser.parse(expr_str)
            if not expr:
                return CommandResult.text(f"无效的骰点表达式: {expr_str}")
            
            result = DiceRoller.roll(expr)
            roll_text = str(result)
        
        # 私聊发送结果
        private_msg = f"🎲 **暗骰结果**\n{roll_text}"
        await self.ctx.client.send_direct_message(self.ctx.user_id, private_msg, msg_type=9)
        
        # 频道提示（不显示结果）
        return CommandResult.text(f"🎲 **{self.ctx.user_name}** 进行了暗骰", quote=False)
    
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


@command("rha", compact=True)
class HiddenRollAttributeCommand(BaseCommand):
    """暗骰技能检定命令 - 结果私聊发送"""
    
    description = "暗骰技能检定（结果私聊发送）"
    usage = ".rha侦查, .rha侦查50, .rhar2侦查, .rhap1聆听60"
    
    async def execute(self, args: str) -> CommandResult:
        """暗骰技能检定: .rha侦查, .rha侦查50, .rhar2侦查"""
        args = args.strip()
        if not args:
            return CommandResult.text("请指定技能名称，如: .rha侦查 或 .rha侦查50")
        
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
                return CommandResult.text("请指定技能名称，如: .rha侦查 或 .rhar2侦查")
            
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
            return CommandResult.text("请指定技能名称，如: .rha侦查 或 .rha侦查50")
        
        # 如果没有指定值，从角色卡获取
        if skill_value is None:
            char = await self.ctx.char_manager.get_active(self.ctx.user_id)
            if not char:
                return CommandResult.text("请先导入角色卡或指定技能值，如: .rha侦查50")
            
            skill_value = char.get_skill(skill_name)
            if skill_value is None:
                return CommandResult.text(f"未找到技能: {skill_name}，可指定值: .rha{skill_name}50")
        
        # 多次判定
        if times > 1:
            return await self._do_multi_check(skill_name, skill_value, bonus, penalty, times)
        
        return await self._do_check(skill_name, skill_value, bonus, penalty)
    
    def _parse_times(self, token: str) -> int | None:
        """解析判定次数标记"""
        match = re.match(r"^t(\d+)$", token.lower())
        if not match:
            return None
        count = int(match.group(1))
        return min(max(count, 1), 10)
    
    def _parse_ra_compact(self, args: str) -> tuple[int, int, int, str, int | None]:
        """解析紧凑格式的 ra 参数"""
        args = args.strip()
        bonus, penalty = 0, 0
        times = 1
        skill_value = None
        
        end_num_match = re.search(r"(\d+)$", args)
        if end_num_match:
            skill_value = int(end_num_match.group(1))
            args = args[: end_num_match.start()]
        
        while args:
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
            
            times_match = re.match(r"^t(\d+)", args, re.IGNORECASE)
            if times_match:
                times = int(times_match.group(1))
                times = min(max(times, 1), 10)
                args = args[times_match.end():]
                continue
            
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
        """执行检定并私聊发送结果"""
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
        
        # 私聊发送详细结果
        private_msg = f"🎲 **暗骰 {skill_name} 检定** ({rule.name})\n{roll_detail}/{target}\n{result}"
        await self.ctx.client.send_direct_message(self.ctx.user_id, private_msg, msg_type=9)
        
        # 频道提示
        return CommandResult.text(f"🎲 **{self.ctx.user_name}** 进行了 **{skill_name}** 暗骰检定", quote=False)
    
    async def _do_multi_check(
        self, skill_name: str, target: int,
        bonus: int = 0, penalty: int = 0, times: int = 1
    ) -> CommandResult:
        """执行多次检定并私聊发送结果"""
        rule_settings = await self.ctx.db.get_user_rule(self.ctx.user_id)
        rule = get_rule(
            rule_settings["rule"],
            rule_settings["critical"],
            rule_settings["fumble"]
        )
        
        bp_desc = ""
        if bonus > 0:
            bp_desc = f" (奖励骰×{bonus})" if bonus > 1 else " (奖励骰)"
        elif penalty > 0:
            bp_desc = f" (惩罚骰×{penalty})" if penalty > 1 else " (惩罚骰)"
        
        lines = [f"🎲 **暗骰 {skill_name} 连续检定** ×{times}{bp_desc} ({rule.name})"]
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
        return CommandResult.text(f"🎲 **{self.ctx.user_name}** 进行了 **{skill_name}** 暗骰连续检定 ×{times}", quote=False)
