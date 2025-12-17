"""规则命令"""
from .base import BaseCommand, CommandResult
from .registry import command
from ...dice.rules import RULE_PRESETS, get_preset_rule


@command("rule")
class RuleCommand(BaseCommand):
    """规则命令"""
    
    description = "规则设置"
    usage = ".rule show, .rule coc6, .rule coc7, .rule crit <值>, .rule fumble <值>"
    
    async def execute(self, args: str) -> CommandResult:
        """规则命令: .rule <子命令>"""
        parts = args.split()
        sub_cmd = parts[0].lower() if parts else "show"
        
        if sub_cmd == "show":
            settings = await self.ctx.db.get_user_rule(self.ctx.user_id)
            return CommandResult.text(
                f"当前规则: **{settings['rule'].upper()}**\n"
                f"大成功: 1-{settings['critical']} | 大失败: {settings['fumble']}-100"
            )
        
        elif sub_cmd in ("coc6", "coc7"):
            await self.ctx.db.set_user_rule(self.ctx.user_id, rule=sub_cmd)
            return CommandResult.text(f"已切换到 **{sub_cmd.upper()}** 规则")
        
        elif sub_cmd == "crit" and len(parts) > 1:
            try:
                value = int(parts[1])
                if 1 <= value <= 20:
                    await self.ctx.db.set_user_rule(self.ctx.user_id, critical=value)
                    return CommandResult.text(f"大成功阈值已设为: 1-{value}")
                return CommandResult.text("大成功阈值范围: 1-20")
            except ValueError:
                return CommandResult.text("请输入有效数字")
        
        elif sub_cmd == "fumble" and len(parts) > 1:
            try:
                value = int(parts[1])
                if 80 <= value <= 100:
                    await self.ctx.db.set_user_rule(self.ctx.user_id, fumble=value)
                    return CommandResult.text(f"大失败阈值已设为: {value}-100")
                return CommandResult.text("大失败阈值范围: 80-100")
            except ValueError:
                return CommandResult.text("请输入有效数字")
        
        return CommandResult.text(
            "可用命令: show, coc6, coc7, crit <值>, fumble <值>\n"
            "或使用 `.set 1/2/3` 快速切换预设规则"
        )


@command("set")
class SetRuleCommand(BaseCommand):
    """快速切换预设规则命令"""
    
    description = "快速切换预设规则"
    usage = ".set 1/2/3"
    
    async def execute(self, args: str) -> CommandResult:
        """快速切换预设规则: .set 1/2/3"""
        args = args.strip()
        
        # 无参数时显示所有预设
        if not args:
            lines = ["**可用规则预设**"]
            for preset_id, preset in RULE_PRESETS.items():
                lines.append(f"`.set {preset_id}` - {preset['name']}: {preset['desc']}")
            return CommandResult.text("\n".join(lines))
        
        # 解析预设编号
        try:
            preset_id = int(args)
        except ValueError:
            return CommandResult.text("请输入预设编号，如 `.set 1`\n使用 `.set` 查看所有预设")
        
        preset = get_preset_rule(preset_id)
        if not preset:
            return CommandResult.text(f"未知预设编号: {preset_id}\n使用 `.set` 查看所有预设")
        
        # 应用预设
        await self.ctx.db.set_user_rule(
            self.ctx.user_id,
            rule=preset["rule"],
            critical=preset["critical"],
            fumble=preset["fumble"]
        )
        
        return CommandResult.text(f"已切换到 **{preset['name']}**\n{preset['desc']}")
