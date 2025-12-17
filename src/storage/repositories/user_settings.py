"""用户设置仓库"""
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .base import BaseRepository


@dataclass
class UserSettings:
    """用户设置数据模型"""
    user_id: str
    active_character: Optional[str] = None
    rule_name: str = "coc7"
    critical_threshold: int = 5
    fumble_threshold: int = 96


class UserSettingsRepository(BaseRepository[UserSettings]):
    """
    用户设置仓库
    
    表结构:
    - user_id: VARCHAR(64) PRIMARY KEY
    - active_character: VARCHAR(128)
    - rule_name: VARCHAR(16) DEFAULT 'coc7'
    - critical_threshold: INT DEFAULT 5
    - fumble_threshold: INT DEFAULT 96
    """
    
    table_name = "user_settings"
    model_class = UserSettings
    
    def _row_to_model(self, row: tuple, columns: List[str]) -> UserSettings:
        """将数据库行转换为 UserSettings 对象"""
        row_dict = dict(zip(columns, row))
        return UserSettings(
            user_id=row_dict["user_id"],
            active_character=row_dict.get("active_character"),
            rule_name=row_dict.get("rule_name", "coc7"),
            critical_threshold=row_dict.get("critical_threshold", 5),
            fumble_threshold=row_dict.get("fumble_threshold", 96),
        )
    
    def _model_to_row(self, entity: UserSettings) -> Dict[str, Any]:
        """将 UserSettings 对象转换为数据库行"""
        return {
            "user_id": entity.user_id,
            "active_character": entity.active_character,
            "rule_name": entity.rule_name,
            "critical_threshold": entity.critical_threshold,
            "fumble_threshold": entity.fumble_threshold,
        }
    
    async def get_or_create(self, user_id: str) -> UserSettings:
        """
        获取用户设置，不存在则创建默认设置
        
        Args:
            user_id: 用户 ID
        
        Returns:
            用户设置对象
        """
        settings = await self.find_one(user_id=user_id)
        if settings:
            return settings
        
        # 创建默认设置
        settings = UserSettings(user_id=user_id)
        await self.insert(settings)
        return settings
    
    async def get_rule(self, user_id: str) -> dict:
        """
        获取用户规则设置
        
        Args:
            user_id: 用户 ID
        
        Returns:
            规则设置字典 {"rule": str, "critical": int, "fumble": int}
        """
        settings = await self.get_or_create(user_id)
        return {
            "rule": settings.rule_name,
            "critical": settings.critical_threshold,
            "fumble": settings.fumble_threshold,
        }
    
    async def set_rule(
        self,
        user_id: str,
        rule: str = None,
        critical: int = None,
        fumble: int = None,
    ) -> UserSettings:
        """
        设置用户规则
        
        Args:
            user_id: 用户 ID
            rule: 规则名称
            critical: 大成功阈值
            fumble: 大失败阈值
        
        Returns:
            更新后的用户设置
        """
        settings = await self.get_or_create(user_id)
        
        if rule is not None:
            settings.rule_name = rule
        if critical is not None:
            settings.critical_threshold = critical
        if fumble is not None:
            settings.fumble_threshold = fumble
        
        await self.upsert(settings, unique_keys=["user_id"])
        return settings
    
    async def get_active_character(self, user_id: str) -> Optional[str]:
        """
        获取当前激活角色名
        
        Args:
            user_id: 用户 ID
        
        Returns:
            角色名或 None
        """
        settings = await self.find_one(user_id=user_id)
        return settings.active_character if settings else None
    
    async def set_active_character(self, user_id: str, name: str) -> None:
        """
        设置当前激活角色
        
        Args:
            user_id: 用户 ID
            name: 角色名
        """
        settings = await self.get_or_create(user_id)
        settings.active_character = name
        await self.upsert(settings, unique_keys=["user_id"])
