"""检定管理器 - 管理 KP 发起的检定"""
import uuid
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Set


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


class CheckManager:
    """检定管理器"""
    
    def __init__(self):
        self._checks: Dict[str, PendingCheck] = {}
    
    def create_check(
        self,
        skill_name: str,
        channel_id: str,
        kp_id: str,
        target_value: Optional[int] = None
    ) -> PendingCheck:
        """创建新检定"""
        check_id = str(uuid.uuid4())[:8]
        check = PendingCheck(
            check_id=check_id,
            skill_name=skill_name,
            channel_id=channel_id,
            kp_id=kp_id,
            created_at=time.time(),
            target_value=target_value
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
    
    def _cleanup_expired(self):
        """清理过期检定"""
        expired = [k for k, v in self._checks.items() if v.is_expired()]
        for k in expired:
            del self._checks[k]
