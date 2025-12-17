"""杂项命令"""
import re
import base64
from loguru import logger
from .base import BaseCommand, CommandResult
from .registry import command
from ..card_builder import CardBuilder


@command("help")
class HelpCommand(BaseCommand):
    """帮助命令"""
    
    description = "显示帮助信息"
    usage = ".help"
    
    async def execute(self, args: str) -> CommandResult:
        """帮助命令"""
        return CommandResult.text("""**COC Dice Bot 帮助**

**骰点命令**
`.r / .rd <表达式>` - 骰点 (如 .rd 1d100, .r 3d6+5, .r 1d6+1d4)
`.rd r2 d100` - 带2个奖励骰的d100
`.rd p1 d100` - 带1个惩罚骰的d100
`.ra <技能名>` - 技能检定 (使用角色卡数值)
`.ra <技能名> <值>` - 指定值检定 (如 .ra 侦查 50)
`.ra r2 侦查` - 带奖励骰的技能检定
`.ra p1 聆听 60` - 带惩罚骰的指定值检定
`.ra p1 <技能> t<轮数>` - 多轮检定 (如 .ra p1 手枪 t3)
`.rc <技能名> <值>` - 指定值检定 (同 .ra 技能 值)
`.sc <成功>/<失败>` - SAN Check (如 .sc0/1d6, .sc1d4/2d6)
`.gun <技能> [r/p] t<波数>` - 全自动枪械连发 (如 .gun 步枪 r1 t7)

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
`.npc <名称> gun <技能> [r/p] t<波数>` - NPC 全自动枪械连发
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
`.cc <角色名> @KP` - 发起角色卡审核

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
`.rule fumble <值>` - 设置大失败阈值

**记事本命令**
`.note` - 查看当前记事本
`.note all` - 查看所有记事本
`.note c <名称>` - 创建新记事本
`.note s <名称>` - 切换记事本
`.note i <内容>` - 记录内容
`.note img <名称>` - 记录图片（发图时附带命令）
`.note list` - 查看记录列表
`.note w <序号>` - 查看具体内容

**其他命令**
`.push` - 将下一条消息发布为卡片并置顶""")


@command("ri")
class InitiativeCommand(BaseCommand):
    """先攻顺序命令"""
    
    description = "先攻顺序表"
    usage = ".ri @用户1 @用户2 npc 守卫 怪物"
    
    async def execute(self, args: str) -> CommandResult:
        """先攻顺序: .ri @用户1 @用户2 npc 守卫 怪物"""
        args = args.strip()
        if not args:
            return CommandResult.text(
                "格式: `.ri @用户1 @用户2 npc <NPC名1> <NPC名2> ...`\n"
                "示例: `.ri @张三 @李四 npc 守卫 怪物`\n"
                "根据 DEX 从大到小排序生成先攻顺序表"
            )
        
        participants = []
        
        # 提取所有 @用户
        user_mentions = re.findall(r"\(met\)(\d+)\(met\)", args)
        remaining = re.sub(r"\(met\)\d+\(met\)", "", args).strip()
        
        # 处理玩家
        for mentioned_user_id in user_mentions:
            char = await self.ctx.char_manager.get_active(mentioned_user_id)
            if char:
                dex = char.get_skill("DEX") or char.attributes.get("DEX", 0)
                participants.append((char.name, dex, "player", mentioned_user_id))
            else:
                participants.append((f"(met){mentioned_user_id}(met)", 0, "player", mentioned_user_id))
        
        # 解析 NPC 名称
        npc_names = []
        if remaining:
            if remaining.lower().startswith("npc"):
                remaining = remaining[3:].strip()
            if remaining:
                npc_names = remaining.split()
        
        # 处理 NPC
        for npc_name in npc_names:
            npc = await self.ctx.npc_manager.get(self.ctx.channel_id, npc_name)
            if npc:
                dex = npc.attributes.get("DEX", 0)
                participants.append((npc.name, dex, "npc", None))
            else:
                participants.append((f"{npc_name} (未找到)", 0, "unknown", None))
        
        if not participants:
            return CommandResult.text("未找到任何参与者，请 @ 用户或指定 NPC 名称")
        
        # 按 DEX 从大到小排序
        participants.sort(key=lambda x: x[1], reverse=True)
        
        card = CardBuilder.build_initiative_card(participants)
        return CommandResult.card(card)



@command("cc")
class CharacterReviewCommand(BaseCommand):
    """角色卡审核命令"""
    
    description = "角色卡审核"
    usage = ".cc <角色名> @KP"
    
    async def execute(self, args: str) -> CommandResult:
        """角色卡审核命令: .cc <角色名> @KP"""
        args = args.strip()
        if not args:
            return CommandResult.text(
                "**角色卡审核命令**\n"
                "`.cc <角色名> @KP` - 发起角色卡审核\n"
                "示例: `.cc 张三 @KP`\n\n"
                "请先在网页上创建角色卡并提交审核，然后使用此命令发起审核\n"
                "只有被 @ 的 KP 才能审核"
            )
        
        # 解析 @KP
        kp_match = re.search(r"\(met\)(\d+)\(met\)", args)
        if not kp_match:
            return CommandResult.text(
                "请 @ 一个 KP 来审核角色卡\n"
                "格式: `.cc <角色名> @KP`\n"
                "示例: `.cc 张三 @KP`"
            )
        
        kp_id = kp_match.group(1)
        char_name = re.sub(r"\s*\(met\)\d+\(met\)\s*", "", args).strip()
        
        # 从数据库获取待审核数据
        review = await self.ctx.db.get_character_review(char_name)
        if not review:
            return CommandResult.text(f"未找到待审核角色卡: {char_name}\n请先在网页上提交审核")
        
        # 验证是否是提交者
        if review["user_id"] != self.ctx.user_id:
            return CommandResult.text("只有提交者可以发起审核")
        
        # 不能让自己审核自己
        if kp_id == self.ctx.user_id:
            return CommandResult.text("不能让自己审核自己的角色卡，请 @ 其他 KP")
        
        # 检查是否已有图片 URL
        image_url = review.get("image_url")
        if not image_url:
            image_data = review["image_data"]
            if image_data and image_data.startswith("data:image/png;base64,"):
                image_data = image_data.split(",", 1)[1]
            
            if not image_data:
                return CommandResult.text("图片数据不存在")
            
            try:
                image_bytes = base64.b64decode(image_data)
            except Exception as e:
                logger.error(f"解码图片失败: {e}")
                return CommandResult.text("图片数据解析失败")
            
            # 上传图片到 KOOK
            image_url = await self.ctx.client.upload_asset(image_bytes, f"{char_name}.png")
            if not image_url:
                return CommandResult.text("图片上传失败")
            
            await self.ctx.db.update_review_image_url(char_name, image_url)
            logger.info(f"角色卡图片上传成功: {char_name} -> {image_url}")
        
        card = CardBuilder.build_character_review_card(
            char_name=char_name,
            image_url=image_url,
            initiator_id=self.ctx.user_id,
            initiator_name=self.ctx.user_name,
            kp_id=kp_id,
        )
        
        return CommandResult.card(card)


@command("hp")
class HPCommand(BaseCommand):
    """HP 调整命令"""
    
    description = "HP 调整"
    usage = ".hp +5, .hp -3, .hp 10"
    
    async def execute(self, args: str) -> CommandResult:
        """HP 调整: .hp +5, .hp -3, .hp 10"""
        return await self._adjust_stat(args, "hp")
    
    async def _adjust_stat(self, args: str, stat_type: str) -> CommandResult:
        """通用属性调整方法"""
        args = args.strip()
        
        char = await self.ctx.char_manager.get_active(self.ctx.user_id)
        if not char:
            return CommandResult.text("请先导入角色卡")
        
        # 无参数时显示当前值
        if not args:
            if stat_type == "hp":
                return CommandResult.text(f"**{char.name}** HP: {char.hp}/{char.max_hp}")
            elif stat_type == "mp":
                return CommandResult.text(f"**{char.name}** MP: {char.mp}/{char.max_mp}")
            else:
                max_san = self._calc_max_san(char)
                return CommandResult.text(f"**{char.name}** SAN: {char.san}/{max_san}")
        
        # 解析调整值
        try:
            if args.startswith("+"):
                delta = int(args[1:])
            elif args.startswith("-"):
                delta = -int(args[1:])
            else:
                new_value = int(args)
                return await self._set_stat(char, stat_type, new_value)
        except ValueError:
            return CommandResult.text(f"无效的数值: {args}")
        
        return await self._apply_stat_delta(char, stat_type, delta)
    
    async def _set_stat(self, char, stat_type: str, new_value: int) -> CommandResult:
        """直接设置属性值"""
        if stat_type == "hp":
            old_value = char.hp
            char.hp = max(0, min(new_value, char.max_hp))
            await self.ctx.char_manager.add(char)
            return CommandResult.text(f"**{char.name}** HP: {old_value} → **{char.hp}**/{char.max_hp}")
        elif stat_type == "mp":
            old_value = char.mp
            char.mp = max(0, min(new_value, char.max_mp))
            await self.ctx.char_manager.add(char)
            return CommandResult.text(f"**{char.name}** MP: {old_value} → **{char.mp}**/{char.max_mp}")
        else:
            old_value = char.san
            max_san = self._calc_max_san(char)
            char.san = max(0, min(new_value, max_san))
            await self.ctx.char_manager.add(char)
            return CommandResult.text(f"**{char.name}** SAN: {old_value} → **{char.san}**/{max_san}")
    
    async def _apply_stat_delta(self, char, stat_type: str, delta: int) -> CommandResult:
        """应用属性变化"""
        sign = "+" if delta > 0 else ""
        if stat_type == "hp":
            old_value = char.hp
            char.hp = max(0, min(char.hp + delta, char.max_hp))
            await self.ctx.char_manager.add(char)
            return CommandResult.text(f"**{char.name}** HP: {old_value} {sign}{delta} → **{char.hp}**/{char.max_hp}")
        elif stat_type == "mp":
            old_value = char.mp
            char.mp = max(0, min(char.mp + delta, char.max_mp))
            await self.ctx.char_manager.add(char)
            return CommandResult.text(f"**{char.name}** MP: {old_value} {sign}{delta} → **{char.mp}**/{char.max_mp}")
        else:
            old_value = char.san
            max_san = self._calc_max_san(char)
            char.san = max(0, min(char.san + delta, max_san))
            await self.ctx.char_manager.add(char)
            return CommandResult.text(f"**{char.name}** SAN: {old_value} {sign}{delta} → **{char.san}**/{max_san}")
    
    def _calc_max_san(self, char) -> int:
        cthulhu_mythos = char.skills.get("克苏鲁神话", 0)
        if cthulhu_mythos == 0:
            cthulhu_mythos = char.skills.get("CM", 0)
        return 99 - cthulhu_mythos


@command("mp")
class MPCommand(HPCommand):
    """MP 调整命令"""
    
    description = "MP 调整"
    usage = ".mp +5, .mp -3, .mp 10"
    
    async def execute(self, args: str) -> CommandResult:
        """MP 调整: .mp +5, .mp -3, .mp 10"""
        return await self._adjust_stat(args, "mp")


@command("san")
class SANCommand(HPCommand):
    """SAN 调整命令"""
    
    description = "SAN 调整"
    usage = ".san +5, .san -3, .san 10"
    
    async def execute(self, args: str) -> CommandResult:
        """SAN 调整: .san +5, .san -3, .san 10"""
        return await self._adjust_stat(args, "san")
