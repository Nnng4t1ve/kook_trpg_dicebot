"""角色卡审核仓库"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from .base import BaseRepository


@dataclass
class CharacterReview:
    """角色卡审核数据模型"""
    char_name: str
    user_id: str
    char_data: dict
    image_data: Optional[str] = None
    image_url: Optional[str] = None
    approved: bool = False
    created_at: Optional[datetime] = None


class ReviewRepository(BaseRepository[CharacterReview]):
    """
    角色卡审核仓库
    
    表结构:
    - id: INT AUTO_INCREMENT PRIMARY KEY
    - char_name: VARCHAR(128) NOT NULL UNIQUE
    - user_id: VARCHAR(64) NOT NULL
    - image_data: LONGTEXT
    - image_url: VARCHAR(512)
    - char_data: JSON NOT NULL
    - approved: BOOLEAN DEFAULT FALSE
    - created_at: TIMESTAMP
    """
    
    table_name = "character_reviews"
    model_class = CharacterReview
    
    def _row_to_model(self, row: tuple, columns: List[str]) -> CharacterReview:
        """将数据库行转换为 CharacterReview 对象"""
        row_dict = dict(zip(columns, row))
        return CharacterReview(
            char_name=row_dict["char_name"],
            user_id=row_dict["user_id"],
            image_data=row_dict.get("image_data"),
            image_url=row_dict.get("image_url"),
            char_data=self._deserialize_json(row_dict.get("char_data", "{}")),
            approved=bool(row_dict.get("approved", False)),
            created_at=row_dict.get("created_at"),
        )
    
    def _model_to_row(self, entity: CharacterReview) -> Dict[str, Any]:
        """将 CharacterReview 对象转换为数据库行"""
        return {
            "char_name": entity.char_name,
            "user_id": entity.user_id,
            "image_data": entity.image_data,
            "image_url": entity.image_url,
            "char_data": self._serialize_json(entity.char_data),
            "approved": entity.approved,
        }
    
    async def find_by_char_name(self, char_name: str) -> Optional[CharacterReview]:
        """
        根据角色名查询审核记录
        
        Args:
            char_name: 角色名
        
        Returns:
            审核记录或 None
        """
        return await self.find_one(char_name=char_name)
    
    async def find_by_user(self, user_id: str) -> List[CharacterReview]:
        """
        查询用户所有审核记录
        
        Args:
            user_id: 用户 ID
        
        Returns:
            审核记录列表
        """
        return await self.find_many(user_id=user_id)
    
    async def save(self, review: CharacterReview) -> int:
        """
        保存审核记录（插入或更新）
        
        Args:
            review: 审核记录对象
        
        Returns:
            受影响的行数
        """
        sql = """
            INSERT INTO character_reviews 
            (char_name, user_id, image_data, image_url, char_data, approved) 
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE 
            image_data = VALUES(image_data),
            image_url = VALUES(image_url),
            char_data = VALUES(char_data),
            approved = VALUES(approved),
            created_at = CURRENT_TIMESTAMP
        """
        return await self.execute(
            sql,
            (
                review.char_name,
                review.user_id,
                review.image_data,
                review.image_url,
                self._serialize_json(review.char_data),
                review.approved,
            ),
        )
    
    async def update_image_url(self, char_name: str, image_url: str) -> int:
        """
        更新审核记录的图片 URL
        
        Args:
            char_name: 角色名
            image_url: 图片 URL
        
        Returns:
            受影响的行数
        """
        sql = "UPDATE character_reviews SET image_url = %s WHERE char_name = %s"
        return await self.execute(sql, (image_url, char_name))
    
    async def set_approved(self, char_name: str, approved: bool) -> int:
        """
        设置审核状态
        
        Args:
            char_name: 角色名
            approved: 是否通过
        
        Returns:
            受影响的行数
        """
        sql = "UPDATE character_reviews SET approved = %s WHERE char_name = %s"
        return await self.execute(sql, (approved, char_name))
    
    async def delete_by_char_name(self, char_name: str) -> bool:
        """
        删除审核记录
        
        Args:
            char_name: 角色名
        
        Returns:
            是否删除成功
        """
        count = await self.delete(char_name=char_name)
        return count > 0
    
    async def cleanup_expired(self, expire_hours: int = 24) -> int:
        """
        清理过期的审核记录
        
        Args:
            expire_hours: 过期时间（小时）
        
        Returns:
            删除的数量
        """
        sql = """
            DELETE FROM character_reviews 
            WHERE created_at < DATE_SUB(NOW(), INTERVAL %s HOUR)
        """
        return await self.execute(sql, (expire_hours,))
    
    async def find_pending(self) -> List[CharacterReview]:
        """
        查询待审核记录
        
        Returns:
            待审核记录列表
        """
        return await self.find_many(approved=False, order_by="created_at DESC")
