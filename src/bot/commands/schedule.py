"""预定时间投票命令"""
import re
import uuid
from datetime import datetime
from typing import Optional

from loguru import logger

from ..card_builder import CardBuilder
from .base import BaseCommand, CommandResult
from .registry import command


@command("pre", aliases=["预定", "schedule"])
class ScheduleCommand(BaseCommand):
    """预定时间投票命令"""

    name = "pre"
    aliases = ["预定", "schedule"]
    description = "发起预定时间投票"
    usage = ".pre 202602230830 @用户1 @用户2 [描述]"

    async def execute(self, args: str) -> CommandResult:
        """执行预定时间投票命令"""
        if not args.strip():
            return CommandResult.text(
                "用法: `.pre 时间 @用户1 @用户2 [描述]`\n"
                "时间格式: YYYYMMDDHHMM 或 MMDDHHMM (省略年份默认当前年)\n"
                "例如: `.pre 202602230830 @张三 @李四 开会讨论`\n"
                "注意: 直接在聊天框中@用户即可"
            )

        # 解析参数
        parsed = self._parse_args(args)
        if not parsed:
            return CommandResult.text(
                "❌ 参数格式错误\n"
                "用法: `.pre 时间 @用户1 @用户2 [描述]`\n"
                "时间格式: YYYYMMDDHHMM 或 MMDDHHMM\n"
                "请确保在时间后面@了至少一个用户"
            )

        time_str, mentioned_users, description = parsed

        # 解析时间
        schedule_time = self._parse_time(time_str)
        if not schedule_time:
            return CommandResult.text(
                "❌ 时间格式错误\n"
                "支持格式:\n"
                "- YYYYMMDDHHMM (如: 202602230830)\n"
                "- MMDDHHMM (如: 02230830，默认当前年份)"
            )

        # 检查时间是否在未来
        if schedule_time <= datetime.now():
            return CommandResult.text("❌ 预定时间必须是未来时间")

        # 检查是否有提及的用户
        if not mentioned_users:
            return CommandResult.text("❌ 请至少提及一个用户")

        # 创建投票记录
        vote_id = await self._create_vote(
            schedule_time,
            mentioned_users,
            description,
            self.ctx.user_id,
            self.ctx.user_name,
            self.ctx.channel_id,
        )

        # 构建投票卡片
        card = CardBuilder.build_schedule_vote_card(
            vote_id=vote_id,
            schedule_time=schedule_time,
            mentioned_users=mentioned_users,
            description=description,
            initiator_name=self.ctx.user_name,
        )

        logger.info(
            f"SCHEDULE_VOTE | user={self.ctx.user_id} | "
            f"time={schedule_time} | users={len(mentioned_users)}"
        )

        return CommandResult.card(card)

    def _parse_args(self, args: str) -> Optional[tuple[str, list[str], str]]:
        """解析命令参数"""
        # KOOK 的 @ 格式是 (met)用户ID(met)
        # 匹配时间和(met)用户ID(met)
        # 时间: 8-12位数字
        # @用户: 一个或多个 (met)用户ID(met)
        # 描述: 剩余部分（可选）
        pattern = r"^(\d{8,12})\s+((?:\(met\)\d+\(met\)\s*)+)(.*)$"
        match = re.match(pattern, args.strip())

        if not match:
            return None

        time_str = match.group(1)
        mentions_str = match.group(2)
        description = match.group(3).strip()

        # 提取用户ID
        mentioned_users = re.findall(r"\(met\)(\d+)\(met\)", mentions_str)

        return time_str, mentioned_users, description

    def _parse_time(self, time_str: str) -> Optional[datetime]:
        """解析时间字符串"""
        try:
            current_year = datetime.now().year

            if len(time_str) == 12:  # YYYYMMDDHHMM
                year = int(time_str[:4])
                month = int(time_str[4:6])
                day = int(time_str[6:8])
                hour = int(time_str[8:10])
                minute = int(time_str[10:12])
            elif len(time_str) == 8:  # MMDDHHMM
                year = current_year
                month = int(time_str[:2])
                day = int(time_str[2:4])
                hour = int(time_str[4:6])
                minute = int(time_str[6:8])
            else:
                return None

            return datetime(year, month, day, hour, minute)

        except (ValueError, IndexError):
            return None

    async def _create_vote(
        self,
        schedule_time: datetime,
        mentioned_users: list[str],
        description: str,
        initiator_id: str,
        initiator_name: str,
        channel_id: str,
    ) -> str:
        """创建投票记录"""
        vote_id = str(uuid.uuid4())[:8]

        # 存储到数据库
        await self.ctx.db.create_schedule_vote(
            vote_id=vote_id,
            schedule_time=schedule_time,
            mentioned_users=mentioned_users,
            description=description,
            initiator_id=initiator_id,
            initiator_name=initiator_name,
            channel_id=channel_id,
        )

        return vote_id
