"""管理员命令"""
from loguru import logger
from .base import BaseCommand, CommandResult
from .registry import command


# 内存缓存管理员 ID（启动时从数据库加载）
_admin_id: str | None = None


async def load_admin_id(db) -> str | None:
    """启动时加载管理员 ID"""
    global _admin_id
    _admin_id = await db.get_bot_admin()
    if _admin_id:
        logger.info(f"已加载管理员: {_admin_id}")
    return _admin_id


async def get_admin_id(db) -> str | None:
    """获取管理员 ID"""
    global _admin_id
    if _admin_id is None:
        _admin_id = await db.get_bot_admin()
    return _admin_id


async def set_admin_id(db, user_id: str) -> bool:
    """设置管理员 ID（仅首次）"""
    global _admin_id
    current = await get_admin_id(db)
    if current is not None:
        return False
    await db.set_bot_admin(user_id)
    _admin_id = user_id
    return True


def is_admin(user_id: str) -> bool:
    """检查是否是管理员"""
    return _admin_id is not None and _admin_id == user_id


@command("admin", aliases=["管理"])
class AdminCommand(BaseCommand):
    """管理员命令"""
    
    description = "机器人管理员命令"
    usage = ".admin bind / .admin friend list / .admin friend accept <id>"
    
    async def execute(self, args: str) -> CommandResult:
        args = args.strip()
        if not args:
            return CommandResult.text(
                "**管理员命令**\n"
                "`.admin bind` - 绑定为机器人管理员（仅首次有效）\n"
                "`.admin friend list` - 查看好友申请列表\n"
                "`.admin friend accept <user_id>` - 同意好友申请\n"
                "`.admin friend reject <user_id>` - 拒绝好友申请"
            )
        
        parts = args.split(maxsplit=1)
        sub_cmd = parts[0].lower()
        sub_args = parts[1] if len(parts) > 1 else ""
        
        if sub_cmd == "bind":
            return await self._bind_admin()
        elif sub_cmd == "friend":
            return await self._handle_friend(sub_args)
        else:
            return CommandResult.text(f"未知子命令: {sub_cmd}")
    
    async def _bind_admin(self) -> CommandResult:
        """绑定管理员"""
        current_admin = await get_admin_id(self.ctx.db)
        
        if current_admin is not None:
            if current_admin == self.ctx.user_id:
                return CommandResult.text("你已经是管理员了")
            return CommandResult.text("❌ 管理员已被绑定，无法重复绑定")
        
        success = await set_admin_id(self.ctx.db, self.ctx.user_id)
        if success:
            logger.info(f"ADMIN_BIND | user={self.ctx.user_id}({self.ctx.user_name})")
            return CommandResult.text(f"✅ 绑定成功！你现在是机器人管理员")
        else:
            return CommandResult.text("❌ 绑定失败，管理员已存在")
    
    async def _handle_friend(self, args: str) -> CommandResult:
        """处理好友相关命令"""
        # 检查权限
        if not is_admin(self.ctx.user_id):
            return CommandResult.text("❌ 只有管理员可以使用此命令")
        
        parts = args.split(maxsplit=1)
        if not parts:
            return CommandResult.text("请指定操作: list / accept <id> / reject <id>")
        
        action = parts[0].lower()
        action_args = parts[1] if len(parts) > 1 else ""
        
        if action == "list":
            return await self._list_friend_requests()
        elif action == "accept":
            return await self._accept_friend(action_args)
        elif action == "reject":
            return await self._reject_friend(action_args)
        else:
            return CommandResult.text(f"未知操作: {action}")
    
    async def _list_friend_requests(self) -> CommandResult:
        """列出好友申请"""
        requests = await self.ctx.client.get_friend_requests()
        
        if not requests:
            return CommandResult.text("📭 暂无好友申请")
        
        lines = ["**📬 好友申请列表**", ""]
        for req in requests:
            request_id = req.get("id", "未知")
            friend_info = req.get("friend_info", {})
            user_id = friend_info.get("id", "未知")
            username = friend_info.get("username", "未知")
            identify_num = friend_info.get("identify_num", "")
            full_name = f"{username}#{identify_num}" if identify_num else username
            lines.append(f"• 申请ID: `{request_id}` | {full_name} (用户ID: {user_id})")
        
        lines.append("")
        lines.append("使用 `.admin friend accept <申请ID>` 同意申请")
        
        return CommandResult.text("\n".join(lines))
    
    async def _accept_friend(self, request_id: str) -> CommandResult:
        """同意好友申请"""
        request_id = request_id.strip()
        if not request_id:
            return CommandResult.text("请指定申请 ID: `.admin friend accept <申请ID>`")
        
        try:
            rid = int(request_id)
        except ValueError:
            return CommandResult.text("申请 ID 必须是数字")
        
        success = await self.ctx.client.handle_friend_request(rid, accept=True)
        if success:
            logger.info(f"FRIEND_ACCEPT | admin={self.ctx.user_id} | request_id={rid}")
            return CommandResult.text(f"✅ 已同意申请 `{rid}`")
        else:
            return CommandResult.text(f"❌ 操作失败，请检查申请 ID 是否正确")
    
    async def _reject_friend(self, request_id: str) -> CommandResult:
        """拒绝好友申请"""
        request_id = request_id.strip()
        if not request_id:
            return CommandResult.text("请指定申请 ID: `.admin friend reject <申请ID>`")
        
        try:
            rid = int(request_id)
        except ValueError:
            return CommandResult.text("申请 ID 必须是数字")
        
        success = await self.ctx.client.handle_friend_request(rid, accept=False)
        if success:
            logger.info(f"FRIEND_REJECT | admin={self.ctx.user_id} | request_id={rid}")
            return CommandResult.text(f"✅ 已拒绝申请 `{rid}`")
        else:
            return CommandResult.text(f"❌ 操作失败，请检查申请 ID 是否正确")
