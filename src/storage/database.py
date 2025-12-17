"""数据库连接管理 - 重构版"""
import json
from typing import Optional

import aiomysql

from ..character.models import Character
from .repositories import (
    CharacterRepository,
    NPCRepository,
    NotebookEntryRepository,
    NotebookRepository,
    ReviewRepository,
    UserSettingsRepository,
)


class Database:
    """
    MySQL 数据库管理器
    
    提供连接池管理、表结构初始化和仓库实例获取
    """

    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        database: str,
        min_pool_size: int = 1,
        max_pool_size: int = 10,
    ):
        self.host = host
        self.port = port
        self.user = user
        self._password = password  # 使用私有属性存储密码
        self.database = database
        self.min_pool_size = min_pool_size
        self.max_pool_size = max_pool_size
        
        self._pool: Optional[aiomysql.Pool] = None
        
        # 仓库实例（延迟初始化）
        self._character_repo: Optional[CharacterRepository] = None
        self._npc_repo: Optional[NPCRepository] = None
        self._user_settings_repo: Optional[UserSettingsRepository] = None
        self._review_repo: Optional[ReviewRepository] = None
        self._notebook_repo: Optional[NotebookRepository] = None
        self._notebook_entry_repo: Optional[NotebookEntryRepository] = None
    
    @property
    def password(self) -> str:
        """获取密码（内部使用）"""
        return self._password
    
    def __repr__(self) -> str:
        """安全的字符串表示，不暴露密码"""
        return f"Database(host={self.host!r}, port={self.port}, user={self.user!r}, database={self.database!r})"
    
    def __str__(self) -> str:
        """安全的字符串表示"""
        return self.__repr__()

    async def connect(self):
        """连接数据库，如果数据库不存在则自动创建"""
        await self._ensure_database_exists()
        
        self._pool = await aiomysql.create_pool(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            db=self.database,
            charset="utf8mb4",
            autocommit=True,
            minsize=self.min_pool_size,
            maxsize=self.max_pool_size,
        )
        await self._init_tables()
    
    async def _ensure_database_exists(self):
        """确保数据库存在，不存在则创建"""
        conn = await aiomysql.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            charset="utf8mb4",
            autocommit=True,
        )
        try:
            async with conn.cursor() as cur:
                await cur.execute(
                    f"CREATE DATABASE IF NOT EXISTS `{self.database}` "
                    f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
        finally:
            conn.close()

    async def close(self):
        """关闭连接池"""
        if self._pool:
            self._pool.close()
            await self._pool.wait_closed()
            self._pool = None
            
            # 清理仓库实例
            self._character_repo = None
            self._npc_repo = None
            self._user_settings_repo = None
            self._review_repo = None
            self._notebook_repo = None
            self._notebook_entry_repo = None

    @property
    def pool(self) -> aiomysql.Pool:
        """获取连接池"""
        if not self._pool:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self._pool

    # ===== 仓库实例获取 =====
    
    @property
    def characters(self) -> CharacterRepository:
        """获取角色仓库"""
        if not self._character_repo:
            self._character_repo = CharacterRepository(self.pool)
        return self._character_repo
    
    @property
    def npcs(self) -> NPCRepository:
        """获取 NPC 仓库"""
        if not self._npc_repo:
            self._npc_repo = NPCRepository(self.pool)
        return self._npc_repo
    
    @property
    def user_settings(self) -> UserSettingsRepository:
        """获取用户设置仓库"""
        if not self._user_settings_repo:
            self._user_settings_repo = UserSettingsRepository(self.pool)
        return self._user_settings_repo
    
    @property
    def reviews(self) -> ReviewRepository:
        """获取审核仓库"""
        if not self._review_repo:
            self._review_repo = ReviewRepository(self.pool)
        return self._review_repo
    
    @property
    def notebooks(self) -> NotebookRepository:
        """获取记事本仓库"""
        if not self._notebook_repo:
            self._notebook_repo = NotebookRepository(self.pool)
        return self._notebook_repo
    
    @property
    def notebook_entries(self) -> NotebookEntryRepository:
        """获取记事本条目仓库"""
        if not self._notebook_entry_repo:
            self._notebook_entry_repo = NotebookEntryRepository(self.pool)
        return self._notebook_entry_repo

    async def _init_tables(self):
        """初始化表结构"""
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    CREATE TABLE IF NOT EXISTS characters (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id VARCHAR(64) NOT NULL,
                        name VARCHAR(128) NOT NULL,
                        data JSON NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE KEY uk_user_name (user_id, name),
                        INDEX idx_user (user_id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)

                await cur.execute("""
                    CREATE TABLE IF NOT EXISTS user_settings (
                        user_id VARCHAR(64) PRIMARY KEY,
                        active_character VARCHAR(128),
                        rule_name VARCHAR(16) DEFAULT 'coc7',
                        critical_threshold INT DEFAULT 5,
                        fumble_threshold INT DEFAULT 96
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)

                await cur.execute("""
                    CREATE TABLE IF NOT EXISTS npcs (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        channel_id VARCHAR(64) NOT NULL,
                        name VARCHAR(128) NOT NULL,
                        template_id INT DEFAULT 1,
                        data JSON NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE KEY uk_channel_name (channel_id, name),
                        INDEX idx_channel (channel_id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)

                await cur.execute("""
                    CREATE TABLE IF NOT EXISTS character_reviews (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        char_name VARCHAR(128) NOT NULL UNIQUE,
                        user_id VARCHAR(64) NOT NULL,
                        image_data LONGTEXT,
                        image_url VARCHAR(512),
                        char_data JSON NOT NULL,
                        approved BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_user (user_id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)

                await cur.execute("""
                    CREATE TABLE IF NOT EXISTS notebooks (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        name VARCHAR(128) NOT NULL UNIQUE,
                        created_by VARCHAR(64) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)

                await cur.execute("""
                    CREATE TABLE IF NOT EXISTS notebook_entries (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        notebook_id INT NOT NULL,
                        content TEXT NOT NULL,
                        created_by VARCHAR(64) NOT NULL,
                        image_url VARCHAR(512),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_notebook (notebook_id),
                        FOREIGN KEY (notebook_id) REFERENCES notebooks(id) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)
                
                # 添加 image_url 列（如果不存在）
                await cur.execute("""
                    SELECT COUNT(*) FROM information_schema.COLUMNS 
                    WHERE TABLE_SCHEMA = DATABASE() 
                    AND TABLE_NAME = 'notebook_entries' 
                    AND COLUMN_NAME = 'image_url'
                """)
                row = await cur.fetchone()
                if row[0] == 0:
                    await cur.execute("""
                        ALTER TABLE notebook_entries 
                        ADD COLUMN image_url VARCHAR(512) AFTER created_by
                    """)

    # ===== 兼容旧接口 =====
    # 以下方法保持向后兼容，内部使用仓库实现

    async def save_character(self, char: Character):
        """保存角色卡"""
        await self.characters.save(char)

    async def get_character(self, user_id: str, name: str) -> Optional[Character]:
        """获取角色卡"""
        return await self.characters.find_by_user_and_name(user_id, name)

    async def list_characters(self, user_id: str):
        """列出用户所有角色卡"""
        return await self.characters.find_by_user(user_id)

    async def delete_character(self, user_id: str, name: str) -> bool:
        """删除角色卡"""
        return await self.characters.delete_by_user_and_name(user_id, name)

    async def get_active_character(self, user_id: str) -> Optional[str]:
        """获取当前激活角色名"""
        return await self.user_settings.get_active_character(user_id)

    async def set_active_character(self, user_id: str, name: str):
        """设置当前激活角色"""
        await self.user_settings.set_active_character(user_id, name)

    async def get_user_rule(self, user_id: str) -> dict:
        """获取用户规则设置"""
        return await self.user_settings.get_rule(user_id)

    async def set_user_rule(
        self,
        user_id: str,
        rule: str = None,
        critical: int = None,
        fumble: int = None,
    ):
        """设置用户规则"""
        await self.user_settings.set_rule(user_id, rule, critical, fumble)

    async def save_npc(self, channel_id: str, npc: Character, template_id: int = 1):
        """保存 NPC"""
        await self.npcs.save(channel_id, npc, template_id)

    async def get_npc(self, channel_id: str, name: str) -> Optional[Character]:
        """获取 NPC"""
        return await self.npcs.find_by_channel_and_name(channel_id, name)

    async def list_npcs(self, channel_id: str):
        """列出频道所有 NPC"""
        return await self.npcs.find_by_channel(channel_id)

    async def delete_npc(self, channel_id: str, name: str) -> bool:
        """删除 NPC"""
        return await self.npcs.delete_by_channel_and_name(channel_id, name)

    async def clear_channel_npcs(self, channel_id: str) -> int:
        """清空频道所有 NPC"""
        return await self.npcs.clear_channel(channel_id)

    async def save_character_review(
        self,
        char_name: str,
        user_id: str,
        image_data: str,
        char_data: dict,
        image_url: str = None,
    ):
        """保存角色卡审核记录"""
        from .repositories import CharacterReview
        review = CharacterReview(
            char_name=char_name,
            user_id=user_id,
            image_data=image_data,
            image_url=image_url,
            char_data=char_data,
            approved=False,
        )
        await self.reviews.save(review)

    async def get_character_review(self, char_name: str) -> Optional[dict]:
        """获取角色卡审核记录"""
        review = await self.reviews.find_by_char_name(char_name)
        if review:
            return {
                "char_name": review.char_name,
                "user_id": review.user_id,
                "image_data": review.image_data,
                "image_url": review.image_url,
                "char_data": review.char_data,
                "approved": review.approved,
                "created_at": review.created_at,
            }
        return None

    async def update_review_image_url(self, char_name: str, image_url: str):
        """更新审核记录的图片 URL"""
        await self.reviews.update_image_url(char_name, image_url)

    async def set_review_approved(self, char_name: str, approved: bool):
        """设置审核状态"""
        await self.reviews.set_approved(char_name, approved)

    async def delete_character_review(self, char_name: str) -> bool:
        """删除角色卡审核记录"""
        return await self.reviews.delete_by_char_name(char_name)

    async def cleanup_expired_reviews(self, expire_hours: int = 24) -> int:
        """清理过期的审核记录"""
        return await self.reviews.cleanup_expired(expire_hours)
