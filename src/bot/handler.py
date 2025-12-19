"""消息处理器 - 使用命令注册器重构版"""
import json
from typing import Optional, Tuple
from loguru import logger
from ..dice import DiceParser, DiceRoller
from ..dice.rules import get_rule, SuccessLevel
from ..character import CharacterManager, NPCManager
from .card_builder import CardBuilder
from .check_manager import CheckManager
from .commands import get_registry, CommandContext, CommandResult


class MessageHandler:
    """消息处理器"""
    
    def __init__(self, client, char_manager: CharacterManager, db, web_app=None):
        self.client = client
        self.char_manager = char_manager
        self.db = db
        self.web_app = web_app
        self.check_manager = CheckManager()
        self.npc_manager = NPCManager(db)
        self.command_prefixes = (".", "。", "/")
        self.registry = get_registry()
    
    async def handle(self, event: dict):
        """处理消息事件"""
        msg_type = event.get("type")
        extra = event.get("extra", {})
        
        # 调试：记录所有消息类型和内容（生产环境设置日志级别为 INFO 可跳过）
        if logger.level("DEBUG").no <= logger._core.min_level:
            author_id = event.get("author_id")
            content = event.get("content", "")[:100]  # 只取前100字符
            logger.debug(f"EVENT | type={msg_type} | user={author_id} | content={content}")
        
        # 处理按钮点击事件 (系统消息 type=255)
        if msg_type == 255 and extra.get("type") == "message_btn_click":
            await self._handle_button_click(extra.get("body", {}))
            return
        
        # 处理文字消息 (type 1, 9) 和卡片消息 (type 10，用户发送的图片)
        if msg_type not in (1, 9, 10):
            return
        
        content = event.get("content", "").strip()
        
        # 卡片消息 (type=10) - KOOK 把用户发送的图片作为卡片消息发送
        if msg_type == 10:
            from .commands.notebook import _user_active_notebook
            
            author_id = event.get("author_id")
            target_id = event.get("target_id")
            channel_type = event.get("channel_type")
            
            # 忽略机器人自己的消息
            author = extra.get("author", {})
            if author.get("bot"):
                return
            
            # 从卡片中提取图片和文字
            image_url, card_text = self._extract_image_and_text_from_card(content)
            if not image_url:
                return
            
            # 检查文字中是否包含 .note img 命令
            cmd_text = card_text.strip() if card_text else ""
            for prefix in self.command_prefixes:
                if cmd_text.startswith(prefix):
                    cmd_str = cmd_text[len(prefix):]
                    parts = cmd_str.split(maxsplit=2)
                    if len(parts) >= 2 and parts[0].lower() == "note" and parts[1].lower() == "img":
                        # 找到 .note img 命令，直接保存图片
                        image_name = parts[2].strip() if len(parts) > 2 else "未命名图片"
                        
                        notebook_name = _user_active_notebook.get(author_id)
                        if not notebook_name:
                            msg = "请先创建或切换记事本: `.note c <名称>` 或 `.note s <名称>`"
                            if channel_type == "GROUP":
                                await self.client.send_message(target_id, msg, msg_type=9)
                            else:
                                await self.client.send_direct_message(author_id, msg, msg_type=9)
                            return
                        
                        notebook = await self.db.notebooks.find_by_name(notebook_name)
                        if not notebook:
                            msg = f"记事本 **{notebook_name}** 不存在"
                            if channel_type == "GROUP":
                                await self.client.send_message(target_id, msg, msg_type=9)
                            else:
                                await self.client.send_direct_message(author_id, msg, msg_type=9)
                            return
                        
                        # 保存图片到记事本
                        await self.db.notebook_entries.add_entry(
                            notebook.id, f"[图片] {image_name}", author_id, image_url=image_url
                        )
                        
                        msg = f"🖼️ 图片 **{image_name}** 已记录到 **{notebook_name}**"
                        logger.info(f"IMG_SAVE | user={author_id} | notebook={notebook_name} | name={image_name}")
                        if channel_type == "GROUP":
                            await self.client.send_message(target_id, msg, msg_type=9)
                        else:
                            await self.client.send_direct_message(author_id, msg, msg_type=9)
                        return
            return
        
        # 解析基本信息
        channel_type = event.get("channel_type")
        target_id = event.get("target_id")
        author_id = event.get("author_id")
        msg_id = event.get("msg_id")
        
        # 忽略机器人自己的消息（Bot响应会在发送后单独记录）
        author = extra.get("author", {})
        is_bot = author.get("bot", False)
        if is_bot:
            return
        
        author_name = author.get("nickname") or author.get("username", "")
        
        # 检查是否以任意命令前缀开头
        prefix_used = None
        for prefix in self.command_prefixes:
            if content.startswith(prefix):
                prefix_used = prefix
                break
        
        # 判断是否为指令
        is_command = prefix_used is not None
        
        # 记录用户消息到日志（如果在记录范围内）
        await self._maybe_log_message(target_id, author_id, author_name, content, is_bot=False, if_cmd=is_command)
        
        # 检查是否有等待推送的状态
        from .commands.push import is_pending_push, clear_pending_push, build_push_card
        if channel_type == "GROUP" and is_pending_push(author_id, target_id):
            # 清除等待状态
            clear_pending_push(author_id, target_id)
            
            # 处理推送
            await self._handle_push_message(content, author_id, author_name, target_id, msg_id)
            return
        
        if not prefix_used:
            return
        
        # 提取附件（图片等）- KOOK API 中 attachments 是 Map 而不是数组
        attachments_raw = extra.get("attachments")
        attachments = []
        if attachments_raw:
            if isinstance(attachments_raw, dict):
                # 单个附件（Map格式）
                attachments = [attachments_raw]
            elif isinstance(attachments_raw, list):
                # 多个附件（数组格式）
                attachments = attachments_raw
        
        # 创建命令上下文
        ctx = CommandContext(
            user_id=author_id,
            user_name=author_name,
            channel_id=target_id,
            channel_type=channel_type,
            msg_id=msg_id,
            client=self.client,
            char_manager=self.char_manager,
            npc_manager=self.npc_manager,
            check_manager=self.check_manager,
            db=self.db,
            web_app=self.web_app,
            attachments=attachments,
        )
        
        # 执行命令
        cmd_str = content[len(prefix_used):]
        result = await self.registry.execute(cmd_str, ctx)
        
        if result and result.content:
            msg_type = 10 if result.is_card else 9
            quote = msg_id if result.quote and not result.is_card else None
            
            if channel_type == "GROUP":
                await self.client.send_message(
                    target_id, result.content, msg_type=msg_type, quote=quote
                )
                # 记录Bot响应到日志（Bot响应是指令的结果，标记为指令相关）
                await self._maybe_log_message(
                    target_id, "bot", "Bot", result.content, is_bot=True, if_cmd=True
                )
            else:
                await self.client.send_direct_message(author_id, result.content, msg_type=msg_type)

    async def _handle_push_message(
        self, content: str, author_id: str, author_name: str, channel_id: str, msg_id: str
    ):
        """处理推送置顶消息"""
        from .commands.push import build_push_card
        
        # 构建卡片
        card = build_push_card(content, author_name)
        
        # 发送卡片消息
        resp = await self.client.send_message(channel_id, card, msg_type=10)
        
        if resp.get("code") != 0:
            logger.error(f"PUSH_SEND_ERR | user={author_id} | resp={resp}")
            await self.client.send_message(channel_id, "❌ 发送卡片失败", msg_type=9)
            return
        
        # 获取新消息的 ID
        new_msg_id = resp.get("data", {}).get("msg_id")
        if not new_msg_id:
            logger.error(f"PUSH_NO_MSG_ID | user={author_id} | resp={resp}")
            return
        
        # 置顶新消息
        pin_success = await self.client.pin_message(new_msg_id, channel_id)
        if not pin_success:
            logger.warning(f"PUSH_PIN_FAIL | user={author_id} | msg_id={new_msg_id}")
            await self.client.send_message(channel_id, "⚠️ 卡片已发送，但置顶失败（可能缺少管理消息权限）", msg_type=9)
        
        # 删除用户原消息
        delete_success = await self.client.delete_message(msg_id)
        if not delete_success:
            logger.warning(f"PUSH_DEL_FAIL | user={author_id} | msg_id={msg_id}")
        
        logger.info(f"PUSH_OK | user={author_id} | channel={channel_id} | pin={pin_success} | del={delete_success}")

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
            logger.warning(f"BTN_ERR | user={user_id} | invalid JSON: {value_str[:50]}")
            return
        
        action = value.get("action")
        logger.info(f"BTN | user={user_id}({user_name}) | channel={target_id} | action={action}")
        
        if action == "check":
            await self._handle_check_button(value, user_id, target_id, user_name)
        elif action == "san_check":
            await self._handle_san_check_button(value, user_id, target_id, user_name)
        elif action == "create_character":
            await self._handle_create_character_button(user_id, value)
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
        elif action == "confirm_create_character":
            await self._handle_confirm_create_character_button(value, user_id, target_id, user_name)
        elif action == "notebook_page":
            await self._handle_notebook_page_button(value, user_id, target_id)
        elif action == "schedule_vote":
            await self._handle_schedule_vote_button(value, user_id, target_id, user_name)
        elif action == "log_page":
            await self._handle_log_page_button(value, user_id, target_id)

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
            await self.client.send_message(target_id, f"(met){user_id}(met) 该检定已过期", msg_type=9)
            return
        
        if self.check_manager.has_completed(check_id, user_id):
            await self.client.send_message(target_id, f"(met){user_id}(met) 你已经完成过这个 SAN Check 了", msg_type=9)
            return
        
        char = await self.char_manager.get_active(user_id)
        if not char:
            await self.client.send_message(target_id, f"(met){user_id}(met) 请先导入角色卡: `.pc new {{JSON}}`", msg_type=9)
            return
        
        current_san = char.san
        if current_san <= 0:
            await self.client.send_message(target_id, f"(met){user_id}(met) **{char.name}** 的 SAN 值已经为 0，无法进行 SAN Check", msg_type=9)
            return
        
        roll = DiceRoller.roll_d100()
        is_success = roll <= current_san
        
        loss_expr = success_expr if is_success else fail_expr
        loss = self._calc_san_loss(loss_expr)
        
        if loss is None:
            await self.client.send_message(target_id, f"(met){user_id}(met) 无法解析损失表达式: {loss_expr}", msg_type=9)
            return
        
        new_san = max(0, current_san - loss)
        char.san = new_san
        await self.char_manager.add(char)
        
        self.check_manager.mark_completed(check_id, user_id)
        
        result_text = "成功" if is_success else "失败"
        lines = [
            f"**{char.name}** 的 SAN Check",
            f"D100={roll}/{current_san} [{result_text}]",
            f"损失: {loss_expr} = {loss}",
            f"SAN: {current_san} → **{new_san}**",
        ]
        
        if loss >= 5:
            madness = roll_temporary_madness()
            lines.extend([
                "",
                f"⚠️ **触发临时疯狂！** (单次损失≥5)",
                f"🎲 症状骰点: 1D10={madness['roll']}",
                f"**{madness['name']}** - 持续 {madness['duration']}",
                f"_{madness['description']}_"
            ])
        
        if new_san == 0:
            lines.extend(["", "💀 **SAN 值归零，陷入永久疯狂！**"])
        
        card = CardBuilder.build_san_check_result_card(
            user_name=user_name, char_name=char.name, roll=roll, san=current_san,
            is_success=is_success, loss_expr=loss_expr, loss=loss, new_san=new_san,
            madness_info=lines[4:] if loss >= 5 or new_san == 0 else None
        )
        await self.client.send_message(target_id, card, msg_type=10)
        # 记录 SAN Check 结果到日志
        await self._maybe_log_message(target_id, "bot", "Bot", card, is_bot=True, if_cmd=True)

    async def _handle_check_button(
        self, value: dict, user_id: str, target_id: str, user_name: str
    ):
        """处理检定按钮点击"""
        check_id = value.get("check_id")
        skill_name = value.get("skill")
        
        check = self.check_manager.get_check(check_id)
        if not check:
            await self.client.send_message(target_id, f"(met){user_id}(met) 该检定已过期", msg_type=9)
            return
        
        if self.check_manager.has_completed(check_id, user_id):
            await self.client.send_message(target_id, f"(met){user_id}(met) 你已经完成过这个检定了", msg_type=9)
            return
        
        if check.target_value is not None:
            target = check.target_value
        else:
            char = await self.char_manager.get_active(user_id)
            if not char:
                await self.client.send_message(target_id, f"(met){user_id}(met) 请先导入角色卡: `.pc new {{JSON}}`", msg_type=9)
                return
            
            skill_value = char.get_skill(skill_name)
            if skill_value is None:
                await self.client.send_message(target_id, f"(met){user_id}(met) 你的角色卡中没有 **{skill_name}** 技能", msg_type=9)
                return
            target = skill_value
        
        rule_settings = await self.db.get_user_rule(user_id)
        rule = get_rule(rule_settings["rule"], rule_settings["critical"], rule_settings["fumble"])
        
        roll = DiceRoller.roll_d100()
        result = rule.check(roll, target)
        
        self.check_manager.mark_completed(check_id, user_id)
        
        card = CardBuilder.build_check_result_card(
            user_name, skill_name, roll, target, result.level.value, result.is_success
        )
        await self.client.send_message(target_id, card, msg_type=10)
        # 记录检定结果到日志
        await self._maybe_log_message(target_id, "bot", "Bot", card, is_bot=True, if_cmd=True)

    async def _handle_create_character_button(self, user_id: str, value: dict = None):
        """处理创建角色卡按钮点击"""
        if not self.web_app:
            await self.client.send_direct_message(user_id, "Web 服务未启用")
            return
        
        from ..config import settings
        
        # 获取技能上限参数
        skill_limit = value.get("skill_limit") if value else None
        occ_limit = value.get("occ_limit") if value else None
        non_occ_limit = value.get("non_occ_limit") if value else None
        
        token = self.web_app.generate_token(user_id, skill_limit, occ_limit, non_occ_limit)
        url = f"{settings.web_base_url}/create/{token}"
        
        logger.info(f"生成角色卡创建链接: user={user_id}, token={token}, limits={skill_limit}/{occ_limit}/{non_occ_limit}")
        
        card = CardBuilder.build_create_link_card(url, skill_limit, occ_limit, non_occ_limit)
        result = await self.client.send_direct_message(user_id, card, msg_type=10)
        logger.info(f"发送创建链接私聊结果: user={user_id}, result={result}")

    async def _handle_grow_character_button(self, user_id: str, value: dict):
        """处理成长角色卡按钮点击"""
        if not self.web_app:
            await self.client.send_direct_message(user_id, "Web 服务未启用")
            return

        char_name = value.get("char_name")
        skills = value.get("skills", [])
        initiator_id = value.get("initiator_id")

        if not char_name or not skills:
            await self.client.send_direct_message(user_id, "参数错误")
            return

        if initiator_id and user_id != initiator_id:
            await self.client.send_direct_message(user_id, "只有发起者可以获取成长链接")
            return

        from ..config import settings
        token = self.web_app.generate_grow_token(user_id, char_name, skills)
        url = f"{settings.web_base_url}/grow/{token}"

        logger.info(f"生成角色成长链接: user={user_id}, char={char_name}, token={token}")

        card = CardBuilder.build_grow_link_card(char_name, skills, url)
        result = await self.client.send_direct_message(user_id, card, msg_type=10)
        logger.info(f"发送成长链接私聊结果: user={user_id}, result={result}")

    async def _handle_opposed_check_button(
        self, value: dict, user_id: str, channel_id: str, user_name: str
    ):
        """处理对抗检定按钮点击"""
        check_id = value.get("check_id")

        check = self.check_manager.get_opposed_check(check_id)
        if not check:
            await self.client.send_message(channel_id, f"(met){user_id}(met) 该对抗检定已过期", msg_type=9)
            return

        npc_is_initiator = check.initiator_id.startswith("npc:")
        npc_is_target = check.target_id.startswith("npc:")

        if npc_is_initiator:
            if user_id != check.target_id:
                await self.client.send_message(channel_id, f"(met){user_id}(met) 你不是这次对抗的参与者", msg_type=9)
                return
        elif npc_is_target:
            if user_id != check.initiator_id:
                await self.client.send_message(channel_id, f"(met){user_id}(met) 你不是这次对抗的参与者", msg_type=9)
                return
        else:
            if user_id not in (check.initiator_id, check.target_id):
                await self.client.send_message(channel_id, f"(met){user_id}(met) 你不是这次对抗的参与者", msg_type=9)
                return

        if user_id == check.initiator_id and check.initiator_level is not None:
            await self.client.send_message(channel_id, f"(met){user_id}(met) 你已经完成检定了", msg_type=9)
            return
        if user_id == check.target_id and check.target_level is not None:
            await self.client.send_message(channel_id, f"(met){user_id}(met) 你已经完成检定了", msg_type=9)
            return

        skill_name = check.get_skill_for_user(user_id)
        bonus, penalty = check.get_bonus_penalty_for_user(user_id)

        char = await self.char_manager.get_active(user_id)
        if not char:
            await self.client.send_message(channel_id, f"(met){user_id}(met) 请先导入角色卡", msg_type=9)
            return

        skill_value = char.get_skill(skill_name)
        if skill_value is None:
            await self.client.send_message(channel_id, f"(met){user_id}(met) 你的角色卡中没有 **{skill_name}** 技能/属性", msg_type=9)
            return

        rule_settings = await self.db.get_user_rule(user_id)
        rule = get_rule(rule_settings["rule"], rule_settings["critical"], rule_settings["fumble"])

        if bonus > 0 or penalty > 0:
            roll_result = DiceRoller.roll_d100_with_bonus(bonus, penalty)
            roll = roll_result.final
        else:
            roll = DiceRoller.roll_d100()

        result = rule.check(roll, skill_value)

        level_values = {
            SuccessLevel.CRITICAL: 4, SuccessLevel.EXTREME: 3,
            SuccessLevel.HARD: 2, SuccessLevel.REGULAR: 1,
            SuccessLevel.FAILURE: 0, SuccessLevel.FUMBLE: -1,
        }
        level_num = level_values[result.level]

        self.check_manager.set_opposed_result(check_id, user_id, roll, skill_value, level_num)

        await self.client.send_message(
            channel_id, f"(met){user_id}(met) **{skill_name}** D100={roll}/{skill_value} 【{result.level.value}】", msg_type=9
        )

        check = self.check_manager.get_opposed_check(check_id)
        if check and check.is_complete():
            await self._send_opposed_result(check, channel_id)

    async def _send_opposed_result(self, check, channel_id: str):
        """发送对抗检定最终结果"""
        if check.initiator_id.startswith("npc:"):
            parts = check.initiator_id.split(":", 2)
            init_name = parts[1] if len(parts) > 1 else "NPC"
        else:
            init_char = await self.char_manager.get_active(check.initiator_id)
            init_name = init_char.name if init_char else f"(met){check.initiator_id}(met)"

        if check.target_id.startswith("npc:"):
            parts = check.target_id.split(":", 2)
            target_name = parts[1] if len(parts) > 1 else "NPC"
        else:
            target_char = await self.char_manager.get_active(check.target_id)
            target_name = target_char.name if target_char else f"(met){check.target_id}(met)"

        level_names = {4: "大成功", 3: "极难成功", 2: "困难成功", 1: "成功", 0: "失败", -1: "大失败"}
        init_level_text = level_names.get(check.initiator_level, "失败")
        target_level_text = level_names.get(check.target_level, "失败")

        if check.initiator_level > check.target_level:
            winner = "initiator"
        elif check.target_level > check.initiator_level:
            winner = "target"
        else:
            winner = "tie"

        if check.initiator_skill == check.target_skill:
            skill_display = check.initiator_skill
        else:
            skill_display = f"{check.initiator_skill} vs {check.target_skill}"

        card = CardBuilder.build_opposed_result_card(
            initiator_name=init_name, target_name=target_name, skill_name=skill_display,
            initiator_roll=check.initiator_roll, initiator_target=check.initiator_target,
            initiator_level=init_level_text, target_roll=check.target_roll,
            target_target=check.target_target, target_level=target_level_text, winner=winner,
        )
        await self.client.send_message(channel_id, card, msg_type=10)
        # 记录对抗检定结果到日志
        await self._maybe_log_message(channel_id, "bot", "Bot", card, is_bot=True, if_cmd=True)

    async def _handle_damage_button(
        self, value: dict, user_id: str, channel_id: str, user_name: str
    ):
        """处理伤害确认按钮点击"""
        from ..data.npc_status import get_hp_status, get_hp_bar

        check_id = value.get("check_id")
        check = self.check_manager.get_damage_check(check_id)
        if not check:
            await self.client.send_message(channel_id, f"(met){user_id}(met) 该伤害确认已过期", msg_type=9)
            return

        if user_id != check.initiator_id:
            await self.client.send_message(channel_id, f"(met){user_id}(met) 只有发起者可以确认伤害", msg_type=9)
            return

        damage = self._calc_damage(check.damage_expr)
        if damage is None:
            await self.client.send_message(channel_id, f"无法解析伤害表达式: {check.damage_expr}", msg_type=9)
            return

        need_con_check = False
        target_name = ""
        max_hp = 0

        if check.target_type == "npc":
            npc = await self.npc_manager.get(check.channel_id, check.target_id)
            if not npc:
                await self.client.send_message(channel_id, f"未找到 NPC: {check.target_id}", msg_type=9)
                return

            old_hp = npc.hp
            max_hp = npc.max_hp
            target_name = npc.name
            npc.hp = max(0, old_hp - damage)
            await self.db.save_npc(check.channel_id, npc)

            if damage >= max_hp // 2 and npc.hp > 0:
                need_con_check = True

            status_level, status_desc = get_hp_status(npc.hp, npc.max_hp)
            hp_bar = get_hp_bar(npc.hp, npc.max_hp, hidden=True)

            card = CardBuilder.build_damage_result_card(
                target_name=npc.name, target_type="npc", damage_expr=check.damage_expr,
                damage=damage, new_hp=npc.hp, hp_bar=hp_bar, status_desc=status_desc,
            )
        else:
            char = await self.char_manager.get_active(check.target_id)
            if not char:
                await self.client.send_message(channel_id, f"目标玩家没有激活的角色卡", msg_type=9)
                return

            old_hp = char.hp
            max_hp = char.max_hp
            target_name = char.name
            char.hp = max(0, old_hp - damage)
            await self.char_manager.add(char)

            if damage >= max_hp // 2 and char.hp > 0:
                need_con_check = True

            status_level, status_desc = get_hp_status(char.hp, char.max_hp)
            hp_bar = get_hp_bar(char.hp, char.max_hp)

            card = CardBuilder.build_damage_result_card(
                target_name=char.name, target_type="player", damage_expr=check.damage_expr,
                damage=damage, old_hp=old_hp, new_hp=char.hp, max_hp=char.max_hp,
                hp_bar=hp_bar, status_level=status_level,
            )

        self.check_manager.remove_damage_check(check_id)
        await self.client.send_message(channel_id, card, msg_type=10)
        # 记录伤害结果到日志
        await self._maybe_log_message(channel_id, "bot", "Bot", card, is_bot=True, if_cmd=True)

        if need_con_check:
            if check.target_type == "npc":
                await self._do_npc_con_check(npc, damage, channel_id)
            else:
                con_check = self.check_manager.create_con_check(
                    target_type="player", target_id=check.target_id, target_name=target_name,
                    channel_id=channel_id, damage=damage, max_hp=max_hp,
                )
                con_card = CardBuilder.build_con_check_card(
                    check_id=con_check.check_id, target_name=target_name,
                    target_id=check.target_id, damage=damage, max_hp=max_hp,
                )
                await self.client.send_message(channel_id, con_card, msg_type=10)

    async def _do_npc_con_check(self, npc, damage: int, channel_id: str):
        """NPC 自动进行体质检定"""
        con_value = npc.attributes.get("CON", 50)
        roll = DiceRoller.roll_d100()
        is_success = roll <= con_value

        card = CardBuilder.build_con_check_result_card(
            target_name=npc.name, roll=roll, con_value=con_value, is_success=is_success, is_npc=True,
        )
        await self.client.send_message(channel_id, card, msg_type=10)
        # 记录NPC体质检定结果到日志
        await self._maybe_log_message(channel_id, "bot", "Bot", card, is_bot=True, if_cmd=True)

    async def _handle_con_check_button(
        self, value: dict, user_id: str, channel_id: str, user_name: str
    ):
        """处理体质检定按钮点击"""
        check_id = value.get("check_id")
        check = self.check_manager.get_con_check(check_id)
        if not check:
            await self.client.send_message(channel_id, f"(met){user_id}(met) 该体质检定已过期", msg_type=9)
            return

        if user_id != check.target_id:
            await self.client.send_message(channel_id, f"(met){user_id}(met) 只有 **{check.target_name}** 可以进行此检定", msg_type=9)
            return

        char = await self.char_manager.get_active(user_id)
        if not char:
            await self.client.send_message(channel_id, f"(met){user_id}(met) 没有激活的角色卡", msg_type=9)
            return

        con_value = char.attributes.get("CON", 50)
        roll = DiceRoller.roll_d100()
        is_success = roll <= con_value

        self.check_manager.remove_con_check(check_id)

        card = CardBuilder.build_con_check_result_card(
            target_name=char.name, roll=roll, con_value=con_value, is_success=is_success, is_npc=False,
        )
        await self.client.send_message(channel_id, card, msg_type=10)
        # 记录体质检定结果到日志
        await self._maybe_log_message(channel_id, "bot", "Bot", card, is_bot=True, if_cmd=True)

    async def _handle_approve_character_button(
        self, value: dict, user_id: str, channel_id: str, user_name: str
    ):
        """处理审核通过按钮点击"""
        char_name = value.get("char_name")
        initiator_id = value.get("initiator_id")
        kp_id = value.get("kp_id")

        if not char_name:
            await self.client.send_message(channel_id, f"(met){user_id}(met) 参数错误", msg_type=9)
            return

        if kp_id and user_id != kp_id:
            await self.client.send_message(channel_id, f"(met){user_id}(met) 只有 (met){kp_id}(met) 可以审核此角色卡", msg_type=9)
            return

        review = await self.db.get_character_review(char_name)
        if not review:
            await self.client.send_message(channel_id, f"(met){user_id}(met) 该角色卡审核已处理或不存在", msg_type=9)
            return

        # approved 默认是 False，只有 True 才表示已审核通过
        if review.get("approved") is True:
            await self.client.send_message(channel_id, f"(met){user_id}(met) 该角色卡已经审核过了", msg_type=9)
            return

        # 标记审核通过
        await self.db.set_review_approved(char_name, True)

        # 发送审核结果到频道（@提交者）
        card = CardBuilder.build_review_result_card(
            char_name=char_name, approved=True, reviewer_name=user_name, initiator_id=initiator_id,
        )
        await self.client.send_message(channel_id, card, msg_type=10)
        
        logger.info(f"角色卡审核通过: {char_name} by {user_name}")

    async def _handle_reject_character_button(
        self, value: dict, user_id: str, channel_id: str, user_name: str
    ):
        """处理审核拒绝按钮点击"""
        char_name = value.get("char_name")
        initiator_id = value.get("initiator_id")
        kp_id = value.get("kp_id")

        if not char_name:
            await self.client.send_message(channel_id, f"(met){user_id}(met) 参数错误", msg_type=9)
            return

        if kp_id and user_id != kp_id:
            await self.client.send_message(channel_id, f"(met){user_id}(met) 只有 (met){kp_id}(met) 可以审核此角色卡", msg_type=9)
            return

        review = await self.db.get_character_review(char_name)
        if not review:
            await self.client.send_message(channel_id, f"(met){user_id}(met) 该角色卡审核已处理或不存在", msg_type=9)
            return

        # 删除审核记录（拒绝时直接删除）
        await self.db.delete_character_review(char_name)

        card = CardBuilder.build_review_result_card(
            char_name=char_name, approved=False, reviewer_name=user_name, initiator_id=initiator_id,
        )
        await self.client.send_message(channel_id, card, msg_type=10)
        logger.info(f"角色卡审核拒绝: {char_name} by {user_name}")

    def _calc_san_loss(self, expr: str) -> int | None:
        """计算 SAN 损失值"""
        expr = expr.strip()
        if expr.isdigit():
            return int(expr)
        
        expr = self._normalize_dice_expr(expr)
        parsed = DiceParser.parse(expr)
        if parsed:
            result = DiceRoller.roll(parsed)
            return max(0, result.total)
        return None

    def _calc_damage(self, expr: str) -> int | None:
        """计算伤害值"""
        expr = expr.strip()
        if expr.isdigit():
            return int(expr)
        
        expr = self._normalize_dice_expr(expr)
        parsed = DiceParser.parse(expr)
        if parsed:
            result = DiceRoller.roll(parsed)
            return max(0, result.total)
        return None

    def _normalize_dice_expr(self, expr: str) -> str:
        """规范化骰点表达式"""
        import re
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

    async def _handle_notebook_page_button(
        self, value: dict, user_id: str, channel_id: str
    ):
        """处理记事本分页按钮点击"""
        from .commands.notebook import _user_active_notebook
        from ..cards.builder import CardBuilder as CB
        from ..cards.components import CardComponents
        
        notebook_name = value.get("notebook")
        page = value.get("page", 1)
        
        if not notebook_name:
            await self.client.send_message(channel_id, f"(met){user_id}(met) 参数错误", msg_type=9)
            return
        
        # 更新用户当前记事本
        _user_active_notebook[user_id] = notebook_name
        
        notebook = await self.db.notebooks.find_by_name(notebook_name)
        if not notebook:
            await self.client.send_message(channel_id, f"(met){user_id}(met) 记事本不存在", msg_type=9)
            return
        
        entries, total = await self.db.notebook_entries.get_entries_page(
            notebook.id, page=page, page_size=10
        )
        
        if total == 0:
            await self.client.send_message(channel_id, f"📒 **{notebook_name}** 暂无记录", msg_type=9)
            return
        
        total_pages = (total + 9) // 10
        
        # 构建卡片
        builder = CB(theme="info")
        builder.header(f"📒 {notebook_name}")
        builder.divider()
        
        start_idx = (page - 1) * 10 + 1
        lines = []
        for i, entry in enumerate(entries):
            idx = start_idx + i
            content_preview = entry.content[:30] + "..." if len(entry.content) > 30 else entry.content
            lines.append(f"**{idx}.** {content_preview}")
        
        builder.section("\n".join(lines))
        builder.context(f"第 {page}/{total_pages} 页 · 共 {total} 条记录")
        
        if total_pages > 1:
            prev_page = total_pages if page == 1 else page - 1
            next_page = 1 if page == total_pages else page + 1
            
            buttons = [
                CardComponents.button(
                    "⬅️ 上一页",
                    {"action": "notebook_page", "notebook": notebook_name, "page": prev_page},
                    theme="secondary"
                ),
                CardComponents.button(
                    "下一页 ➡️",
                    {"action": "notebook_page", "notebook": notebook_name, "page": next_page},
                    theme="secondary"
                ),
            ]
            builder.buttons(*buttons)
        
        card = builder.build()
        await self.client.send_message(channel_id, card, msg_type=10)

    def _extract_image_and_text_from_card(self, content: str) -> tuple[str | None, str | None]:
        """从卡片消息中提取图片 URL 和文字内容"""
        image_url = None
        text_content = None
        
        try:
            cards = json.loads(content)
            if not isinstance(cards, list):
                return None, None
            
            for card in cards:
                modules = card.get("modules", [])
                for module in modules:
                    module_type = module.get("type")
                    
                    # container 类型包含图片
                    if module_type == "container":
                        elements = module.get("elements", [])
                        for elem in elements:
                            if elem.get("type") == "image" and not image_url:
                                image_url = elem.get("src")
                    
                    # image-group 类型也可能包含图片
                    elif module_type == "image-group":
                        elements = module.get("elements", [])
                        for elem in elements:
                            if elem.get("type") == "image" and not image_url:
                                image_url = elem.get("src")
                    
                    # section 类型包含文字
                    elif module_type == "section":
                        text_obj = module.get("text", {})
                        if text_obj.get("type") in ("plain-text", "kmarkdown"):
                            text_content = text_obj.get("content", "")
                    
                    # context 类型也可能包含文字
                    elif module_type == "context":
                        elements = module.get("elements", [])
                        for elem in elements:
                            if elem.get("type") in ("plain-text", "kmarkdown"):
                                text_content = elem.get("content", "")
                                
        except (json.JSONDecodeError, TypeError, KeyError):
            pass
        
        return image_url, text_content

    async def _handle_schedule_vote_button(
        self, value: dict, user_id: str, channel_id: str, user_name: str
    ):
        """处理预定时间投票按钮点击"""
        vote_id = value.get("vote_id")
        choice = value.get("choice")  # "agree" or "reject"
        
        if not vote_id or not choice:
            await self.client.send_message(channel_id, f"(met){user_id}(met) 参数错误", msg_type=9)
            return
        
        # 获取投票信息
        vote_info = await self.db.get_schedule_vote(vote_id)
        if not vote_info:
            await self.client.send_message(channel_id, f"(met){user_id}(met) 该投票已过期或不存在", msg_type=9)
            return
        
        # 检查用户是否有投票权限（必须在被提及的用户ID列表中）
        mentioned_users = vote_info.get("mentioned_users", [])
        if user_id not in mentioned_users:
            await self.client.send_message(channel_id, f"(met){user_id}(met) 你没有参与此次投票的权限", msg_type=9)
            return
        
        # 检查用户是否已经投过票（使用用户ID作为key）
        existing_votes = await self.db.get_schedule_votes(vote_id)
        if user_id in existing_votes:
            current_choice = existing_votes[user_id]["choice"]
            choice_text = "同意" if current_choice == "agree" else "拒绝"
            await self.client.send_message(channel_id, f"(met){user_id}(met) 你已经投过票了（选择：{choice_text}），每人只能投一次", msg_type=9)
            return
        
        # 记录投票（使用用户ID作为key）
        await self.db.record_schedule_vote(vote_id, user_id, choice, user_id)
        
        # 发送投票确认消息
        choice_text = "同意" if choice == "agree" else "拒绝"
        emoji = "✅" if choice == "agree" else "❌"
        await self.client.send_message(
            channel_id, 
            f"{emoji} (met){user_id}(met) 选择了 **{choice_text}**", 
            msg_type=9
        )
        
        # 获取更新后的投票结果
        updated_votes = await self.db.get_schedule_votes(vote_id)
        
        # 构建并发送更新后的投票结果卡片
        result_card = CardBuilder.build_schedule_vote_result_card(
            vote_id=vote_id,
            schedule_time=vote_info["schedule_time"],
            description=vote_info.get("description", ""),
            initiator_name=vote_info["initiator_name"],
            votes=updated_votes,
            mentioned_users=mentioned_users
        )
        
        await self.client.send_message(channel_id, result_card, msg_type=10)
        
        logger.info(f"SCHEDULE_VOTE | user={user_id}({user_name}) | vote_id={vote_id} | choice={choice}")


    async def _maybe_log_message(
        self,
        channel_id: str,
        user_id: str,
        user_name: str,
        content: str,
        is_bot: bool = False,
        if_cmd: bool = False,
    ):
        """如果频道有活跃日志且用户在记录范围内，则记录消息"""
        from .commands.gamelog import get_active_log, is_user_in_log

        log_info = get_active_log(channel_id)
        if not log_info or log_info.get("paused"):
            return

        # Bot消息总是记录，用户消息需要检查是否在参与者列表中
        if not is_bot and not is_user_in_log(channel_id, user_id):
            return

        # 如果是卡片消息（JSON格式），将 Unicode 转义码还原成正常文字
        log_content = content
        if content.startswith("[{") or content.startswith("{"):
            try:
                # 解析 JSON 再序列化，ensure_ascii=False 会将 \uXXXX 转为正常字符
                parsed = json.loads(content)
                log_content = json.dumps(parsed, ensure_ascii=False)
            except json.JSONDecodeError:
                pass  # 解析失败则保持原样

        # 记录到数据库
        await self.db.add_game_log_entry(
            log_name=log_info["log_name"],
            user_id=user_id,
            user_name=user_name,
            content=log_content,
            msg_type="text",
            is_bot=is_bot,
            if_cmd=if_cmd,
        )

    async def _handle_log_page_button(
        self, value: dict, user_id: str, channel_id: str
    ):
        """处理日志列表翻页按钮"""
        page = value.get("page", 1)
        target_channel = value.get("channel_id", channel_id)

        logs, total = await self.db.list_game_logs(target_channel, page=page, page_size=10)

        if total == 0:
            await self.client.send_message(channel_id, "📝 当前频道暂无日志记录", msg_type=9)
            return

        card = CardBuilder.build_game_log_list_card(
            logs=logs,
            total=total,
            page=page,
            channel_id=target_channel,
        )

        await self.client.send_message(channel_id, card, msg_type=10)
