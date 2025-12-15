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
    
    def __init__(self, client, char_manager: CharacterManager, db):
        self.client = client
        self.char_manager = char_manager
        self.db = db
        self.check_manager = CheckManager()
        self.command_prefix = "."
    
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
        if not content.startswith(self.command_prefix):
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
            content[1:], author_id, target_id, author_name
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
        parts = cmd.split(maxsplit=1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        # 需要 channel_id 的命令
        if command == "check":
            return await self._cmd_kp_check(args, user_id, channel_id, user_name)
        
        handlers = {
            "r": self._cmd_roll,
            "rd": self._cmd_roll,  # .rd 也支持骰点
            "ra": self._cmd_roll_attribute,
            "rc": self._cmd_roll_check,
            "pc": self._cmd_character,
            "rule": self._cmd_rule,
            "help": self._cmd_help,
        }
        
        handler = handlers.get(command)
        if handler:
            result = await handler(args, user_id)
            return (result, False)
        return (None, False)
    
    async def _cmd_roll(self, args: str, user_id: str) -> str:
        """基础骰点: .r 1d100"""
        expr_str = args.strip() or "1d100"
        expr = DiceParser.parse(expr_str)
        
        if not expr:
            return f"无效的骰点表达式: {expr_str}"
        
        result = DiceRoller.roll(expr)
        return str(result)
    
    async def _cmd_roll_attribute(self, args: str, user_id: str) -> str:
        """技能检定: .ra 侦查"""
        skill_name = args.strip()
        if not skill_name:
            return "请指定技能名称，如: .ra 侦查"
        
        char = await self.char_manager.get_active(user_id)
        if not char:
            return "请先导入角色卡: .pc new {JSON}"
        
        skill_value = char.get_skill(skill_name)
        if skill_value is None:
            return f"未找到技能: {skill_name}"
        
        return await self._do_check(user_id, skill_name, skill_value)
    
    async def _cmd_roll_check(self, args: str, user_id: str) -> str:
        """指定值检定: .rc 侦查 60"""
        parts = args.split()
        if len(parts) < 2:
            return "格式: .rc <技能名> <值>"
        
        skill_name = parts[0]
        try:
            skill_value = int(parts[1])
        except ValueError:
            return "技能值必须是数字"
        
        return await self._do_check(user_id, skill_name, skill_value)
    
    async def _do_check(self, user_id: str, skill_name: str, target: int) -> str:
        """执行检定"""
        rule_settings = await self.db.get_user_rule(user_id)
        rule = get_rule(
            rule_settings["rule"],
            rule_settings["critical"],
            rule_settings["fumble"]
        )
        
        roll = DiceRoller.roll_d100()
        result = rule.check(roll, target)
        
        return f"**{skill_name}** 检定 ({rule.name})\n{result}"

    async def _cmd_character(self, args: str, user_id: str) -> str:
        """角色卡命令: .pc <子命令>"""
        parts = args.split(maxsplit=1)
        sub_cmd = parts[0].lower() if parts else "show"
        sub_args = parts[1] if len(parts) > 1 else ""
        
        if sub_cmd == "new":
            return await self._pc_new(sub_args, user_id)
        elif sub_cmd == "list":
            return await self._pc_list(user_id)
        elif sub_cmd == "switch":
            return await self._pc_switch(sub_args, user_id)
        elif sub_cmd == "show":
            return await self._pc_show(user_id)
        elif sub_cmd == "del":
            return await self._pc_delete(sub_args, user_id)
        else:
            return "未知子命令。可用: new, list, switch, show, del"
    
    async def _pc_new(self, json_str: str, user_id: str) -> str:
        """导入角色卡"""
        if not json_str:
            return "请提供角色卡 JSON 数据"
        
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
`.r / .rd <表达式>` - 骰点 (如 .rd 1d100, .r 3d6+5)
`.ra <技能名>` - 技能检定 (需要角色卡)
`.rc <技能名> <值>` - 指定值检定

**KP 命令**
`.check <技能名> [描述]` - 发起检定 (玩家点击按钮骰点)

**角色卡命令**
`.pc new <JSON>` - 导入角色卡
`.pc list` - 列出角色卡
`.pc switch <名称>` - 切换角色卡
`.pc show` - 显示当前角色
`.pc del <名称>` - 删除角色卡

**规则命令**
`.rule show` - 显示当前规则
`.rule coc6/coc7` - 切换规则
`.rule crit <值>` - 设置大成功阈值
`.rule fumble <值>` - 设置大失败阈值"""
