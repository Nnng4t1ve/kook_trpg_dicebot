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
    token: Optional[str] = None  # 创建链接token
    image_data: Optional[str] = None
    image_url: Optional[str] = None
    occupation_skills: Optional[List[str]] = None  # 本职技能列表
    random_sets: Optional[List[dict]] = None  # 随机属性组
    approved: bool = False
    status: int = 0  # 0=草稿/缓存中, 1=已提交待审核, 2=审核通过
    created_at: Optional[datetime] = None


class ReviewRepository(BaseRepository[CharacterReview]):
    """
    角色卡审核仓库
    
    表结构:
    - id: INT AUTO_INCREMENT PRIMARY KEY
    - char_name: VARCHAR(128) NOT NULL UNIQUE
    - user_id: VARCHAR(64) NOT NULL
    - token: VARCHAR(64) (创建链接token，带索引)
    - image_data: LONGTEXT
    - image_url: VARCHAR(512)
    - char_data: JSON NOT NULL
    - occupation_skills: JSON (本职技能列表)
    - random_sets: JSON (随机属性组)
    - approved: BOOLEAN DEFAULT FALSE
    - status: TINYINT DEFAULT 0 (0=草稿, 1=已提交, 2=审核通过)
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
            token=row_dict.get("token"),
            image_data=row_dict.get("image_data"),
            image_url=row_dict.get("image_url"),
            char_data=self._deserialize_json(row_dict.get("char_data", "{}")),
            occupation_skills=self._deserialize_json(
                row_dict.get("occupation_skills", "[]")
            ),
            random_sets=self._deserialize_json(row_dict.get("random_sets", "[]")),
            approved=bool(row_dict.get("approved", False)),
            status=int(row_dict.get("status", 0)),
            created_at=row_dict.get("created_at"),
        )

    def _model_to_row(self, entity: CharacterReview) -> Dict[str, Any]:
        """将 CharacterReview 对象转换为数据库行"""
        return {
            "char_name": entity.char_name,
            "user_id": entity.user_id,
            "token": entity.token,
            "image_data": entity.image_data,
            "image_url": entity.image_url,
            "char_data": self._serialize_json(entity.char_data),
            "occupation_skills": self._serialize_json(entity.occupation_skills or []),
            "random_sets": self._serialize_json(entity.random_sets or []),
            "approved": entity.approved,
            "status": entity.status,
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

    async def find_by_token(self, token: str) -> Optional[CharacterReview]:
        """
        根据token查询缓存记录（使用索引，高效查询）
        
        Args:
            token: 创建链接的token
        
        Returns:
            审核记录或 None
        """
        return await self.find_one(token=token)

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
            (char_name, user_id, token, image_data, image_url, char_data, occupation_skills, random_sets, approved, status) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) AS new_values
            ON DUPLICATE KEY UPDATE 
            token = new_values.token,
            image_data = new_values.image_data,
            image_url = new_values.image_url,
            char_data = new_values.char_data,
            occupation_skills = new_values.occupation_skills,
            random_sets = new_values.random_sets,
            approved = new_values.approved,
            status = new_values.status,
            created_at = CURRENT_TIMESTAMP
        """
        return await self.execute(
            sql,
            (
                review.char_name,
                review.user_id,
                review.token,
                review.image_data,
                review.image_url,
                self._serialize_json(review.char_data),
                self._serialize_json(review.occupation_skills or []),
                self._serialize_json(review.random_sets or []),
                review.approved,
                review.status,
            ),
        )

    async def save_draft(self, review: CharacterReview) -> int:
        """
        保存草稿（仅当状态为草稿时才更新，防止覆盖已提交的数据）
        
        Args:
            review: 审核记录对象
        
        Returns:
            受影响的行数
        """
        sql = """
            INSERT INTO character_reviews 
            (char_name, user_id, token, image_data, image_url, char_data, occupation_skills, random_sets, approved, status) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) AS new_values
            ON DUPLICATE KEY UPDATE 
            token = CASE WHEN character_reviews.status = 0 THEN new_values.token ELSE character_reviews.token END,
            char_data = CASE WHEN character_reviews.status = 0 THEN new_values.char_data ELSE character_reviews.char_data END,
            occupation_skills = CASE WHEN character_reviews.status = 0 THEN new_values.occupation_skills ELSE character_reviews.occupation_skills END,
            random_sets = CASE WHEN character_reviews.status = 0 THEN new_values.random_sets ELSE character_reviews.random_sets END,
            created_at = CASE WHEN character_reviews.status = 0 THEN CURRENT_TIMESTAMP ELSE character_reviews.created_at END
        """
        return await self.execute(
            sql,
            (
                review.char_name,
                review.user_id,
                review.token,
                review.image_data,
                review.image_url,
                self._serialize_json(review.char_data),
                self._serialize_json(review.occupation_skills or []),
                self._serialize_json(review.random_sets or []),
                review.approved,
                review.status,
            ),
        )

    async def set_status(self, char_name: str, status: int) -> int:
        """
        设置审核状态码
        
        Args:
            char_name: 角色名
            status: 状态码 (0=草稿, 1=已提交, 2=审核通过)
        
        Returns:
            受影响的行数
        """
        sql = "UPDATE character_reviews SET status = %s WHERE char_name = %s"
        return await self.execute(sql, (status, char_name))
    
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
    
    async def cleanup_expired(self, expire_hours: int = 72) -> int:
        """
        清理过期的审核记录（默认3天）
        
        Args:
            expire_hours: 过期时间（小时），默认72小时（3天）
        
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
