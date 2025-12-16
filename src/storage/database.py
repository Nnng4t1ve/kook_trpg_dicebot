"""数据库操作 - MySQL"""
import json
import aiomysql
from typing import List, Optional
from ..character.models import Character


class Database:
    """MySQL 数据库操作"""

    def __init__(self, host: str, port: int, user: str, password: str, database: str):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self._pool: Optional[aiomysql.Pool] = None

    async def connect(self):
        """连接数据库，如果数据库不存在则自动创建"""
        # 先连接不指定数据库，创建数据库
        await self._ensure_database_exists()
        
        # 再连接到指定数据库
        self._pool = await aiomysql.create_pool(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            db=self.database,
            charset="utf8mb4",
            autocommit=True,
            minsize=1,
            maxsize=10,
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

    async def save_character(self, char: Character):
        """保存角色卡"""
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """INSERT INTO characters (user_id, name, data) 
                       VALUES (%s, %s, %s) AS new_data
                       ON DUPLICATE KEY UPDATE data = new_data.data""",
                    (char.user_id, char.name, char.to_json()),
                )

    async def get_character(self, user_id: str, name: str) -> Optional[Character]:
        """获取角色卡"""
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT data FROM characters WHERE user_id = %s AND name = %s",
                    (user_id, name),
                )
                row = await cur.fetchone()
                if row:
                    data = json.loads(row[0]) if isinstance(row[0], str) else row[0]
                    return Character.from_dict(data)
        return None

    async def list_characters(self, user_id: str) -> List[Character]:
        """列出用户所有角色卡"""
        chars = []
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT data FROM characters WHERE user_id = %s", (user_id,)
                )
                rows = await cur.fetchall()
                for row in rows:
                    data = json.loads(row[0]) if isinstance(row[0], str) else row[0]
                    chars.append(Character.from_dict(data))
        return chars

    async def delete_character(self, user_id: str, name: str) -> bool:
        """删除角色卡"""
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "DELETE FROM characters WHERE user_id = %s AND name = %s",
                    (user_id, name),
                )
                return cur.rowcount > 0

    async def get_active_character(self, user_id: str) -> Optional[str]:
        """获取当前激活角色名"""
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT active_character FROM user_settings WHERE user_id = %s",
                    (user_id,),
                )
                row = await cur.fetchone()
                return row[0] if row else None

    async def set_active_character(self, user_id: str, name: str):
        """设置当前激活角色"""
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """INSERT INTO user_settings (user_id, active_character) 
                       VALUES (%s, %s) AS new_data
                       ON DUPLICATE KEY UPDATE active_character = new_data.active_character""",
                    (user_id, name),
                )

    async def get_user_rule(self, user_id: str) -> dict:
        """获取用户规则设置"""
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """SELECT rule_name, critical_threshold, fumble_threshold 
                       FROM user_settings WHERE user_id = %s""",
                    (user_id,),
                )
                row = await cur.fetchone()
                if row:
                    return {"rule": row[0], "critical": row[1], "fumble": row[2]}
        return {"rule": "coc7", "critical": 5, "fumble": 96}

    async def set_user_rule(
        self,
        user_id: str,
        rule: str = None,
        critical: int = None,
        fumble: int = None,
    ):
        """设置用户规则"""
        current = await self.get_user_rule(user_id)
        rule = rule or current["rule"]
        critical = critical if critical is not None else current["critical"]
        fumble = fumble if fumble is not None else current["fumble"]

        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """INSERT INTO user_settings 
                       (user_id, rule_name, critical_threshold, fumble_threshold)
                       VALUES (%s, %s, %s, %s) AS new_data
                       ON DUPLICATE KEY UPDATE 
                       rule_name = new_data.rule_name,
                       critical_threshold = new_data.critical_threshold,
                       fumble_threshold = new_data.fumble_threshold""",
                    (user_id, rule, critical, fumble),
                )


    # ===== NPC 操作 =====

    async def save_npc(self, channel_id: str, npc: Character, template_id: int = 1):
        """保存 NPC"""
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """INSERT INTO npcs (channel_id, name, template_id, data) 
                       VALUES (%s, %s, %s, %s) AS new_data
                       ON DUPLICATE KEY UPDATE 
                       template_id = new_data.template_id,
                       data = new_data.data""",
                    (channel_id, npc.name, template_id, npc.to_json()),
                )

    async def get_npc(self, channel_id: str, name: str) -> Optional[Character]:
        """获取 NPC"""
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT data FROM npcs WHERE channel_id = %s AND name = %s",
                    (channel_id, name),
                )
                row = await cur.fetchone()
                if row:
                    data = json.loads(row[0]) if isinstance(row[0], str) else row[0]
                    return Character.from_dict(data)
        return None

    async def list_npcs(self, channel_id: str) -> List[Character]:
        """列出频道所有 NPC"""
        npcs = []
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT data FROM npcs WHERE channel_id = %s", (channel_id,)
                )
                rows = await cur.fetchall()
                for row in rows:
                    data = json.loads(row[0]) if isinstance(row[0], str) else row[0]
                    npcs.append(Character.from_dict(data))
        return npcs

    async def delete_npc(self, channel_id: str, name: str) -> bool:
        """删除 NPC"""
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "DELETE FROM npcs WHERE channel_id = %s AND name = %s",
                    (channel_id, name),
                )
                return cur.rowcount > 0

    async def clear_channel_npcs(self, channel_id: str) -> int:
        """清空频道所有 NPC"""
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "DELETE FROM npcs WHERE channel_id = %s", (channel_id,)
                )
                return cur.rowcount
