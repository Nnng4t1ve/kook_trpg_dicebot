"""NPC 数据仓库"""
from typing import Any, Dict, List, Optional

from ...character.models import Character
from .base import BaseRepository


class NPCRepository(BaseRepository[Character]):
    """
    NPC 数据仓库
    
    表结构:
    - id: INT AUTO_INCREMENT PRIMARY KEY
    - channel_id: VARCHAR(64) NOT NULL
    - name: VARCHAR(128) NOT NULL
    - template_id: INT DEFAULT 1
    - data: JSON NOT NULL
    - created_at: TIMESTAMP
    """
    
    table_name = "npcs"
    model_class = Character
    
    def _row_to_model(self, row: tuple, columns: List[str]) -> Character:
        """将数据库行转换为 Character 对象"""
        row_dict = dict(zip(columns, row))
        data = self._deserialize_json(row_dict.get("data", "{}"))
        return Character.from_dict(data)
    
    def _model_to_row(self, entity: Character, channel_id: str = None, template_id: int = 1) -> Dict[str, Any]:
        """将 Character 对象转换为数据库行"""
        return {
            "channel_id": channel_id or "",
            "name": entity.name,
            "template_id": template_id,
            "data": entity.to_json(),
        }
    
    async def find_by_channel(self, channel_id: str) -> List[Character]:
        """
        查询频道所有 NPC
        
        Args:
            channel_id: 频道 ID
        
        Returns:
            NPC 列表
        """
        return await self.find_many(channel_id=channel_id)
    
    async def find_by_channel_and_name(
        self, channel_id: str, name: str
    ) -> Optional[Character]:
        """
        查询指定 NPC
        
        Args:
            channel_id: 频道 ID
            name: NPC 名称
        
        Returns:
            NPC 对象或 None
        """
        return await self.find_one(channel_id=channel_id, name=name)
    
    async def save(
        self, channel_id: str, npc: Character, template_id: int = 1
    ) -> int:
        """
        保存 NPC（插入或更新）
        
        Args:
            channel_id: 频道 ID
            npc: NPC 对象
            template_id: 模板 ID
        
        Returns:
            受影响的行数
        """
        sql = """
            INSERT INTO npcs (channel_id, name, template_id, data) 
            VALUES (%s, %s, %s, %s) AS new_values
            ON DUPLICATE KEY UPDATE 
            template_id = new_values.template_id,
            data = new_values.data
        """
        return await self.execute(
            sql, (channel_id, npc.name, template_id, npc.to_json())
        )
    
    async def delete_by_channel_and_name(
        self, channel_id: str, name: str
    ) -> bool:
        """
        删除指定 NPC
        
        Args:
            channel_id: 频道 ID
            name: NPC 名称
        
        Returns:
            是否删除成功
        """
        count = await self.delete(channel_id=channel_id, name=name)
        return count > 0
    
    async def clear_channel(self, channel_id: str) -> int:
        """
        清空频道所有 NPC
        
        Args:
            channel_id: 频道 ID
        
        Returns:
            删除的数量
        """
        return await self.delete(channel_id=channel_id)
    
    async def count_by_channel(self, channel_id: str) -> int:
        """
        统计频道 NPC 数量
        
        Args:
            channel_id: 频道 ID
        
        Returns:
            NPC 数量
        """
        return await self.count(channel_id=channel_id)
