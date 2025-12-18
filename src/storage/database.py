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
                        INDEX idx_user (user_id),
                        INDEX idx_created_at (created_at)
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

                # 机器人设置表（存储管理员等全局配置）
                await cur.execute("""
                    CREATE TABLE IF NOT EXISTS bot_settings (
                        `key` VARCHAR(64) PRIMARY KEY,
                        `value` VARCHAR(256) NOT NULL,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)

                # 预定时间投票表
                await cur.execute("""
                    CREATE TABLE IF NOT EXISTS schedule_votes (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        vote_id VARCHAR(32) NOT NULL UNIQUE,
                        schedule_time DATETIME NOT NULL,
                        mentioned_users JSON NOT NULL,
                        description TEXT,
                        initiator_id VARCHAR(64) NOT NULL,
                        initiator_name VARCHAR(128) NOT NULL,
                        channel_id VARCHAR(64) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_vote_id (vote_id),
                        INDEX idx_channel (channel_id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)

                # 预定时间投票记录表
                await cur.execute("""
                    CREATE TABLE IF NOT EXISTS schedule_vote_records (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        vote_id VARCHAR(32) NOT NULL,
                        user_name VARCHAR(128) NOT NULL,
                        user_id VARCHAR(64) NOT NULL,
                        choice ENUM('agree', 'reject') NOT NULL,
                        voted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE KEY uk_vote_user (vote_id, user_name),
                        INDEX idx_vote_id (vote_id),
                        FOREIGN KEY (vote_id) REFERENCES schedule_votes(vote_id) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)

                # 游戏日志表
                await cur.execute("""
                    CREATE TABLE IF NOT EXISTS game_logs (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        log_name VARCHAR(128) NOT NULL UNIQUE,
                        channel_id VARCHAR(64) NOT NULL,
                        initiator_id VARCHAR(64) NOT NULL,
                        participants JSON NOT NULL,
                        started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        ended_at TIMESTAMP NULL,
                        INDEX idx_channel (channel_id),
                        INDEX idx_log_name (log_name)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)

                # 游戏日志条目表
                await cur.execute("""
                    CREATE TABLE IF NOT EXISTS game_log_entries (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        log_name VARCHAR(128) NOT NULL,
                        user_id VARCHAR(64) NOT NULL,
                        user_name VARCHAR(128) NOT NULL,
                        content TEXT NOT NULL,
                        msg_type VARCHAR(16) DEFAULT 'text',
                        is_bot BOOLEAN DEFAULT FALSE,
                        roll_result JSON NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_log_name (log_name),
                        INDEX idx_user (user_id),
                        FOREIGN KEY (log_name) REFERENCES game_logs(log_name) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
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

    # ===== 机器人设置 =====

    async def get_bot_admin(self) -> str | None:
        """获取机器人管理员 ID"""
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT `value` FROM bot_settings WHERE `key` = 'admin_id'"
                )
                row = await cur.fetchone()
                return row[0] if row else None

    async def set_bot_admin(self, user_id: str):
        """设置机器人管理员 ID（仅首次有效）"""
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                # 使用 INSERT IGNORE 确保只有首次插入成功
                await cur.execute(
                    "INSERT IGNORE INTO bot_settings (`key`, `value`) VALUES ('admin_id', %s)",
                    (user_id,)
                )

    async def get_bot_id(self) -> str | None:
        """获取机器人自身 ID"""
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT `value` FROM bot_settings WHERE `key` = 'bot_id'"
                )
                row = await cur.fetchone()
                return row[0] if row else None

    async def set_bot_id(self, bot_id: str):
        """设置机器人自身 ID"""
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "INSERT INTO bot_settings (`key`, `value`) VALUES ('bot_id', %s) AS new_val "
                    "ON DUPLICATE KEY UPDATE `value` = new_val.`value`",
                    (bot_id,)
                )
    # ===== 预定时间投票 =====

    async def create_schedule_vote(
        self,
        vote_id: str,
        schedule_time,
        mentioned_users: list[str],
        description: str,
        initiator_id: str,
        initiator_name: str,
        channel_id: str,
    ):
        """创建预定时间投票"""
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    INSERT INTO schedule_votes 
                    (vote_id, schedule_time, mentioned_users, description, initiator_id, initiator_name, channel_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    vote_id,
                    schedule_time,
                    json.dumps(mentioned_users),
                    description,
                    initiator_id,
                    initiator_name,
                    channel_id
                ))

    async def get_schedule_vote(self, vote_id: str) -> Optional[dict]:
        """获取预定时间投票信息"""
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    SELECT vote_id, schedule_time, mentioned_users, description, 
                           initiator_id, initiator_name, channel_id, created_at
                    FROM schedule_votes 
                    WHERE vote_id = %s
                """, (vote_id,))
                row = await cur.fetchone()
                if row:
                    return {
                        "vote_id": row[0],
                        "schedule_time": row[1],
                        "mentioned_users": json.loads(row[2]),
                        "description": row[3],
                        "initiator_id": row[4],
                        "initiator_name": row[5],
                        "channel_id": row[6],
                        "created_at": row[7],
                    }
                return None

    async def record_schedule_vote(
        self, vote_id: str, user_name: str, choice: str, user_id: str
    ):
        """记录用户投票"""
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    INSERT INTO schedule_vote_records 
                    (vote_id, user_name, user_id, choice)
                    VALUES (%s, %s, %s, %s) AS new_val
                    ON DUPLICATE KEY UPDATE 
                    choice = new_val.choice, voted_at = CURRENT_TIMESTAMP
                """, (vote_id, user_name, user_id, choice))

    async def get_schedule_votes(self, vote_id: str) -> dict:
        """获取投票记录"""
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    SELECT user_name, user_id, choice, voted_at
                    FROM schedule_vote_records 
                    WHERE vote_id = %s
                """, (vote_id,))
                rows = await cur.fetchall()
                
                votes = {}
                for row in rows:
                    votes[row[0]] = {
                        "user_id": row[1],
                        "choice": row[2],
                        "voted_at": row[3],
                    }
                return votes

    async def cleanup_expired_schedule_votes(self, expire_hours: int = 72) -> int:
        """清理过期的投票记录"""
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                # 删除过期的投票（默认72小时后过期）
                await cur.execute("""
                    DELETE FROM schedule_votes 
                    WHERE created_at < DATE_SUB(NOW(), INTERVAL %s HOUR)
                """, (expire_hours,))
                return cur.rowcount


    # ===== 游戏日志 =====

    async def create_game_log(
        self,
        log_name: str,
        channel_id: str,
        initiator_id: str,
        participants: list[str],
    ):
        """创建游戏日志"""
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO game_logs (log_name, channel_id, initiator_id, participants)
                    VALUES (%s, %s, %s, %s)
                """,
                    (log_name, channel_id, initiator_id, json.dumps(participants)),
                )

    async def end_game_log(self, log_name: str):
        """结束游戏日志"""
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    UPDATE game_logs SET ended_at = CURRENT_TIMESTAMP WHERE log_name = %s
                """,
                    (log_name,),
                )

    async def get_game_log(self, log_name: str) -> Optional[dict]:
        """获取游戏日志信息"""
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT log_name, channel_id, initiator_id, participants, 
                           started_at, ended_at,
                           (SELECT COUNT(*) FROM game_log_entries WHERE log_name = g.log_name) as entry_count
                    FROM game_logs g WHERE log_name = %s
                """,
                    (log_name,),
                )
                row = await cur.fetchone()
                if row:
                    return {
                        "log_name": row[0],
                        "channel_id": row[1],
                        "initiator_id": row[2],
                        "participants": json.loads(row[3]),
                        "started_at": row[4],
                        "ended_at": row[5],
                        "entry_count": row[6],
                    }
                return None

    async def list_game_logs(
        self, channel_id: str, page: int = 1, page_size: int = 10
    ) -> tuple[list[dict], int]:
        """列出频道的游戏日志"""
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                # 获取总数
                await cur.execute(
                    "SELECT COUNT(*) FROM game_logs WHERE channel_id = %s",
                    (channel_id,),
                )
                total = (await cur.fetchone())[0]

                # 获取分页数据
                offset = (page - 1) * page_size
                await cur.execute(
                    """
                    SELECT g.log_name, g.initiator_id, g.started_at, g.ended_at,
                           (SELECT COUNT(*) FROM game_log_entries WHERE log_name = g.log_name) as entry_count
                    FROM game_logs g
                    WHERE g.channel_id = %s
                    ORDER BY g.started_at DESC
                    LIMIT %s OFFSET %s
                """,
                    (channel_id, page_size, offset),
                )
                rows = await cur.fetchall()

                logs = []
                for row in rows:
                    logs.append(
                        {
                            "log_name": row[0],
                            "initiator_id": row[1],
                            "started_at": row[2],
                            "ended_at": row[3],
                            "entry_count": row[4],
                        }
                    )

                return logs, total

    async def add_game_log_entry(
        self,
        log_name: str,
        user_id: str,
        user_name: str,
        content: str,
        msg_type: str = "text",
        is_bot: bool = False,
        roll_result: dict = None,
    ):
        """添加日志条目"""
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO game_log_entries 
                    (log_name, user_id, user_name, content, msg_type, is_bot, roll_result)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                    (
                        log_name,
                        user_id,
                        user_name,
                        content,
                        msg_type,
                        is_bot,
                        json.dumps(roll_result) if roll_result else None,
                    ),
                )

    async def get_game_log_entries(self, log_name: str) -> list[dict]:
        """获取日志所有条目"""
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT user_id, user_name, content, msg_type, is_bot, roll_result, created_at
                    FROM game_log_entries
                    WHERE log_name = %s
                    ORDER BY created_at ASC
                """,
                    (log_name,),
                )
                rows = await cur.fetchall()

                entries = []
                for row in rows:
                    entries.append(
                        {
                            "user_id": row[0],
                            "user_name": row[1],
                            "content": row[2],
                            "msg_type": row[3],
                            "is_bot": row[4],
                            "roll_result": json.loads(row[5]) if row[5] else None,
                            "created_at": row[6].isoformat() if row[6] else None,
                        }
                    )

                return entries

    async def get_game_log_stats(self, log_name: str) -> dict:
        """获取日志统计信息"""
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT COUNT(*) FROM game_log_entries WHERE log_name = %s",
                    (log_name,),
                )
                total = (await cur.fetchone())[0]
                return {"total_entries": total}

    async def analyze_game_log(self, log_name: str) -> dict:
        """分析日志统计数据 - 从消息内容中解析骰点结果"""
        import re

        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                # 获取所有非Bot用户发送的骰点命令的下一条Bot回复
                await cur.execute(
                    """
                    SELECT user_id, user_name, content, is_bot
                    FROM game_log_entries
                    WHERE log_name = %s
                    ORDER BY created_at ASC
                """,
                    (log_name,),
                )
                rows = await cur.fetchall()

                # 统计每个用户的骰点结果
                user_stats: dict[str, dict] = {}
                
                # 遍历消息，找到用户的骰点命令和对应的Bot回复
                last_user_id = None
                last_user_name = None
                
                for row in rows:
                    user_id = row[0]
                    user_name = row[1]
                    content = row[2]
                    is_bot = row[3]
                    
                    # 如果是用户发送的骰点命令，记录用户信息
                    if not is_bot and content.startswith((".ra", ".rc", "。ra", "。rc", "/ra", "/rc")):
                        last_user_id = user_id
                        last_user_name = user_name
                        continue
                    
                    # 如果是Bot回复且有上一个用户的骰点命令
                    if is_bot and last_user_id and "检定" in content:
                        # 解析骰点结果
                        result_level = self._parse_roll_result(content)
                        
                        if result_level:
                            if last_user_id not in user_stats:
                                user_stats[last_user_id] = {
                                    "user_name": last_user_name,
                                    "total_rolls": 0,
                                    "success": 0,
                                    "failure": 0,
                                    "critical": 0,
                                    "fumble": 0,
                                }
                            
                            stats = user_stats[last_user_id]
                            stats["total_rolls"] += 1
                            
                            if result_level == "大成功":
                                stats["critical"] += 1
                                stats["success"] += 1
                            elif result_level == "大失败":
                                stats["fumble"] += 1
                                stats["failure"] += 1
                            elif result_level in ("成功", "困难成功", "极难成功"):
                                stats["success"] += 1
                            elif result_level == "失败":
                                stats["failure"] += 1
                        
                        # 重置，避免重复计算
                        last_user_id = None
                        last_user_name = None

                # 找出各项最多的用户
                most_success = max(user_stats.values(), key=lambda x: x["success"], default=None)
                most_failure = max(user_stats.values(), key=lambda x: x["failure"], default=None)
                most_critical = max(user_stats.values(), key=lambda x: x["critical"], default=None)
                most_fumble = max(user_stats.values(), key=lambda x: x["fumble"], default=None)

                return {
                    "user_stats": user_stats,
                    "most_success": most_success,
                    "most_failure": most_failure,
                    "most_critical": most_critical,
                    "most_fumble": most_fumble,
                    "total_rolls": sum(s["total_rolls"] for s in user_stats.values()),
                }

    def _parse_roll_result(self, content: str) -> Optional[str]:
        """从Bot回复内容中解析骰点结果等级"""
        import re
        
        # 匹配 [大成功], [大失败], [成功], [失败], [困难成功], [极难成功]
        match = re.search(r"\[(大成功|大失败|极难成功|困难成功|成功|失败)\]", content)
        if match:
            return match.group(1)
        return None
