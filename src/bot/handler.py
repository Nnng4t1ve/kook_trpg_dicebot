"""消息处理器"""
import json
from typing import Optional, Tuple
from loguru import logger
from ..dice import DiceParser, DiceRoller, CheckResult
from ..dice.rules import get_rule
from ..character import CharacterManager, CharacterImporter, NPCManager, NPC_TEMPLATES
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
        self.npc_manager = NPCManager(db)
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
        elif action == "san_check":
            await self._handle_san_check_button(
                value, user_id, target_id, user_name
            )
        elif action == "create_character":
            await self._handle_create_character_button(user_id)
        elif action == "grow_character":
            await self._handle_grow_character_button(user_id, value)
        elif action == "opposed_check":
            await self._handle_opposed_check_button(value, user_id, target_id, user_name)
        elif action == "confirm_damage":
            await self._handle_damage_button(value, user_id, target_id, user_name)
        elif action == "con_check":
            await self._handle_con_check_button(value, user_id, target_id, user_name)
        elif action == "approve_character":
            await self._handle_approve_character_button(value, user_id, target_id, user_name)
        elif action == "reject_character":
            await self._handle_reject_character_button(value, user_id, target_id, user_name)

    async def _handle_san_check_button(
        self, value: dict, user_id: str, target_id: str, user_name: str
    ):
        """处理 SAN Check 按钮点击"""
        from ..data.madness import roll_temporary_madness
        
        check_id = value.get("check_id")
        success_expr = value.get("success_expr")
        fail_expr = value.get("fail_expr")
        
        check = self.check_manager.get_check(check_id)
        if not check:
            await self.client.send_message(
                target_id, f"(met){user_id}(met) 该检定已过期", msg_type=9
            )
            return
        
        # 检查是否已经检定过
        if self.check_manager.has_completed(check_id, user_id):
            await self.client.send_message(
                target_id, f"(met){user_id}(met) 你已经完成过这个 SAN Check 了", msg_type=9
            )
            return
        
        # 获取角色卡
        char = await self.char_manager.get_active(user_id)
        if not char:
            await self.client.send_message(
                target_id, 
                f"(met){user_id}(met) 请先导入角色卡: `.pc new {{JSON}}`", 
                msg_type=9
            )
            return
        
        current_san = char.san
        if current_san <= 0:
            await self.client.send_message(
                target_id, 
                f"(met){user_id}(met) **{char.name}** 的 SAN 值已经为 0，无法进行 SAN Check", 
                msg_type=9
            )
            return
        
        # 进行 SAN 检定 (d100 <= san 为成功)
        roll = DiceRoller.roll_d100()
        is_success = roll <= current_san
        
        # 计算损失
        loss_expr = success_expr if is_success else fail_expr
        loss = self._calc_san_loss(loss_expr)
        
        if loss is None:
            await self.client.send_message(
                target_id, f"(met){user_id}(met) 无法解析损失表达式: {loss_expr}", msg_type=9
            )
            return
        
        # 更新 SAN 值
        new_san = max(0, current_san - loss)
        char.san = new_san
        await self.char_manager.add(char)  # 保存更新
        
        # 标记完成
        self.check_manager.mark_completed(check_id, user_id)
        
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
        
        # 发送结果卡片
        card = CardBuilder.build_san_check_result_card(
            user_name=user_name,
            char_name=char.name,
            roll=roll,
            san=current_san,
            is_success=is_success,
            loss_expr=loss_expr,
            loss=loss,
            new_san=new_san,
            madness_info=lines[4:] if loss >= 5 or new_san == 0 else None
        )
        await self.client.send_message(target_id, card, msg_type=10)

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
        all_commands = ["r", "rd", "ra", "rc", "rule", "help", "check", "pc", "npc", "ad", "ri", "dmg", "hp", "mp", "san", "cc"]
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

        if command == "ad":
            return await self._cmd_opposed_check(args, user_id, channel_id, user_name)

        if command == "dmg":
            return await self._cmd_damage(args, user_id, channel_id, user_name)

        if command == "npc":
            return await self._cmd_npc(args, user_id, channel_id, user_name)

        # pc create 需要返回卡片
        if command == "pc":
            return await self._cmd_character(args, user_id)

        # 角色卡审核命令
        if command == "cc":
            return await self._cmd_character_review(args, user_id, channel_id, user_name)
        
        # 需要 channel_id 的命令
        if command == "ri":
            return await self._cmd_initiative(args, user_id, channel_id, user_name)

        handlers = {
            "r": self._cmd_roll,
            "rd": self._cmd_roll,  # .rd 也支持骰点
            "ra": self._cmd_roll_attribute,
            "rc": self._cmd_roll_check,
            "sc": self._cmd_san_check,
            "rule": self._cmd_rule,
            "set": self._cmd_set_rule,
            "help": self._cmd_help,
            "hp": self._cmd_hp,
            "mp": self._cmd_mp,
            "san": self._cmd_san,
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
            return await self._pc_grow(sub_args, user_id)  # 返回 (str, bool)
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

    async def _pc_grow(self, args: str, user_id: str) -> Tuple[str, bool]:
        """角色卡成长: .pc grow <角色名> <技能1> <技能2> ..."""
        if not self.web_app:
            return ("Web 服务未启用", False)

        parts = args.split()
        if len(parts) < 2:
            return ("格式: .pc grow <角色名> <技能1> <技能2> ...\n示例: .pc grow 张三 侦查 聆听 图书馆", False)

        char_name = parts[0]
        skill_names = parts[1:]

        # 检查角色是否存在
        char = await self.char_manager.get(user_id, char_name)
        if not char:
            return (f"未找到角色: {char_name}", False)

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
            return (f"角色 {char_name} 没有这些技能: {', '.join(skill_names)}", False)

        # 返回卡片消息
        card = CardBuilder.build_grow_character_card(char_name, valid_skills, user_id)
        return (card, True)

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

    async def _handle_grow_character_button(self, user_id: str, value: dict):
        """处理成长角色卡按钮点击 - 私聊发送链接"""
        if not self.web_app:
            await self.client.send_direct_message(user_id, "Web 服务未启用")
            return

        char_name = value.get("char_name")
        skills = value.get("skills", [])
        initiator_id = value.get("initiator_id")

        if not char_name or not skills:
            await self.client.send_direct_message(user_id, "参数错误")
            return

        # 验证是否是发起者
        if initiator_id and user_id != initiator_id:
            await self.client.send_direct_message(user_id, "只有发起者可以获取成长链接")
            return

        from ..config import settings

        token = self.web_app.generate_grow_token(user_id, char_name, skills)
        url = f"{settings.web_base_url}/grow/{token}"

        logger.info(f"生成角色成长链接: user={user_id}, char={char_name}, token={token}")

        skills_text = "、".join(skills)
        msg = f"📈 **{char_name}** 的技能成长链接\n\n{url}\n\n可成长技能: {skills_text}\n⏰ 链接有效期 10 分钟"
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
        
        return "可用命令: show, coc6, coc7, crit <值>, fumble <值>\n或使用 `.set 1/2/3` 快速切换预设规则"

    async def _cmd_set_rule(self, args: str, user_id: str) -> str:
        """快速切换预设规则: .set 1/2/3"""
        from ..dice.rules import RULE_PRESETS, get_preset_rule
        
        args = args.strip()
        
        # 无参数时显示所有预设
        if not args:
            lines = ["**可用规则预设**"]
            for preset_id, preset in RULE_PRESETS.items():
                lines.append(f"`.set {preset_id}` - {preset['name']}: {preset['desc']}")
            return "\n".join(lines)
        
        # 解析预设编号
        try:
            preset_id = int(args)
        except ValueError:
            return "请输入预设编号，如 `.set 1`\n使用 `.set` 查看所有预设"
        
        preset = get_preset_rule(preset_id)
        if not preset:
            return f"未知预设编号: {preset_id}\n使用 `.set` 查看所有预设"
        
        # 应用预设
        await self.db.set_user_rule(
            user_id,
            rule=preset["rule"],
            critical=preset["critical"],
            fumble=preset["fumble"]
        )
        
        return f"已切换到 **{preset['name']}**\n{preset['desc']}"
    
    async def _cmd_kp_check(
        self, args: str, user_id: str, channel_id: str, user_name: str
    ) -> Tuple[str, bool]:
        """KP 发起检定: .check 侦查 [描述] 或 .check sc1d3/1d10 [描述]"""
        import re
        
        parts = args.split(maxsplit=1)
        if not parts:
            return ("格式: `.check <技能名> [描述]`\n示例: `.check 侦查 仔细搜索房间`\n`.check sc0/1d6` - SAN Check", False)
        
        skill_name = parts[0]
        description = parts[1] if len(parts) > 1 else ""
        
        # 检测 SAN check 格式: sc0/1d6, sc1d3/1d10 等
        san_match = re.match(r"^sc(.+)/(.+)$", skill_name, re.IGNORECASE)
        if san_match:
            success_expr = san_match.group(1).strip()
            fail_expr = san_match.group(2).strip()
            
            # 创建 SAN check
            check = self.check_manager.create_check(
                skill_name=f"sc:{success_expr}/{fail_expr}",  # 特殊格式标记
                channel_id=channel_id,
                kp_id=user_id
            )
            
            # 构建 SAN check 卡片
            card = CardBuilder.build_san_check_card(
                check_id=check.check_id,
                success_expr=success_expr,
                fail_expr=fail_expr,
                description=description,
                kp_name=user_name
            )
            
            logger.info(f"KP {user_id} 发起 SAN Check: {success_expr}/{fail_expr}, check_id={check.check_id}")
            return (card, True)
        
        # 普通技能检定
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

    async def _cmd_opposed_check(
        self, args: str, user_id: str, channel_id: str, user_name: str
    ) -> Tuple[str, bool]:
        """对抗检定: .ad @用户 力量 或 .ad npc <npc名> 斗殴 闪避 r1 p1"""
        import re

        args = args.strip()
        if not args:
            return (
                "格式: `.ad @用户 <技能> [r/p] [r/p]`\n"
                "或: `.ad npc <NPC名> <技能> [r/p] [r/p]`\n"
                "示例: `.ad @张三 力量` 或 `.ad npc 守卫 斗殴 闪避 r1 p1`",
                False,
            )

        # 检查是否是 NPC 对抗: .ad npc <name> ...
        if args.lower().startswith("npc "):
            return await self._cmd_opposed_check_vs_npc(
                args[4:].strip(), user_id, channel_id, user_name
            )

        # 解析 @用户 (KOOK 格式: (met)用户ID(met))
        match = re.match(r"\(met\)(\d+)\(met\)\s*(.+)", args)
        if not match:
            return ("格式: `.ad @用户 <技能>` 或 `.ad npc <NPC名> <技能>`", False)

        target_id = match.group(1)
        rest_part = match.group(2).strip()

        if not rest_part:
            return ("请指定技能名称", False)

        if target_id == user_id:
            return ("不能和自己对抗", False)

        # 解析参数：技能1 [技能2] [r/p] [r/p]
        parts = rest_part.split()
        initiator_skill = None
        target_skill = None
        initiator_bonus, initiator_penalty = 0, 0
        target_bonus, target_penalty = 0, 0

        skills = []
        bp_list = []  # 奖励骰/惩罚骰列表

        for part in parts:
            bp = self._parse_bonus_penalty(part)
            if bp:
                bp_list.append(bp)
            else:
                skills.append(part)

        if len(skills) == 0:
            return ("请指定技能名称", False)
        elif len(skills) == 1:
            initiator_skill = skills[0]
            target_skill = skills[0]
        else:
            initiator_skill = skills[0]
            target_skill = skills[1]

        # 分配奖励骰/惩罚骰
        if len(bp_list) >= 1:
            initiator_bonus, initiator_penalty = bp_list[0]
        if len(bp_list) >= 2:
            target_bonus, target_penalty = bp_list[1]

        # 创建对抗检定
        check = self.check_manager.create_opposed_check(
            initiator_id=user_id,
            target_id=target_id,
            initiator_skill=initiator_skill,
            target_skill=target_skill,
            channel_id=channel_id,
            initiator_bonus=initiator_bonus,
            initiator_penalty=initiator_penalty,
            target_bonus=target_bonus,
            target_penalty=target_penalty,
        )

        # 构建卡片
        card = CardBuilder.build_opposed_check_card(
            check_id=check.check_id,
            initiator_name=user_name,
            target_id=target_id,
            initiator_skill=initiator_skill,
            target_skill=target_skill,
            initiator_bp=(initiator_bonus, initiator_penalty),
            target_bp=(target_bonus, target_penalty),
        )

        logger.info(
            f"对抗检定: {user_id}({initiator_skill}) vs {target_id}({target_skill})"
        )
        return (card, True)

    async def _cmd_opposed_check_vs_npc(
        self, args: str, user_id: str, channel_id: str, user_name: str
    ) -> Tuple[str, bool]:
        """玩家向 NPC 发起对抗: .ad npc <npc名> <技能1> [技能2] [r/p]"""
        parts = args.split()
        if not parts:
            return ("格式: `.ad npc <NPC名> <技能> [r/p]`", False)

        npc_name = parts[0]
        rest_parts = parts[1:]

        # 获取 NPC
        npc = await self.npc_manager.get(channel_id, npc_name)
        if not npc:
            return (f"未找到 NPC: {npc_name}", False)

        if not rest_parts:
            return ("请指定技能名称", False)

        # 解析技能和奖励骰/惩罚骰
        player_skill = None
        npc_skill = None
        player_bonus, player_penalty = 0, 0
        npc_bonus, npc_penalty = 0, 0

        skills = []
        bp_list = []

        for part in rest_parts:
            bp = self._parse_bonus_penalty(part)
            if bp:
                bp_list.append(bp)
            else:
                skills.append(part)

        if len(skills) == 0:
            return ("请指定技能名称", False)
        elif len(skills) == 1:
            player_skill = skills[0]
            npc_skill = skills[0]
        else:
            player_skill = skills[0]
            npc_skill = skills[1]

        # 分配奖励骰/惩罚骰 (第一个给玩家，第二个给 NPC)
        if len(bp_list) >= 1:
            player_bonus, player_penalty = bp_list[0]
        if len(bp_list) >= 2:
            npc_bonus, npc_penalty = bp_list[1]

        # 验证 NPC 有这个技能
        npc_skill_value = npc.get_skill(npc_skill)
        if npc_skill_value is None:
            return (f"NPC **{npc_name}** 没有技能: {npc_skill}", False)

        # 创建对抗检定 (玩家为发起者，NPC 为目标)
        check = self.check_manager.create_opposed_check(
            initiator_id=user_id,
            target_id=f"npc:{npc_name}:{channel_id}",
            initiator_skill=player_skill,
            target_skill=npc_skill,
            channel_id=channel_id,
            initiator_bonus=player_bonus,
            initiator_penalty=player_penalty,
            target_bonus=npc_bonus,
            target_penalty=npc_penalty,
        )

        # NPC 立即进行检定
        from ..dice.rules import SuccessLevel

        rule_settings = await self.db.get_user_rule(user_id)
        rule = get_rule(
            rule_settings["rule"], rule_settings["critical"], rule_settings["fumble"]
        )

        if npc_bonus > 0 or npc_penalty > 0:
            roll_result = DiceRoller.roll_d100_with_bonus(npc_bonus, npc_penalty)
            npc_roll = roll_result.final
        else:
            npc_roll = DiceRoller.roll_d100()

        npc_result = rule.check(npc_roll, npc_skill_value)

        level_values = {
            SuccessLevel.CRITICAL: 4,
            SuccessLevel.EXTREME: 3,
            SuccessLevel.HARD: 2,
            SuccessLevel.REGULAR: 1,
            SuccessLevel.FAILURE: 0,
            SuccessLevel.FUMBLE: 0,
        }
        npc_level = level_values[npc_result.level]

        # 保存 NPC 结果 (作为 target)
        self.check_manager.set_opposed_result(
            check.check_id,
            f"npc:{npc_name}:{channel_id}",
            npc_roll,
            npc_skill_value,
            npc_level,
        )

        # 构建卡片 (玩家点击按钮进行检定)
        card = CardBuilder.build_player_vs_npc_opposed_card(
            check_id=check.check_id,
            player_name=user_name,
            player_id=user_id,
            npc_name=npc_name,
            player_skill=player_skill,
            npc_skill=npc_skill,
            npc_roll=npc_roll,
            npc_target=npc_skill_value,
            npc_level=npc_result.level.value,
            player_bp=(player_bonus, player_penalty),
            npc_bp=(npc_bonus, npc_penalty),
        )

        logger.info(f"玩家对抗NPC: {user_id}({player_skill}) vs {npc_name}({npc_skill})")
        return (card, True)

    async def _handle_opposed_check_button(
        self, value: dict, user_id: str, channel_id: str, user_name: str
    ):
        """处理对抗检定按钮点击"""
        from ..dice.rules import SuccessLevel

        check_id = value.get("check_id")

        check = self.check_manager.get_opposed_check(check_id)
        if not check:
            await self.client.send_message(
                channel_id, f"(met){user_id}(met) 该对抗检定已过期", msg_type=9
            )
            return

        # 检查是否涉及 NPC
        npc_is_initiator = check.initiator_id.startswith("npc:")
        npc_is_target = check.target_id.startswith("npc:")

        # 验证是否是参与者
        if npc_is_initiator:
            # NPC 发起对抗：只有目标玩家可以点击
            if user_id != check.target_id:
                await self.client.send_message(
                    channel_id, f"(met){user_id}(met) 你不是这次对抗的参与者", msg_type=9
                )
                return
        elif npc_is_target:
            # 玩家向 NPC 发起对抗：只有发起者玩家可以点击
            if user_id != check.initiator_id:
                await self.client.send_message(
                    channel_id, f"(met){user_id}(met) 你不是这次对抗的参与者", msg_type=9
                )
                return
        else:
            # 普通玩家对抗
            if user_id not in (check.initiator_id, check.target_id):
                await self.client.send_message(
                    channel_id, f"(met){user_id}(met) 你不是这次对抗的参与者", msg_type=9
                )
                return

        # 检查是否已经检定过
        if user_id == check.initiator_id and check.initiator_level is not None:
            await self.client.send_message(
                channel_id, f"(met){user_id}(met) 你已经完成检定了", msg_type=9
            )
            return
        if user_id == check.target_id and check.target_level is not None:
            await self.client.send_message(
                channel_id, f"(met){user_id}(met) 你已经完成检定了", msg_type=9
            )
            return

        # 获取该用户对应的技能和奖励骰/惩罚骰
        skill_name = check.get_skill_for_user(user_id)
        bonus, penalty = check.get_bonus_penalty_for_user(user_id)

        # 获取技能值
        char = await self.char_manager.get_active(user_id)
        if not char:
            await self.client.send_message(
                channel_id, f"(met){user_id}(met) 请先导入角色卡", msg_type=9
            )
            return

        skill_value = char.get_skill(skill_name)
        if skill_value is None:
            await self.client.send_message(
                channel_id,
                f"(met){user_id}(met) 你的角色卡中没有 **{skill_name}** 技能/属性",
                msg_type=9,
            )
            return

        # 执行检定（带奖励骰/惩罚骰）
        rule_settings = await self.db.get_user_rule(user_id)
        rule = get_rule(
            rule_settings["rule"], rule_settings["critical"], rule_settings["fumble"]
        )

        if bonus > 0 or penalty > 0:
            roll_result = DiceRoller.roll_d100_with_bonus(bonus, penalty)
            roll = roll_result.final
        else:
            roll = DiceRoller.roll_d100()

        result = rule.check(roll, skill_value)

        # 成功等级转数值 (用于比较)
        level_values = {
            SuccessLevel.CRITICAL: 4,
            SuccessLevel.EXTREME: 3,
            SuccessLevel.HARD: 2,
            SuccessLevel.REGULAR: 1,
            SuccessLevel.FAILURE: 0,
            SuccessLevel.FUMBLE: 0,  # 大失败按失败计算
        }
        level_num = level_values[result.level]

        # 保存结果
        self.check_manager.set_opposed_result(
            check_id, user_id, roll, skill_value, level_num
        )

        # 发送个人结果
        await self.client.send_message(
            channel_id,
            f"(met){user_id}(met) **{skill_name}** D100={roll}/{skill_value} 【{result.level.value}】",
            msg_type=9,
        )

        # 检查是否双方都完成了
        check = self.check_manager.get_opposed_check(check_id)
        if check and check.is_complete():
            await self._send_opposed_result(check, channel_id)

    async def _send_opposed_result(self, check, channel_id: str):
        """发送对抗检定最终结果"""
        # 获取双方名字
        # 检查是否是 NPC (initiator_id 格式: "npc:名称:channel_id")
        if check.initiator_id.startswith("npc:"):
            parts = check.initiator_id.split(":", 2)
            init_name = parts[1] if len(parts) > 1 else "NPC"
        else:
            init_char = await self.char_manager.get_active(check.initiator_id)
            init_name = init_char.name if init_char else f"(met){check.initiator_id}(met)"

        # 检查目标是否是 NPC
        if check.target_id.startswith("npc:"):
            parts = check.target_id.split(":", 2)
            target_name = parts[1] if len(parts) > 1 else "NPC"
        else:
            target_char = await self.char_manager.get_active(check.target_id)
            target_name = (
                target_char.name if target_char else f"(met){check.target_id}(met)"
            )

        # 等级数值转文字
        level_names = {4: "大成功", 3: "极难成功", 2: "困难成功", 1: "成功", 0: "失败"}

        init_level_text = level_names.get(check.initiator_level, "失败")
        target_level_text = level_names.get(check.target_level, "失败")

        # 判断胜负
        if check.initiator_level > check.target_level:
            winner = "initiator"
        elif check.target_level > check.initiator_level:
            winner = "target"
        else:
            winner = "tie"

        # 技能名称显示
        if check.initiator_skill == check.target_skill:
            skill_display = check.initiator_skill
        else:
            skill_display = f"{check.initiator_skill} vs {check.target_skill}"

        # 构建结果卡片
        card = CardBuilder.build_opposed_result_card(
            initiator_name=init_name,
            target_name=target_name,
            skill_name=skill_display,
            initiator_roll=check.initiator_roll,
            initiator_target=check.initiator_target,
            initiator_level=init_level_text,
            target_roll=check.target_roll,
            target_target=check.target_target,
            target_level=target_level_text,
            winner=winner,
        )

        await self.client.send_message(channel_id, card, msg_type=10)

    async def _cmd_npc(
        self, args: str, user_id: str, channel_id: str, user_name: str
    ) -> Tuple[str, bool]:
        """NPC 命令: .npc create <name> <模板>, .npc <name> ra <技能>, .npc <name> ad @用户 <技能>"""
        import re

        args = args.strip()
        if not args:
            return (
                "**NPC 命令**\n"
                "`.npc create <名称> [模板]` - 创建 NPC (模板: 1=普通, 2=困难, 3=极难)\n"
                "`.npc <名称> ra <技能>` - NPC 技能检定\n"
                "`.npc <名称> ad @用户 <技能1> [技能2] [r/p]` - NPC 对抗检定\n"
                "`.npc list` - 列出当前频道 NPC\n"
                "`.npc del <名称>` - 删除 NPC\n"
                "`.npc <名称>` - 查看 NPC 属性",
                False,
            )

        parts = args.split(maxsplit=1)
        sub_cmd = parts[0].lower()
        sub_args = parts[1] if len(parts) > 1 else ""

        # .npc create <name> [template]
        if sub_cmd == "create":
            return await self._npc_create(sub_args, channel_id)

        # .npc list
        if sub_cmd == "list":
            return await self._npc_list(channel_id)

        # .npc del <name>
        if sub_cmd == "del":
            return await self._npc_delete(sub_args, channel_id)

        # 其他情况: .npc <name> [子命令]
        # 第一个参数是 NPC 名称
        npc_name = sub_cmd
        npc = await self.npc_manager.get(channel_id, npc_name)

        if not npc:
            return (f"未找到 NPC: {npc_name}\n使用 `.npc create {npc_name} [1/2/3]` 创建", False)

        if not sub_args:
            # .npc <name> - 显示 NPC 信息
            return self._npc_show(npc)

        # 解析子命令
        sub_parts = sub_args.split(maxsplit=1)
        npc_cmd = sub_parts[0].lower()
        npc_args = sub_parts[1] if len(sub_parts) > 1 else ""

        if npc_cmd == "ra":
            return await self._npc_ra(npc, npc_args, user_id)
        elif npc_cmd == "ad":
            return await self._npc_ad(npc, npc_args, channel_id, user_name)
        else:
            # 可能是紧凑格式: .npc name ra力量 -> sub_args = "ra力量"
            if sub_args.lower().startswith("ra"):
                skill_part = sub_args[2:]
                return await self._npc_ra(npc, skill_part, user_id)
            elif sub_args.lower().startswith("ad"):
                ad_part = sub_args[2:]
                return await self._npc_ad(npc, ad_part, channel_id, user_name)
            else:
                return (f"未知 NPC 子命令: {npc_cmd}\n可用: ra, ad", False)

    async def _npc_create(self, args: str, channel_id: str) -> Tuple[str, bool]:
        """创建 NPC"""
        parts = args.split()
        if not parts:
            return ("格式: `.npc create <名称> [模板]`\n模板: 1=普通, 2=困难, 3=极难", False)

        name = parts[0]
        template_id = 1
        if len(parts) > 1:
            try:
                template_id = int(parts[1])
            except ValueError:
                return ("模板必须是数字 (1/2/3)", False)

        if template_id not in NPC_TEMPLATES:
            return (f"无效模板: {template_id}\n可用: 1=普通, 2=困难, 3=极难", False)

        # 检查是否已存在
        existing = await self.npc_manager.get(channel_id, name)
        if existing:
            return (f"NPC **{name}** 已存在，请先删除或使用其他名称", False)

        npc = await self.npc_manager.create(channel_id, name, template_id)
        if not npc:
            return ("创建失败", False)

        template = NPC_TEMPLATES[template_id]
        attrs = " | ".join(f"{k}:{v}" for k, v in npc.attributes.items())
        skills = " | ".join(f"{k}:{v}" for k, v in npc.skills.items())

        return (
            f"✅ NPC **{name}** 创建成功 (模板: {template['name']})\n"
            f"属性: {attrs}\n"
            f"技能: {skills}",
            False,
        )

    async def _npc_list(self, channel_id: str) -> Tuple[str, bool]:
        """列出频道 NPC"""
        npcs = await self.npc_manager.list_all(channel_id)
        if not npcs:
            return ("当前频道没有 NPC", False)

        lines = ["**NPC 列表**"]
        for npc in npcs:
            attrs_brief = f"STR:{npc.attributes.get('STR', '?')} DEX:{npc.attributes.get('DEX', '?')}"
            lines.append(f"• {npc.name} ({attrs_brief})")
        return ("\n".join(lines), False)

    async def _npc_delete(self, args: str, channel_id: str) -> Tuple[str, bool]:
        """删除 NPC"""
        name = args.strip()
        if not name:
            return ("格式: `.npc del <名称>`", False)

        if await self.npc_manager.delete(channel_id, name):
            return (f"已删除 NPC: **{name}**", False)
        return (f"未找到 NPC: {name}", False)

    def _npc_show(self, npc) -> Tuple[str, bool]:
        """显示 NPC 信息"""
        attrs = " | ".join(f"{k}:{v}" for k, v in npc.attributes.items())
        skills = " | ".join(f"{k}:{v}" for k, v in npc.skills.items())
        return (
            f"**{npc.name}**\n"
            f"HP: {npc.hp}/{npc.max_hp} | MP: {npc.mp}/{npc.max_mp} | 体格: {npc.build} | DB: {npc.db}\n"
            f"属性: {attrs}\n"
            f"技能: {skills}",
            False,
        )

    async def _npc_ra(self, npc, args: str, user_id: str) -> Tuple[str, bool]:
        """NPC 技能检定: .npc <name> ra <技能> [r/p]"""
        args = args.strip()
        if not args:
            return ("格式: `.npc <名称> ra <技能>`", False)

        # 解析奖励骰/惩罚骰和技能
        bonus, penalty, skill_name, skill_value = self._parse_ra_compact(args)

        if not skill_name:
            return ("请指定技能名称", False)

        # 如果没有指定值，从 NPC 获取
        if skill_value is None:
            skill_value = npc.get_skill(skill_name)
            if skill_value is None:
                return (f"NPC **{npc.name}** 没有技能: {skill_name}", False)

        # 执行检定
        rule_settings = await self.db.get_user_rule(user_id)
        rule = get_rule(
            rule_settings["rule"],
            rule_settings["critical"],
            rule_settings["fumble"],
        )

        if bonus > 0 or penalty > 0:
            roll_result = DiceRoller.roll_d100_with_bonus(bonus, penalty)
            roll = roll_result.final
            roll_detail = str(roll_result)
        else:
            roll = DiceRoller.roll_d100()
            roll_detail = f"D100={roll}"

        result = rule.check(roll, skill_value)

        return (
            f"**{npc.name}** 的 **{skill_name}** 检定 ({rule.name})\n{roll_detail}/{skill_value}\n{result}",
            False,
        )

    async def _npc_ad(
        self, npc, args: str, channel_id: str, user_name: str
    ) -> Tuple[str, bool]:
        """NPC 对抗检定: .npc <name> ad @用户 <技能1> [技能2] [r/p]"""
        import re

        args = args.strip()
        if not args:
            return (
                "格式: `.npc <名称> ad @用户 <技能> [r/p]`\n"
                "示例: `.npc 守卫 ad @张三 斗殴 闪避 r1 p1`",
                False,
            )

        # 解析 @用户
        match = re.match(r"\(met\)(\d+)\(met\)\s*(.+)", args)
        if not match:
            return ("格式: `.npc <名称> ad @用户 <技能>`\n请 @ 一个用户", False)

        target_id = match.group(1)
        rest_part = match.group(2).strip()

        if not rest_part:
            return ("请指定技能名称", False)

        # 解析参数
        parts = rest_part.split()
        npc_skill = None
        target_skill = None
        npc_bonus, npc_penalty = 0, 0
        target_bonus, target_penalty = 0, 0

        skills = []
        bp_list = []

        for part in parts:
            bp = self._parse_bonus_penalty(part)
            if bp:
                bp_list.append(bp)
            else:
                skills.append(part)

        if len(skills) == 0:
            return ("请指定技能名称", False)
        elif len(skills) == 1:
            npc_skill = skills[0]
            target_skill = skills[0]
        else:
            npc_skill = skills[0]
            target_skill = skills[1]

        # 分配奖励骰/惩罚骰 (第一个给 NPC，第二个给目标)
        if len(bp_list) >= 1:
            npc_bonus, npc_penalty = bp_list[0]
        if len(bp_list) >= 2:
            target_bonus, target_penalty = bp_list[1]

        # 验证 NPC 有这个技能
        npc_skill_value = npc.get_skill(npc_skill)
        if npc_skill_value is None:
            return (f"NPC **{npc.name}** 没有技能: {npc_skill}", False)

        # 创建对抗检定 (NPC 作为发起者)
        check = self.check_manager.create_opposed_check(
            initiator_id=f"npc:{npc.name}:{channel_id}",
            target_id=target_id,
            initiator_skill=npc_skill,
            target_skill=target_skill,
            channel_id=channel_id,
            initiator_bonus=npc_bonus,
            initiator_penalty=npc_penalty,
            target_bonus=target_bonus,
            target_penalty=target_penalty,
        )

        # NPC 立即进行检定
        from ..dice.rules import SuccessLevel

        rule_settings = await self.db.get_user_rule(target_id)  # 使用目标的规则
        rule = get_rule(
            rule_settings["rule"], rule_settings["critical"], rule_settings["fumble"]
        )

        if npc_bonus > 0 or npc_penalty > 0:
            roll_result = DiceRoller.roll_d100_with_bonus(npc_bonus, npc_penalty)
            npc_roll = roll_result.final
        else:
            npc_roll = DiceRoller.roll_d100()

        npc_result = rule.check(npc_roll, npc_skill_value)

        level_values = {
            SuccessLevel.CRITICAL: 4,
            SuccessLevel.EXTREME: 3,
            SuccessLevel.HARD: 2,
            SuccessLevel.REGULAR: 1,
            SuccessLevel.FAILURE: 0,
            SuccessLevel.FUMBLE: 0,
        }
        npc_level = level_values[npc_result.level]

        # 保存 NPC 结果
        self.check_manager.set_opposed_result(
            check.check_id,
            f"npc:{npc.name}:{channel_id}",
            npc_roll,
            npc_skill_value,
            npc_level,
        )

        # 构建卡片 (显示 NPC 已完成检定)
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

        logger.info(
            f"NPC 对抗: {npc.name}({npc_skill}) vs {target_id}({target_skill})"
        )
        return (card, True)

    async def _cmd_initiative(
        self, args: str, user_id: str, channel_id: str, user_name: str
    ) -> Tuple[str, bool]:
        """先攻顺序: .ri @用户1 @用户2 npc 守卫 怪物"""
        import re

        args = args.strip()
        if not args:
            return (
                "格式: `.ri @用户1 @用户2 npc <NPC名1> <NPC名2> ...`\n"
                "示例: `.ri @张三 @李四 npc 守卫 怪物`\n"
                "根据 DEX 从大到小排序生成先攻顺序表",
                False,
            )

        # 解析参与者列表
        participants = []  # [(name, dex, type)]
        
        # 提取所有 @用户 (KOOK 格式: (met)用户ID(met))
        user_mentions = re.findall(r"\(met\)(\d+)\(met\)", args)
        
        # 移除 @用户 后剩余的部分用于解析 NPC
        remaining = re.sub(r"\(met\)\d+\(met\)", "", args).strip()
        
        # 处理玩家
        for mentioned_user_id in user_mentions:
            char = await self.char_manager.get_active(mentioned_user_id)
            if char:
                dex = char.get_skill("DEX") or char.attributes.get("DEX", 0)
                participants.append((char.name, dex, "player", mentioned_user_id))
            else:
                participants.append((f"(met){mentioned_user_id}(met)", 0, "player", mentioned_user_id))
        
        # 解析 NPC 名称
        # 格式: npc name1 name2 或直接 name1 name2 (如果前面有 npc 关键字)
        npc_names = []
        if remaining:
            # 检查是否以 npc 开头
            if remaining.lower().startswith("npc"):
                remaining = remaining[3:].strip()
            
            # 剩余部分按空格分割作为 NPC 名称
            if remaining:
                npc_names = remaining.split()
        
        # 处理 NPC
        for npc_name in npc_names:
            npc = await self.npc_manager.get(channel_id, npc_name)
            if npc:
                dex = npc.attributes.get("DEX", 0)
                participants.append((npc.name, dex, "npc", None))
            else:
                # NPC 不存在，提示
                participants.append((f"{npc_name} (未找到)", 0, "unknown", None))
        
        if not participants:
            return ("未找到任何参与者，请 @ 用户或指定 NPC 名称", False)
        
        # 按 DEX 从大到小排序
        participants.sort(key=lambda x: x[1], reverse=True)
        
        # 构建先攻顺序表
        card = CardBuilder.build_initiative_card(participants)
        return (card, True)

    async def _cmd_damage(
        self, args: str, user_id: str, channel_id: str, user_name: str
    ) -> Tuple[str, bool]:
        """
        伤害命令: .dmg @用户 <伤害表达式> 或 .dmg npc <名称> <伤害表达式>
        返回卡片，只有发起者能点击确认
        """
        import re

        args = args.strip()
        if not args:
            return (
                "**伤害命令**\n"
                "`.dmg @用户 <伤害>` - 对玩家造成伤害\n"
                "`.dmg npc <名称> <伤害>` - 对 NPC 造成伤害\n"
                "示例: `.dmg @张三 1d6+2`, `.dmg npc 守卫 2d6`",
                False,
            )

        # 检查是否是 NPC: .dmg npc <name> <damage>
        if args.lower().startswith("npc "):
            return await self._cmd_damage_npc(
                args[4:].strip(), user_id, channel_id, user_name
            )

        # 解析 @用户 (KOOK 格式: (met)用户ID(met))
        match = re.match(r"\(met\)(\d+)\(met\)\s*(.+)", args)
        if not match:
            return ("格式: `.dmg @用户 <伤害>` 或 `.dmg npc <名称> <伤害>`", False)

        target_id = match.group(1)
        damage_expr = match.group(2).strip()

        if not damage_expr:
            return ("请指定伤害值，如: `.dmg @用户 1d6+2`", False)

        # 验证伤害表达式
        normalized_expr = self._normalize_dice_expr(damage_expr)
        if not damage_expr.isdigit() and not DiceParser.parse(normalized_expr):
            return (f"无法解析伤害表达式: {damage_expr}", False)

        # 获取目标角色卡
        char = await self.char_manager.get_active(target_id)
        if not char:
            return (f"(met){target_id}(met) 没有激活的角色卡", False)

        # 创建伤害检定
        check = self.check_manager.create_damage_check(
            initiator_id=user_id,
            target_type="player",
            target_id=target_id,
            channel_id=channel_id,
            damage_expr=damage_expr,
        )

        # 构建卡片
        card = CardBuilder.build_damage_card(
            check_id=check.check_id,
            initiator_name=user_name,
            target_name=char.name,
            target_type="player",
            damage_expr=damage_expr,
            target_id=target_id,
        )

        logger.info(f"伤害检定: {user_id} -> {target_id}, expr={damage_expr}")
        return (card, True)

    async def _cmd_damage_npc(
        self, args: str, user_id: str, channel_id: str, user_name: str
    ) -> Tuple[str, bool]:
        """对 NPC 造成伤害，返回卡片"""
        parts = args.split(maxsplit=1)
        if len(parts) < 2:
            return ("格式: `.dmg npc <名称> <伤害>`\n示例: `.dmg npc 守卫 2d6`", False)

        npc_name = parts[0]
        damage_expr = parts[1].strip()

        # 获取 NPC
        npc = await self.npc_manager.get(channel_id, npc_name)
        if not npc:
            return (f"未找到 NPC: {npc_name}", False)

        # 验证伤害表达式
        normalized_expr = self._normalize_dice_expr(damage_expr)
        if not damage_expr.isdigit() and not DiceParser.parse(normalized_expr):
            return (f"无法解析伤害表达式: {damage_expr}", False)

        # 创建伤害检定
        check = self.check_manager.create_damage_check(
            initiator_id=user_id,
            target_type="npc",
            target_id=npc_name,
            channel_id=channel_id,
            damage_expr=damage_expr,
        )

        # 构建卡片
        card = CardBuilder.build_damage_card(
            check_id=check.check_id,
            initiator_name=user_name,
            target_name=npc.name,
            target_type="npc",
            damage_expr=damage_expr,
        )

        logger.info(f"NPC伤害检定: {user_id} -> {npc_name}, expr={damage_expr}")
        return (card, True)

    async def _handle_damage_button(
        self, value: dict, user_id: str, channel_id: str, user_name: str
    ):
        """处理伤害确认按钮点击"""
        from ..data.npc_status import get_hp_status, get_hp_bar

        check_id = value.get("check_id")

        check = self.check_manager.get_damage_check(check_id)
        if not check:
            await self.client.send_message(
                channel_id, f"(met){user_id}(met) 该伤害确认已过期", msg_type=9
            )
            return

        # 验证是否是发起者
        if user_id != check.initiator_id:
            await self.client.send_message(
                channel_id, f"(met){user_id}(met) 只有发起者可以确认伤害", msg_type=9
            )
            return

        # 计算伤害
        damage = self._calc_damage(check.damage_expr)
        if damage is None:
            await self.client.send_message(
                channel_id, f"无法解析伤害表达式: {check.damage_expr}", msg_type=9
            )
            return

        need_con_check = False
        target_name = ""
        max_hp = 0

        if check.target_type == "npc":
            # NPC 伤害
            npc = await self.npc_manager.get(check.channel_id, check.target_id)
            if not npc:
                await self.client.send_message(
                    channel_id, f"未找到 NPC: {check.target_id}", msg_type=9
                )
                return

            old_hp = npc.hp
            max_hp = npc.max_hp
            target_name = npc.name

            npc.hp = max(0, old_hp - damage)
            await self.db.save_npc(check.channel_id, npc)

            # 检查是否需要体质检定 (伤害 >= 最大HP的一半 且 受伤后HP不为0)
            if damage >= max_hp // 2 and npc.hp > 0:
                need_con_check = True

            status_level, status_desc = get_hp_status(npc.hp, npc.max_hp)
            hp_bar = get_hp_bar(npc.hp, npc.max_hp, hidden=True)

            card = CardBuilder.build_damage_result_card(
                target_name=npc.name,
                target_type="npc",
                damage_expr=check.damage_expr,
                damage=damage,
                new_hp=npc.hp,
                hp_bar=hp_bar,
                status_desc=status_desc,
            )
        else:
            # 玩家伤害
            char = await self.char_manager.get_active(check.target_id)
            if not char:
                await self.client.send_message(
                    channel_id, f"目标玩家没有激活的角色卡", msg_type=9
                )
                return

            old_hp = char.hp
            max_hp = char.max_hp
            target_name = char.name

            char.hp = max(0, old_hp - damage)
            await self.char_manager.add(char)

            # 检查是否需要体质检定 (伤害 >= 最大HP的一半 且 受伤后HP不为0)
            if damage >= max_hp // 2 and char.hp > 0:
                need_con_check = True

            status_level, status_desc = get_hp_status(char.hp, char.max_hp)
            hp_bar = get_hp_bar(char.hp, char.max_hp)

            card = CardBuilder.build_damage_result_card(
                target_name=char.name,
                target_type="player",
                damage_expr=check.damage_expr,
                damage=damage,
                old_hp=old_hp,
                new_hp=char.hp,
                max_hp=char.max_hp,
                hp_bar=hp_bar,
                status_level=status_level,
            )

        # 移除检定
        self.check_manager.remove_damage_check(check_id)

        # 发送结果卡片
        await self.client.send_message(channel_id, card, msg_type=10)

        # 如果需要体质检定
        if need_con_check:
            if check.target_type == "npc":
                # NPC 自动进行体质检定
                await self._do_npc_con_check(
                    npc, damage, channel_id
                )
            else:
                # 玩家需要点击卡片
                con_check = self.check_manager.create_con_check(
                    target_type="player",
                    target_id=check.target_id,
                    target_name=target_name,
                    channel_id=channel_id,
                    damage=damage,
                    max_hp=max_hp,
                )
                con_card = CardBuilder.build_con_check_card(
                    check_id=con_check.check_id,
                    target_name=target_name,
                    target_id=check.target_id,
                    damage=damage,
                    max_hp=max_hp,
                )
                await self.client.send_message(channel_id, con_card, msg_type=10)

    async def _do_npc_con_check(self, npc, damage: int, channel_id: str):
        """NPC 自动进行体质检定"""
        con_value = npc.attributes.get("CON", 50)
        roll = DiceRoller.roll_d100()
        is_success = roll <= con_value

        card = CardBuilder.build_con_check_result_card(
            target_name=npc.name,
            roll=roll,
            con_value=con_value,
            is_success=is_success,
            is_npc=True,
        )
        await self.client.send_message(channel_id, card, msg_type=10)

    async def _handle_con_check_button(
        self, value: dict, user_id: str, channel_id: str, user_name: str
    ):
        """处理体质检定按钮点击"""
        check_id = value.get("check_id")

        check = self.check_manager.get_con_check(check_id)
        if not check:
            await self.client.send_message(
                channel_id, f"(met){user_id}(met) 该体质检定已过期", msg_type=9
            )
            return

        # 验证是否是目标玩家
        if user_id != check.target_id:
            await self.client.send_message(
                channel_id, f"(met){user_id}(met) 只有 **{check.target_name}** 可以进行此检定", msg_type=9
            )
            return

        # 获取角色卡
        char = await self.char_manager.get_active(user_id)
        if not char:
            await self.client.send_message(
                channel_id, f"(met){user_id}(met) 没有激活的角色卡", msg_type=9
            )
            return

        # 获取体质值
        con_value = char.attributes.get("CON", 50)

        # 进行检定
        roll = DiceRoller.roll_d100()
        is_success = roll <= con_value

        # 移除检定
        self.check_manager.remove_con_check(check_id)

        # 发送结果卡片
        card = CardBuilder.build_con_check_result_card(
            target_name=char.name,
            roll=roll,
            con_value=con_value,
            is_success=is_success,
            is_npc=False,
        )
        await self.client.send_message(channel_id, card, msg_type=10)

    def _calc_damage(self, expr: str) -> int | None:
        """计算伤害值，支持数字或骰点表达式"""
        expr = expr.strip()

        # 纯数字
        if expr.isdigit():
            return int(expr)

        # 骰点表达式
        expr = self._normalize_dice_expr(expr)
        parsed = DiceParser.parse(expr)
        if parsed:
            result = DiceRoller.roll(parsed)
            return max(0, result.total)  # 伤害不能为负

        return None

    async def _cmd_hp(self, args: str, user_id: str) -> str:
        """HP 调整: .hp +5, .hp -3, .hp 10"""
        return await self._adjust_stat(args, user_id, "hp")

    async def _cmd_mp(self, args: str, user_id: str) -> str:
        """MP 调整: .mp +5, .mp -3, .mp 10"""
        return await self._adjust_stat(args, user_id, "mp")

    async def _cmd_san(self, args: str, user_id: str) -> str:
        """SAN 调整: .san +5, .san -3, .san 10"""
        return await self._adjust_stat(args, user_id, "san")

    async def _adjust_stat(self, args: str, user_id: str, stat_type: str) -> str:
        """通用属性调整方法"""
        args = args.strip()

        # 获取角色卡
        char = await self.char_manager.get_active(user_id)
        if not char:
            return "请先导入角色卡"

        # 无参数时显示当前值
        if not args:
            if stat_type == "hp":
                return f"**{char.name}** HP: {char.hp}/{char.max_hp}"
            elif stat_type == "mp":
                return f"**{char.name}** MP: {char.mp}/{char.max_mp}"
            else:  # san
                max_san = self._calc_max_san(char)
                return f"**{char.name}** SAN: {char.san}/{max_san}"

        # 解析调整值
        try:
            if args.startswith("+"):
                delta = int(args[1:])
            elif args.startswith("-"):
                delta = -int(args[1:])
            else:
                # 直接设置值
                new_value = int(args)
                return await self._set_stat(char, stat_type, new_value)
        except ValueError:
            return f"无效的数值: {args}"

        # 应用调整
        return await self._apply_stat_delta(char, stat_type, delta)

    async def _set_stat(self, char, stat_type: str, new_value: int) -> str:
        """直接设置属性值"""
        if stat_type == "hp":
            old_value = char.hp
            char.hp = max(0, min(new_value, char.max_hp))
            await self.char_manager.add(char)
            return f"**{char.name}** HP: {old_value} → **{char.hp}**/{char.max_hp}"
        elif stat_type == "mp":
            old_value = char.mp
            char.mp = max(0, min(new_value, char.max_mp))
            await self.char_manager.add(char)
            return f"**{char.name}** MP: {old_value} → **{char.mp}**/{char.max_mp}"
        else:  # san
            old_value = char.san
            max_san = self._calc_max_san(char)
            char.san = max(0, min(new_value, max_san))
            await self.char_manager.add(char)
            return f"**{char.name}** SAN: {old_value} → **{char.san}**/{max_san}"

    async def _apply_stat_delta(self, char, stat_type: str, delta: int) -> str:
        """应用属性变化"""
        if stat_type == "hp":
            old_value = char.hp
            char.hp = max(0, min(char.hp + delta, char.max_hp))
            await self.char_manager.add(char)
            sign = "+" if delta > 0 else ""
            return f"**{char.name}** HP: {old_value} {sign}{delta} → **{char.hp}**/{char.max_hp}"
        elif stat_type == "mp":
            old_value = char.mp
            char.mp = max(0, min(char.mp + delta, char.max_mp))
            await self.char_manager.add(char)
            sign = "+" if delta > 0 else ""
            return f"**{char.name}** MP: {old_value} {sign}{delta} → **{char.mp}**/{char.max_mp}"
        else:  # san
            old_value = char.san
            max_san = self._calc_max_san(char)
            char.san = max(0, min(char.san + delta, max_san))
            await self.char_manager.add(char)
            sign = "+" if delta > 0 else ""
            return f"**{char.name}** SAN: {old_value} {sign}{delta} → **{char.san}**/{max_san}"

    def _calc_max_san(self, char) -> int:
        """计算 SAN 上限: 99 - 克苏鲁神话技能"""
        cthulhu_mythos = char.skills.get("克苏鲁神话", 0)
        if cthulhu_mythos == 0:
            cthulhu_mythos = char.skills.get("CM", 0)
        return 99 - cthulhu_mythos

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
`.check sc<成功>/<失败>` - 发起 SAN Check (如 .check sc0/1d6)
`.ad @用户 <技能>` - 对抗检定 (如 .ad @张三 力量)
`.ad @用户 <我的技能> <对方技能>` - 不同技能对抗 (如 .ad @张三 斗殴 闪避)
`.ad npc <NPC名> <技能>` - 向 NPC 发起对抗 (如 .ad npc 守卫 斗殴)
`.dmg @用户 <伤害>` - 对玩家造成伤害 (如 .dmg @张三 1d6+2)
`.dmg npc <名称> <伤害>` - 对 NPC 造成伤害 (如 .dmg npc 守卫 2d6)
`.ri @用户1 @用户2 npc <NPC名>` - 先攻顺序表 (按 DEX 排序)

**NPC 命令**
`.npc create <名称> [模板]` - 创建 NPC (1=普通, 2=困难, 3=极难)
`.npc <名称> ra <技能>` - NPC 技能检定 (如 .npc 守卫 ra力量)
`.npc <名称> ad @用户 <技能>` - NPC 对抗检定 (如 .npc 守卫 ad @张三 斗殴 闪避 r1 p1)
`.npc list` - 列出当前频道 NPC
`.npc del <名称>` - 删除 NPC

**角色卡命令**
`.pc create` - 获取在线创建链接
`.pc new <JSON>` - 导入角色卡
`.pc grow <角色> <技能...>` - 技能成长 (如 .pc grow 张三 侦查 聆听)
`.pc list` - 列出角色卡
`.pc switch <名称>` - 切换角色卡
`.pc show` - 显示当前角色
`.pc del <名称>` - 删除角色卡

**属性调整**
`.hp` - 查看当前 HP
`.hp +5` / `.hp -3` - 增减 HP
`.hp 10` - 设置 HP 为指定值
`.mp` / `.mp +5` / `.mp -3` - MP 调整 (同上)
`.san` / `.san +5` / `.san -3` - SAN 调整 (上限=99-克苏鲁神话)

**规则命令**
`.set` - 查看所有预设规则
`.set 1` - COC7标准规则
`.set 2` - COC7村规 (技能≥50: 1-5大成功; <50: 仅1大成功)
`.set 3` - COC6标准规则
`.rule show` - 显示当前规则
`.rule crit <值>` - 设置大成功阈值
`.rule fumble <值>` - 设置大失败阈值"""

    async def _cmd_character_review(
        self, args: str, user_id: str, channel_id: str, user_name: str
    ) -> Tuple[str, bool]:
        """角色卡审核命令: .cc <角色名>"""
        import base64

        char_name = args.strip()
        if not char_name:
            return (
                "**角色卡审核命令**\n"
                "`.cc <角色名>` - 发起角色卡审核\n"
                "示例: `.cc 张三`\n\n"
                "请先在网页上创建角色卡并提交审核，然后使用此命令发起审核",
                False,
            )

        # 从数据库获取待审核数据
        review = await self.db.get_character_review(char_name)
        if not review:
            return (f"未找到待审核角色卡: {char_name}\n请先在网页上提交审核", False)

        # 验证是否是提交者
        if review["user_id"] != user_id:
            return ("只有提交者可以发起审核", False)

        # 检查是否已有图片 URL（避免重复上传）
        image_url = review.get("image_url")
        if not image_url:
            # 解码图片数据
            image_data = review["image_data"]
            if image_data and image_data.startswith("data:image/png;base64,"):
                image_data = image_data.split(",", 1)[1]

            if not image_data:
                return ("图片数据不存在", False)

            try:
                image_bytes = base64.b64decode(image_data)
            except Exception as e:
                logger.error(f"解码图片失败: {e}")
                return ("图片数据解析失败", False)

            # 上传图片到 KOOK
            image_url = await self.client.upload_asset(image_bytes, f"{char_name}.png")
            if not image_url:
                return ("图片上传失败", False)

            # 更新数据库中的图片 URL
            await self.db.update_review_image_url(char_name, image_url)
            logger.info(f"角色卡图片上传成功: {char_name} -> {image_url}")

        # 构建审核卡片
        card = CardBuilder.build_character_review_card(
            char_name=char_name,
            image_url=image_url,
            initiator_id=user_id,
            initiator_name=user_name,
        )

        return (card, True)

    async def _handle_approve_character_button(
        self, value: dict, user_id: str, channel_id: str, user_name: str
    ):
        """处理审核通过按钮点击"""
        char_name = value.get("char_name")
        initiator_id = value.get("initiator_id")

        if not char_name:
            await self.client.send_message(
                channel_id, f"(met){user_id}(met) 参数错误", msg_type=9
            )
            return

        # 从数据库获取待审核数据
        review = await self.db.get_character_review(char_name)
        if not review:
            await self.client.send_message(
                channel_id, f"(met){user_id}(met) 未找到待审核角色卡: {char_name}", msg_type=9
            )
            return

        # 设置为已审核通过
        await self.db.set_review_approved(char_name, True)

        # 发送审核结果卡片
        card = CardBuilder.build_review_result_card(
            char_name=char_name,
            approved=True,
            reviewer_name=user_name,
            initiator_id=initiator_id,
        )
        await self.client.send_message(channel_id, card, msg_type=10)

        logger.info(f"角色卡审核通过: {char_name} by {user_name}")

    async def _handle_reject_character_button(
        self, value: dict, user_id: str, channel_id: str, user_name: str
    ):
        """处理审核拒绝按钮点击"""
        char_name = value.get("char_name")
        initiator_id = value.get("initiator_id")

        if not char_name:
            await self.client.send_message(
                channel_id, f"(met){user_id}(met) 参数错误", msg_type=9
            )
            return

        # 从数据库删除待审核数据
        await self.db.delete_character_review(char_name)

        # 发送审核结果卡片
        card = CardBuilder.build_review_result_card(
            char_name=char_name,
            approved=False,
            reviewer_name=user_name,
            initiator_id=initiator_id,
        )
        await self.client.send_message(channel_id, card, msg_type=10)

        logger.info(f"角色卡审核拒绝: {char_name} by {user_name}")
