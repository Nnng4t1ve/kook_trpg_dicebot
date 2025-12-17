"""角色数据仓库"""
from typing import Any, Dict, List, Optional

from ...character.models import Character
from .base import BaseRepository


class CharacterRepository(BaseRepository[Character]):
    """
    角色数据仓库
    
    表结构:
    - id: INT AUTO_INCREMENT PRIMARY KEY
    - user_id: VARCHAR(64) NOT NULL
    - name: VARCHAR(128) NOT NULL
    - data: JSON NOT NULL
    - created_at: TIMESTAMP
    """
    
    table_name = "characters"
    model_class = Character
    
    def _row_to_model(self, row: tuple, columns: List[str]) -> Character:
        """将数据库行转换为 Character 对象"""
        row_dict = dict(zip(columns, row))
        data = self._deserialize_json(row_dict.get("data", "{}"))
        return Character.from_dict(data)
    
    def _model_to_row(self, entity: Character) -> Dict[str, Any]:
        """将 Character 对象转换为数据库行"""
        return {
            "user_id": entity.user_id,
            "name": entity.name,
            "data": entity.to_json(),
        }
    
    async def find_by_user(self, user_id: str) -> List[Character]:
        """
        查询用户所有角色
        
        Args:
            user_id: 用户 ID
        
        Returns:
            角色列表
        """
        return await self.find_many(user_id=user_id)
    
    async def find_by_user_and_name(
        self, user_id: str, name: str
    ) -> Optional[Character]:
        """
        查询指定角色
        
        Args:
            user_id: 用户 ID
            name: 角色名
        
        Returns:
            角色对象或 None
        """
        return await self.find_one(user_id=user_id, name=name)
    
    async def save(self, char: Character) -> int:
        """
        保存角色（插入或更新）
        
        Args:
            char: 角色对象
        
        Returns:
            受影响的行数
        """
        return await self.upsert(char, unique_keys=["user_id", "name"])
    
    async def delete_by_user_and_name(self, user_id: str, name: str) -> bool:
        """
        删除指定角色
        
        Args:
            user_id: 用户 ID
            name: 角色名
        
        Returns:
            是否删除成功
        """
        count = await self.delete(user_id=user_id, name=name)
        return count > 0
    
    async def count_by_user(self, user_id: str) -> int:
        """
        统计用户角色数量
        
        Args:
            user_id: 用户 ID
        
        Returns:
            角色数量
        """
        return await self.count(user_id=user_id)
