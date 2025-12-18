"""游戏日志记录命令"""
import re
from datetime import datetime
from typing import Optional

from loguru import logger

from ..card_builder import CardBuilder
from .base import BaseCommand, CommandResult
from .registry import command


# 存储当前活跃的日志会话 {channel_id: log_info}
_active_logs: dict[str, dict] = {}


def get_active_log(channel_id: str) -> Optional[dict]:
    """获取频道的活跃日志"""
    return _active_logs.get(channel_id)


def is_user_in_log(channel_id: str, user_id: str) -> bool:
    """检查用户是否在日志记录范围内"""
    log_info = _active_logs.get(channel_id)
    if not log_info or log_info.get("paused"):
        return False
    return user_id in log_info.get("participants", [])


@command("log", aliases=["日志", "记录"])
class GameLogCommand(BaseCommand):
    """游戏日志记录命令"""

    name = "log"
    aliases = ["日志", "记录"]
    description = "记录游戏日志"
    usage = ".log start @用户1 @用户2 | save | load | end | list | o <名称> | a <名称>"

    async def execute(self, args: str) -> CommandResult:
        """执行日志命令"""
        if not args.strip():
            return self._show_help()

        parts = args.strip().split(maxsplit=1)
        sub_cmd = parts[0].lower()
        sub_args = parts[1] if len(parts) > 1 else ""

        if sub_cmd == "start":
            return await self._start_log(sub_args)
        elif sub_cmd == "save":
            return await self._save_log()
        elif sub_cmd == "load":
            return await self._load_log()
        elif sub_cmd == "end":
            return await self._end_log()
        elif sub_cmd == "list":
            return await self._list_logs()
        elif sub_cmd == "o":
            return await self._export_log(sub_args)
        elif sub_cmd == "a":
            return await self._analyze_log(sub_args)
        else:
            return self._show_help()

    def _show_help(self) -> CommandResult:
        """显示帮助信息"""
        return CommandResult.text(
            "📝 **日志记录命令**\n"
            "`.log start @用户1 @用户2` - 开始记录（自动包含发起者）\n"
            "`.log save` - 暂停记录\n"
            "`.log load` - 继续记录\n"
            "`.log end` - 结束记录\n"
            "`.log list` - 查看记录列表\n"
            "`.log o <名称>` - 导出JSON文件\n"
            "`.log a <名称>` - 分析统计数据"
        )

    async def _start_log(self, args: str) -> CommandResult:
        """开始记录日志"""
        channel_id = self.ctx.channel_id

        # 检查是否已有活跃日志
        if channel_id in _active_logs:
            return CommandResult.text("❌ 当前频道已有进行中的日志记录，请先结束: `.log end`")

        # 解析@用户
        mentioned_users = re.findall(r"\(met\)(\d+)\(met\)", args)

        # 添加发起者（如果不在列表中）
        if self.ctx.user_id not in mentioned_users:
            mentioned_users.insert(0, self.ctx.user_id)

        if len(mentioned_users) < 1:
            return CommandResult.text("❌ 请至少指定一个参与者")

        # 生成日志名称: 时间戳_频道ID
        now = datetime.now()
        log_name = f"{now.strftime('%Y%m%d_%H%M%S')}_{channel_id}"

        # 创建日志记录
        await self.ctx.db.create_game_log(
            log_name=log_name,
            channel_id=channel_id,
            initiator_id=self.ctx.user_id,
            participants=mentioned_users,
        )

        # 存储活跃日志信息
        _active_logs[channel_id] = {
            "log_name": log_name,
            "participants": mentioned_users,
            "initiator_id": self.ctx.user_id,
            "paused": False,
            "started_at": now,
        }

        # 构建参与者显示
        participants_display = ", ".join([f"(met){uid}(met)" for uid in mentioned_users])

        logger.info(f"LOG_START | channel={channel_id} | log={log_name} | users={len(mentioned_users)}")

        return CommandResult.text(
            f"📝 **日志记录已开始**\n"
            f"名称: `{log_name}`\n"
            f"参与者: {participants_display}\n"
            f"将记录以上用户和Bot的所有发言"
        )

    async def _save_log(self) -> CommandResult:
        """暂停记录"""
        channel_id = self.ctx.channel_id

        if channel_id not in _active_logs:
            return CommandResult.text("❌ 当前频道没有进行中的日志记录")

        log_info = _active_logs[channel_id]
        if log_info.get("paused"):
            return CommandResult.text("❌ 日志记录已经是暂停状态")

        log_info["paused"] = True
        logger.info(f"LOG_SAVE | channel={channel_id} | log={log_info['log_name']}")

        return CommandResult.text(f"⏸️ 日志记录已暂停: `{log_info['log_name']}`\n使用 `.log load` 继续记录")

    async def _load_log(self) -> CommandResult:
        """继续记录"""
        channel_id = self.ctx.channel_id

        if channel_id not in _active_logs:
            return CommandResult.text("❌ 当前频道没有进行中的日志记录")

        log_info = _active_logs[channel_id]
        if not log_info.get("paused"):
            return CommandResult.text("❌ 日志记录已经在进行中")

        log_info["paused"] = False
        logger.info(f"LOG_LOAD | channel={channel_id} | log={log_info['log_name']}")

        return CommandResult.text(f"▶️ 日志记录已继续: `{log_info['log_name']}`")

    async def _end_log(self) -> CommandResult:
        """结束记录"""
        channel_id = self.ctx.channel_id

        if channel_id not in _active_logs:
            return CommandResult.text("❌ 当前频道没有进行中的日志记录")

        log_info = _active_logs.pop(channel_id)
        log_name = log_info["log_name"]

        # 更新数据库中的结束时间
        await self.ctx.db.end_game_log(log_name)

        # 获取统计信息
        stats = await self.ctx.db.get_game_log_stats(log_name)

        logger.info(f"LOG_END | channel={channel_id} | log={log_name} | entries={stats.get('total_entries', 0)}")

        return CommandResult.text(
            f"⏹️ **日志记录已结束**\n"
            f"名称: `{log_name}`\n"
            f"共记录 **{stats.get('total_entries', 0)}** 条消息\n"
            f"使用 `.log o {log_name}` 导出 | `.log a {log_name}` 分析"
        )

    async def _list_logs(self, page: int = 1) -> CommandResult:
        """列出日志记录"""
        channel_id = self.ctx.channel_id

        logs, total = await self.ctx.db.list_game_logs(channel_id, page=page, page_size=10)

        if total == 0:
            return CommandResult.text("📝 当前频道暂无日志记录")

        card = CardBuilder.build_game_log_list_card(
            logs=logs,
            total=total,
            page=page,
            channel_id=channel_id,
        )

        return CommandResult.card(card)

    async def _export_log(self, log_name: str) -> CommandResult:
        """导出日志"""
        if not log_name.strip():
            return CommandResult.text("❌ 请指定日志名称: `.log o <名称>`")

        log_name = log_name.strip()

        # 检查日志是否存在
        log_info = await self.ctx.db.get_game_log(log_name)
        if not log_info:
            return CommandResult.text(f"❌ 日志 `{log_name}` 不存在")

        # 检查权限（只有同频道的日志可以导出）
        if log_info["channel_id"] != self.ctx.channel_id:
            return CommandResult.text("❌ 只能导出当前频道的日志")

        # 生成导出链接
        from ...config import settings

        export_url = f"{settings.web_base_url}/api/logs/{log_name}/export"

        card = CardBuilder.build_game_log_export_card(
            log_name=log_name,
            export_url=export_url,
            total_entries=log_info.get("entry_count", 0),
        )

        return CommandResult.card(card)

    async def _analyze_log(self, log_name: str) -> CommandResult:
        """分析日志统计"""
        if not log_name.strip():
            return CommandResult.text("❌ 请指定日志名称: `.log a <名称>`")

        log_name = log_name.strip()

        # 检查日志是否存在
        log_info = await self.ctx.db.get_game_log(log_name)
        if not log_info:
            return CommandResult.text(f"❌ 日志 `{log_name}` 不存在")

        # 检查权限
        if log_info["channel_id"] != self.ctx.channel_id:
            return CommandResult.text("❌ 只能分析当前频道的日志")

        # 获取统计数据
        stats = await self.ctx.db.analyze_game_log(log_name)

        card = CardBuilder.build_game_log_analysis_card(
            log_name=log_name,
            stats=stats,
        )

        return CommandResult.card(card)
