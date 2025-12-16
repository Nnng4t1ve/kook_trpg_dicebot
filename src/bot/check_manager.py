"""检定管理器 - 管理 KP 发起的检定"""
import asyncio
import uuid
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Set, Tuple
from loguru import logger


@dataclass
class PendingCheck:
    """待处理的检定"""
    check_id: str
    skill_name: str
    channel_id: str
    kp_id: str
    created_at: float
    target_value: Optional[int] = None  # 如果指定了固定值
    completed_users: Set[str] = field(default_factory=set)  # 已完成检定的用户

    def is_expired(self, timeout: int = 600) -> bool:
        """检查是否过期 (默认 10 分钟)"""
        return time.time() - self.created_at > timeout


@dataclass
class OpposedCheck:
    """对抗检定"""
    check_id: str
    initiator_id: str  # 发起者 ID
    target_id: str  # 目标用户 ID
    initiator_skill: str  # 发起者技能
    target_skill: str  # 目标技能
    channel_id: str
    created_at: float
    # 奖励骰/惩罚骰
    initiator_bonus: int = 0
    initiator_penalty: int = 0
    target_bonus: int = 0
    target_penalty: int = 0
    # 发起者的检定结果
    initiator_roll: Optional[int] = None
    initiator_target: Optional[int] = None
    initiator_level: Optional[int] = None  # 成功等级数值
    # 目标的检定结果
    target_roll: Optional[int] = None
    target_target: Optional[int] = None
    target_level: Optional[int] = None

    def is_expired(self, timeout: int = 600) -> bool:
        return time.time() - self.created_at > timeout

    def is_complete(self) -> bool:
        return self.initiator_level is not None and self.target_level is not None

    def get_skill_for_user(self, user_id: str) -> Optional[str]:
        """获取用户对应的技能"""
        if user_id == self.initiator_id:
            return self.initiator_skill
        elif user_id == self.target_id:
            return self.target_skill
        return None

    def get_bonus_penalty_for_user(self, user_id: str) -> Tuple[int, int]:
        """获取用户对应的奖励骰/惩罚骰"""
        if user_id == self.initiator_id:
            return (self.initiator_bonus, self.initiator_penalty)
        elif user_id == self.target_id:
            return (self.target_bonus, self.target_penalty)
        return (0, 0)


class CheckManager:
    """检定管理器"""

    def __init__(self, cleanup_interval: int = 300):
        self._checks: Dict[str, PendingCheck] = {}
        self._opposed_checks: Dict[str, OpposedCheck] = {}
        self._cleanup_interval = cleanup_interval  # 清理间隔（秒）
        self._cleanup_task: Optional[asyncio.Task] = None
    
    def start_cleanup_task(self):
        """启动定时清理任务"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
            logger.info(f"检定清理任务已启动，间隔 {self._cleanup_interval} 秒")
    
    def stop_cleanup_task(self):
        """停止定时清理任务"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            self._cleanup_task = None
            logger.info("检定清理任务已停止")
    
    async def _periodic_cleanup(self):
        """定期清理过期检定"""
        while True:
            try:
                await asyncio.sleep(self._cleanup_interval)
                cleaned = self._cleanup_expired()
                if cleaned > 0:
                    logger.debug(f"清理了 {cleaned} 个过期检定")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"清理任务出错: {e}")

    def create_check(
        self,
        skill_name: str,
        channel_id: str,
        kp_id: str,
        target_value: Optional[int] = None,
    ) -> PendingCheck:
        """创建新检定"""
        check_id = str(uuid.uuid4())[:8]
        check = PendingCheck(
            check_id=check_id,
            skill_name=skill_name,
            channel_id=channel_id,
            kp_id=kp_id,
            created_at=time.time(),
            target_value=target_value,
        )
        self._checks[check_id] = check
        self._cleanup_expired()
        return check

    def get_check(self, check_id: str) -> Optional[PendingCheck]:
        """获取检定"""
        check = self._checks.get(check_id)
        if check and not check.is_expired():
            return check
        return None

    def mark_completed(self, check_id: str, user_id: str) -> bool:
        """标记用户已完成检定"""
        check = self.get_check(check_id)
        if check:
            if user_id in check.completed_users:
                return False  # 已经检定过了
            check.completed_users.add(user_id)
            return True
        return False

    def has_completed(self, check_id: str, user_id: str) -> bool:
        """检查用户是否已完成检定"""
        check = self.get_check(check_id)
        return check is not None and user_id in check.completed_users

    # ===== 对抗检定 =====
    def create_opposed_check(
        self,
        initiator_id: str,
        target_id: str,
        initiator_skill: str,
        target_skill: str,
        channel_id: str,
        initiator_bonus: int = 0,
        initiator_penalty: int = 0,
        target_bonus: int = 0,
        target_penalty: int = 0,
    ) -> OpposedCheck:
        """创建对抗检定"""
        check_id = str(uuid.uuid4())[:8]
        check = OpposedCheck(
            check_id=check_id,
            initiator_id=initiator_id,
            target_id=target_id,
            initiator_skill=initiator_skill,
            target_skill=target_skill,
            channel_id=channel_id,
            created_at=time.time(),
            initiator_bonus=initiator_bonus,
            initiator_penalty=initiator_penalty,
            target_bonus=target_bonus,
            target_penalty=target_penalty,
        )
        self._opposed_checks[check_id] = check
        self._cleanup_expired()
        return check

    def get_opposed_check(self, check_id: str) -> Optional[OpposedCheck]:
        """获取对抗检定"""
        check = self._opposed_checks.get(check_id)
        if check and not check.is_expired():
            return check
        return None

    def set_opposed_result(
        self, check_id: str, user_id: str, roll: int, target: int, level: int
    ) -> bool:
        """设置对抗检定结果"""
        check = self.get_opposed_check(check_id)
        if not check:
            return False

        if user_id == check.initiator_id:
            check.initiator_roll = roll
            check.initiator_target = target
            check.initiator_level = level
            return True
        elif user_id == check.target_id:
            check.target_roll = roll
            check.target_target = target
            check.target_level = level
            return True
        return False

    def _cleanup_expired(self) -> int:
        """清理过期检定，返回清理数量"""
        count = 0
        expired = [k for k, v in self._checks.items() if v.is_expired()]
        for k in expired:
            del self._checks[k]
            count += 1
        expired = [k for k, v in self._opposed_checks.items() if v.is_expired()]
        for k in expired:
            del self._opposed_checks[k]
            count += 1
        return count
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            "pending_checks": len(self._checks),
            "opposed_checks": len(self._opposed_checks)
        }
