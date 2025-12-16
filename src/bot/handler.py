"""消息处理器"""
import json
from typing import Optional, Tuple
from loguru import logger
from ..dice import DiceParser, DiceRoller, CheckResult
from ..dice.rules import get_rule
from ..character import CharacterManager, CharacterImporter
from .card_builder import CardBuilder
from .check_manager import CheckManager


class MessageHandler:
    """消息处理器"""
    
    def __init__(self, client, char_manager: CharacterManager, db, web_app=None):
        self.client = client
        self.char_manager = char_manager
        self.db = db
        self.web_app = web_app
        self.check_manager = CheckManager()
        self.command_prefixes = (".", "。", "/")  # 支持多种前缀
    
    async def handle(self, event: dict):
        """处理消息事件"""
        msg_type = event.get("type")
        extra = event.get("extra", {})
        
        # 处理按钮点击事件 (系统消息 type=255)
        if msg_type == 255 and extra.get("type") == "message_btn_click":
            await self._handle_button_click(extra.get("body", {}))
            return
        
        # 只处理文字消息 (type 1 或 9)
        if msg_type not in (1, 9):
            return
        
        content = event.get("content", "").strip()
        
        # 检查是否以任意命令前缀开头
        prefix_used = None
        for prefix in self.command_prefixes:
            if content.startswith(prefix):
                prefix_used = prefix
                break
        
        if not prefix_used:
            return
        
        # 解析命令
        channel_type = event.get("channel_type")
        target_id = event.get("target_id")
        author_id = event.get("author_id")
        msg_id = event.get("msg_id")
        
        # 忽略机器人自己的消息
        author = extra.get("author", {})
        if author.get("bot"):
            return
        
        author_name = author.get("nickname") or author.get("username", "")
        logger.info(f"收到命令: {content} from {author_id}")
        
        # 执行命令 (可能返回卡片消息)
        response, is_card = await self._execute_command(
            content[len(prefix_used):], author_id, target_id, author_name
        )
        
        if response:
            msg_type = 10 if is_card else 9
            if channel_type == "GROUP":
                await self.client.send_message(
                    target_id, response, msg_type=msg_type, 
                    quote=msg_id if not is_card else None
                )
            else:
                await self.client.send_direct_message(author_id, response, msg_type=msg_type)

    async def _handle_button_click(self, body: dict):
        """处理按钮点击事件"""
        user_id = body.get("user_id")
        target_id = body.get("target_id")
        value_str = body.get("value", "{}")
        user_info = body.get("user_info", {})
        user_name = user_info.get("nickname") or user_info.get("username", "玩家")
        
        try:
            value = json.loads(value_str)
        except json.JSONDecodeError:
            return
        
        action = value.get("action")
        
        if action == "check":
            await self._handle_check_button(
                value, user_id, target_id, user_name
            )
        elif action == "create_character":
            await self._handle_create_character_button(user_id)
    
    async def _handle_check_button(
        self, value: dict, user_id: str, target_id: str, user_name: str
    ):
        """处理检定按钮点击"""
        check_id = value.get("check_id")
        skill_name = value.get("skill")
        
        check = self.check_manager.get_check(check_id)
        if not check:
            await self.client.send_message(
                target_id, f"(met){user_id}(met) 该检定已过期", msg_type=9
            )
            return
        
        # 检查是否已经检定过
        if self.check_manager.has_completed(check_id, user_id):
            await self.client.send_message(
                target_id, f"(met){user_id}(met) 你已经完成过这个检定了", msg_type=9
            )
            return
        
        # 获取技能值
        if check.target_value is not None:
            target = check.target_value
        else:
            char = await self.char_manager.get_active(user_id)
            if not char:
                await self.client.send_message(
                    target_id, 
                    f"(met){user_id}(met) 请先导入角色卡: `.pc new {{JSON}}`", 
                    msg_type=9
                )
                return
            
            skill_value = char.get_skill(skill_name)
            if skill_value is None:
                await self.client.send_message(
                    target_id, 
                    f"(met){user_id}(met) 你的角色卡中没有 **{skill_name}** 技能", 
                    msg_type=9
                )
                return
            target = skill_value
        
        # 执行检定
        rule_settings = await self.db.get_user_rule(user_id)
        rule = get_rule(
            rule_settings["rule"],
            rule_settings["critical"],
            rule_settings["fumble"]
        )
        
        roll = DiceRoller.roll_d100()
        result = rule.check(roll, target)
        
        # 标记完成
        self.check_manager.mark_completed(check_id, user_id)
        
        # 发送结果卡片
        card = CardBuilder.build_check_result_card(
            user_name, skill_name, roll, target, 
            result.level.value, result.is_success
        )
        await self.client.send_message(target_id, card, msg_type=10)

    async def _execute_command(
        self, cmd: str, user_id: str, channel_id: str = "", user_name: str = ""
    ) -> Tuple[Optional[str], bool]:
        """执行命令，返回 (响应内容, 是否为卡片消息)"""
        # 支持紧凑格式的命令列表（可以不带空格）
        # 按长度降序排列，优先匹配长的命令
        compact_commands = ["rd", "rc", "ra", "sc", "r"]
        
        # 先尝试空格分隔
        parts = cmd.split(maxsplit=1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        # 如果命令不在已知列表中，尝试紧凑格式解析
        all_commands = ["r", "rd", "ra", "rc", "rule", "help", "check", "pc"]
        if command not in all_commands:
            # 尝试匹配紧凑格式命令前缀
            cmd_lower = cmd.lower()
            for prefix in compact_commands:
                if cmd_lower.startswith(prefix) and len(cmd) > len(prefix):
                    # 检查前缀后面不是ASCII字母（避免 "rule" 被解析为 "r" + "ule"）
                    # 但允许中文、数字、rp（奖励骰/惩罚骰前缀）
                    next_char = cmd[len(prefix)]
                    is_ascii_letter = next_char.isascii() and next_char.isalpha()
                    if not is_ascii_letter or next_char.lower() in "rp":
                        command = prefix
                        args = cmd[len(prefix) :]
                        break
        
        # 需要 channel_id 的命令
        if command == "check":
            return await self._cmd_kp_check(args, user_id, channel_id, user_name)
        
        # pc create 需要返回卡片
        if command == "pc":
            return await self._cmd_character(args, user_id)
        
        handlers = {
            "r": self._cmd_roll,
            "rd": self._cmd_roll,  # .rd 也支持骰点
            "ra": self._cmd_roll_attribute,
            "rc": self._cmd_roll_check,
            "sc": self._cmd_san_check,
            "rule": self._cmd_rule,
            "help": self._cmd_help,
        }
        
        handler = handlers.get(command)
        if handler:
            result = await handler(args, user_id)
            return (result, False)
        return (None, False)
    
    async def _cmd_roll(self, args: str, user_id: str) -> str:
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
        # 例如 "100" -> "d100", "6+d4" -> "d6+d4"
        expr_str = self._normalize_dice_expr(expr_str)
        
        # 如果是 d100 且有奖励/惩罚骰，使用特殊处理
        if (bonus > 0 or penalty > 0) and expr_str.lower() in ("d100", "1d100"):
            result = DiceRoller.roll_d100_with_bonus(bonus, penalty)
            return str(result)
        
        # 普通骰点
        expr = DiceParser.parse(expr_str)
        if not expr:
            return f"无效的骰点表达式: {expr_str}"
        
        result = DiceRoller.roll(expr)
        return str(result)
    
    def _normalize_dice_expr(self, expr: str) -> str:
        """
        规范化骰点表达式，处理紧凑格式
        - "100" -> "d100"
        - "6+d4+3" -> "d6+d4+3"
        - "d6+4" -> "d6+4" (不变)
        """
        import re
        
        expr = expr.strip()
        if not expr:
            return "d100"
        
        # 如果整个表达式就是一个数字，当作 dN
        if expr.isdigit():
            return f"d{expr}"
        
        # 处理表达式开头：如果以数字开头且后面是 +/-，补上 d
        # 例如 "6+d4" -> "d6+d4"
        if expr[0].isdigit():
            match = re.match(r"^(\d+)([+-])", expr)
            if match:
                expr = f"d{expr}"
        
        return expr
    
    def _parse_bonus_penalty(self, token: str) -> tuple[int, int] | None:
        """解析奖励骰/惩罚骰标记，返回 (bonus, penalty) 或 None"""
        import re
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
    
    def _parse_ra_compact(self, args: str) -> tuple[int, int, str, int | None]:
        """
        解析紧凑格式的 ra 参数，如 r2侦查50, p1聆听, 侦查50, 侦查
        返回: (bonus, penalty, skill_name, skill_value or None)
        """
        import re

        args = args.strip()
        bonus, penalty = 0, 0
        skill_value = None
        skill_name = args

        # 先提取末尾的数字（技能值）
        end_num_match = re.search(r"(\d+)$", args)
        if end_num_match:
            skill_value = int(end_num_match.group(1))
            args = args[: end_num_match.start()]

        # 再检查开头的奖励骰/惩罚骰
        bp_match = re.match(r"^([rp])(\d*)", args, re.IGNORECASE)
        if bp_match:
            bp_type = bp_match.group(1).lower()
            bp_count = int(bp_match.group(2)) if bp_match.group(2) else 1
            bp_count = min(bp_count, 10)
            if bp_type == "r":
                bonus = bp_count
            else:
                penalty = bp_count
            skill_name = args[bp_match.end() :]
        else:
            skill_name = args

        return (bonus, penalty, skill_name.strip(), skill_value)

    async def _cmd_roll_attribute(self, args: str, user_id: str) -> str:
        """技能检定: .ra侦查, .ra侦查50, .rar2侦查, .rap1聆听60, 也支持空格分隔"""
        args = args.strip()
        if not args:
            return "请指定技能名称，如: .ra侦查 或 .ra侦查50"

        # 先尝试空格分隔的格式（向后兼容）
        parts = args.split()
        bonus, penalty = 0, 0
        skill_value = None
        skill_name = args

        if len(parts) >= 2:
            # 有空格，使用原来的解析逻辑
            # 检查第一个参数是否是奖励骰/惩罚骰
            bp_match = self._parse_bonus_penalty(parts[0])
            if bp_match:
                bonus, penalty = bp_match
                parts = parts[1:]

            if not parts:
                return "请指定技能名称，如: .ra侦查 或 .rar2侦查"

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
            bonus, penalty, skill_name, skill_value = self._parse_ra_compact(args)

        if not skill_name:
            return "请指定技能名称，如: .ra侦查 或 .ra侦查50"

        # 如果没有指定值，从角色卡获取
        if skill_value is None:
            char = await self.char_manager.get_active(user_id)
            if not char:
                return "请先导入角色卡或指定技能值，如: .ra侦查50"

            skill_value = char.get_skill(skill_name)
            if skill_value is None:
                return f"未找到技能: {skill_name}，可指定值: .ra{skill_name}50"

        return await self._do_check(user_id, skill_name, skill_value, bonus, penalty)
    
    async def _cmd_roll_check(self, args: str, user_id: str) -> str:
        """指定值检定: .rc 侦查 60, .rc r2 侦查 60"""
        parts = args.split()
        if len(parts) < 2:
            return "格式: .rc <技能名> <值> 或 .rc r2 <技能名> <值>"
        
        # 解析奖励骰/惩罚骰
        bonus, penalty = 0, 0
        bp_match = self._parse_bonus_penalty(parts[0])
        if bp_match:
            bonus, penalty = bp_match
            parts = parts[1:]
        
        if len(parts) < 2:
            return "格式: .rc <技能名> <值>"
        
        skill_name = parts[0]
        try:
            skill_value = int(parts[1])
        except ValueError:
            return "技能值必须是数字"
        
        return await self._do_check(user_id, skill_name, skill_value, bonus, penalty)
    
    async def _do_check(
        self, user_id: str, skill_name: str, target: int, 
        bonus: int = 0, penalty: int = 0
    ) -> str:
        """执行检定"""
        rule_settings = await self.db.get_user_rule(user_id)
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
        
        return f"**{skill_name}** 检定 ({rule.name})\n{roll_detail}\n{result}"

    async def _cmd_character(self, args: str, user_id: str) -> Tuple[str, bool]:
        """角色卡命令: .pc <子命令>"""
        parts = args.split(maxsplit=1)
        sub_cmd = parts[0].lower() if parts else "show"
        sub_args = parts[1] if len(parts) > 1 else ""
        
        if sub_cmd == "new":
            return (await self._pc_new(sub_args, user_id), False)
        elif sub_cmd == "create":
            return await self._pc_create_link(user_id)  # 返回卡片
        elif sub_cmd == "grow":
            return (await self._pc_grow(sub_args, user_id), False)
        elif sub_cmd == "list":
            return (await self._pc_list(user_id), False)
        elif sub_cmd == "switch":
            return (await self._pc_switch(sub_args, user_id), False)
        elif sub_cmd == "show":
            return (await self._pc_show(user_id), False)
        elif sub_cmd == "del":
            return (await self._pc_delete(sub_args, user_id), False)
        else:
            return ("未知子命令。可用: new, create, grow, list, switch, show, del", False)
    
    async def _pc_create_link(self, user_id: str) -> Tuple[str, bool]:
        """发送创建角色卡的交互卡片"""
        card = CardBuilder.build_create_character_card()
        return (card, True)

    async def _pc_grow(self, args: str, user_id: str) -> str:
        """角色卡成长: .pc grow <角色名> <技能1> <技能2> ..."""
        if not self.web_app:
            return "Web 服务未启用"

        parts = args.split()
        if len(parts) < 2:
            return "格式: .pc grow <角色名> <技能1> <技能2> ...\n示例: .pc grow 张三 侦查 聆听 图书馆"

        char_name = parts[0]
        skill_names = parts[1:]

        # 检查角色是否存在
        char = await self.char_manager.get(user_id, char_name)
        if not char:
            return f"未找到角色: {char_name}"

        # 验证技能是否存在于角色卡中
        valid_skills = []
        invalid_skills = []
        for skill in skill_names:
            if skill in char.skills:
                valid_skills.append(skill)
            else:
                # 尝试别名解析
                from ..dice.skill_alias import skill_resolver
                resolved = skill_resolver.resolve(skill)
                if resolved in char.skills:
                    valid_skills.append(resolved)
                else:
                    invalid_skills.append(skill)

        if not valid_skills:
            return f"角色 {char_name} 没有这些技能: {', '.join(skill_names)}"

        # 生成成长链接
        from ..config import settings
        token = self.web_app.generate_grow_token(user_id, char_name, valid_skills)
        url = f"{settings.web_base_url}/grow/{token}"

        msg_lines = [f"📈 **{char_name}** 的技能成长链接", "", url, ""]
        msg_lines.append(f"可成长技能: {', '.join(valid_skills)}")
        if invalid_skills:
            msg_lines.append(f"⚠️ 未找到: {', '.join(invalid_skills)}")
        msg_lines.append("\n⏰ 链接有效期 10 分钟")

        return "\n".join(msg_lines)

    async def _handle_create_character_button(self, user_id: str):
        """处理创建角色卡按钮点击 - 私聊发送链接"""
        if not self.web_app:
            await self.client.send_direct_message(user_id, "Web 服务未启用")
            return
        
        from ..config import settings
        token = self.web_app.generate_token(user_id)
        url = f"{settings.web_base_url}/create/{token}"
        
        logger.info(f"生成角色卡创建链接: user={user_id}, token={token}")
        
        msg = f"🎲 **你的专属角色卡创建链接**\n\n{url}\n\n⏰ 链接有效期 10 分钟，仅限本人使用"
        await self.client.send_direct_message(user_id, msg)
    
    async def _pc_new(self, json_str: str, user_id: str) -> str:
        """导入角色卡"""
        if not json_str:
            return "请提供角色卡 JSON 数据，或使用 `.pc create` 在线创建"
        
        char, error = CharacterImporter.from_json(json_str, user_id)
        if error:
            return f"导入失败: {error}"
        
        await self.char_manager.add(char)
        return f"角色卡 **{char.name}** 导入成功！"
    
    async def _pc_list(self, user_id: str) -> str:
        """列出角色卡"""
        chars = await self.char_manager.list_all(user_id)
        if not chars:
            return "暂无角色卡"
        
        active = await self.char_manager.get_active(user_id)
        active_name = active.name if active else None
        
        lines = ["**角色卡列表**"]
        for char in chars:
            marker = "→ " if char.name == active_name else "  "
            lines.append(f"{marker}{char.name}")
        return "\n".join(lines)
    
    async def _pc_switch(self, name: str, user_id: str) -> str:
        """切换角色卡"""
        name = name.strip()
        if not name:
            return "请指定角色名称"
        
        success = await self.char_manager.set_active(user_id, name)
        if success:
            return f"已切换到角色: **{name}**"
        return f"未找到角色: {name}"
    
    async def _pc_show(self, user_id: str) -> str:
        """显示当前角色"""
        char = await self.char_manager.get_active(user_id)
        if not char:
            return "当前没有选中的角色卡"
        
        lines = [f"**{char.name}**"]
        lines.append(f"HP: {char.hp}/{char.max_hp} | MP: {char.mp}/{char.max_mp} | SAN: {char.san}")
        
        if char.attributes:
            attrs = " | ".join(f"{k}:{v}" for k, v in char.attributes.items())
            lines.append(f"属性: {attrs}")
        
        if char.skills:
            skills = " | ".join(f"{k}:{v}" for k, v in list(char.skills.items())[:10])
            lines.append(f"技能: {skills}")
        
        return "\n".join(lines)
    
    async def _pc_delete(self, name: str, user_id: str) -> str:
        """删除角色卡"""
        name = name.strip()
        if not name:
            return "请指定角色名称"
        
        success = await self.char_manager.delete(user_id, name)
        if success:
            return f"已删除角色: **{name}**"
        return f"未找到角色: {name}"

    async def _cmd_san_check(self, args: str, user_id: str) -> str:
        """SAN Check: .sc 0/1d6, .sc1/1d10, .sc 1d4/2d6"""
        from ..data.madness import roll_temporary_madness

        args = args.strip()
        if not args:
            return "格式: .sc <成功损失>/<失败损失>\n示例: .sc 0/1d6, .sc 1/1d4+1, .sc 1d4/2d6"

        # 解析成功/失败损失表达式
        if "/" not in args:
            return "格式错误，需要用 / 分隔成功和失败的损失值\n示例: .sc 0/1d6"

        success_expr, fail_expr = args.split("/", 1)
        success_expr = success_expr.strip()
        fail_expr = fail_expr.strip()

        # 获取角色卡
        char = await self.char_manager.get_active(user_id)
        if not char:
            return "请先导入角色卡"

        current_san = char.san
        if current_san <= 0:
            return f"**{char.name}** 的 SAN 值已经为 0，无法进行 SAN Check"

        # 进行 SAN 检定 (d100 <= san 为成功)
        roll = DiceRoller.roll_d100()
        is_success = roll <= current_san

        # 计算损失
        loss_expr = success_expr if is_success else fail_expr
        loss = self._calc_san_loss(loss_expr)

        if loss is None:
            return f"无法解析损失表达式: {loss_expr}"

        # 更新 SAN 值
        new_san = max(0, current_san - loss)
        char.san = new_san
        await self.char_manager.add(char)  # 保存更新

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

        return "\n".join(lines)

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
            return max(0, result.total)  # 损失不能为负

        return None

    async def _cmd_rule(self, args: str, user_id: str) -> str:
        """规则命令: .rule <子命令>"""
        parts = args.split()
        sub_cmd = parts[0].lower() if parts else "show"
        
        if sub_cmd == "show":
            settings = await self.db.get_user_rule(user_id)
            return (f"当前规则: **{settings['rule'].upper()}**\n"
                   f"大成功: 1-{settings['critical']} | 大失败: {settings['fumble']}-100")
        
        elif sub_cmd in ("coc6", "coc7"):
            await self.db.set_user_rule(user_id, rule=sub_cmd)
            return f"已切换到 **{sub_cmd.upper()}** 规则"
        
        elif sub_cmd == "crit" and len(parts) > 1:
            try:
                value = int(parts[1])
                if 1 <= value <= 20:
                    await self.db.set_user_rule(user_id, critical=value)
                    return f"大成功阈值已设为: 1-{value}"
                return "大成功阈值范围: 1-20"
            except ValueError:
                return "请输入有效数字"
        
        elif sub_cmd == "fumble" and len(parts) > 1:
            try:
                value = int(parts[1])
                if 80 <= value <= 100:
                    await self.db.set_user_rule(user_id, fumble=value)
                    return f"大失败阈值已设为: {value}-100"
                return "大失败阈值范围: 80-100"
            except ValueError:
                return "请输入有效数字"
        
        return "可用命令: show, coc6, coc7, crit <值>, fumble <值>"
    
    async def _cmd_kp_check(
        self, args: str, user_id: str, channel_id: str, user_name: str
    ) -> Tuple[str, bool]:
        """KP 发起检定: .check 侦查 [描述]"""
        parts = args.split(maxsplit=1)
        if not parts:
            return ("格式: `.check <技能名> [描述]`\n示例: `.check 侦查 仔细搜索房间`", False)
        
        skill_name = parts[0]
        description = parts[1] if len(parts) > 1 else ""
        
        # 创建检定
        check = self.check_manager.create_check(
            skill_name=skill_name,
            channel_id=channel_id,
            kp_id=user_id
        )
        
        # 构建卡片
        card = CardBuilder.build_check_card(
            check_id=check.check_id,
            skill_name=skill_name,
            description=description,
            kp_name=user_name
        )
        
        logger.info(f"KP {user_id} 发起检定: {skill_name}, check_id={check.check_id}")
        return (card, True)
    
    async def _cmd_help(self, args: str, user_id: str) -> str:
        """帮助命令"""
        return """**COC Dice Bot 帮助**

**骰点命令**
`.r / .rd <表达式>` - 骰点 (如 .rd 1d100, .r 3d6+5, .r 1d6+1d4)
`.rd r2 d100` - 带2个奖励骰的d100
`.rd p1 d100` - 带1个惩罚骰的d100
`.ra <技能名>` - 技能检定 (使用角色卡数值)
`.ra <技能名> <值>` - 指定值检定 (如 .ra 侦查 50)
`.ra r2 侦查` - 带奖励骰的技能检定
`.ra p1 聆听 60` - 带惩罚骰的指定值检定
`.rc <技能名> <值>` - 指定值检定 (同 .ra 技能 值)
`.sc <成功>/<失败>` - SAN Check (如 .sc0/1d6, .sc1d4/2d6)

**KP 命令**
`.check <技能名> [描述]` - 发起检定 (玩家点击按钮骰点)

**角色卡命令**
`.pc create` - 获取在线创建链接
`.pc new <JSON>` - 导入角色卡
`.pc grow <角色> <技能...>` - 技能成长 (如 .pc grow 张三 侦查 聆听)
`.pc list` - 列出角色卡
`.pc switch <名称>` - 切换角色卡
`.pc show` - 显示当前角色
`.pc del <名称>` - 删除角色卡

**规则命令**
`.rule show` - 显示当前规则
`.rule coc6/coc7` - 切换规则
`.rule crit <值>` - 设置大成功阈值
`.rule fumble <值>` - 设置大失败阈值"""
