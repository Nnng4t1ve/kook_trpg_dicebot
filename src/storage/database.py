"""数据库操作"""
import aiosqlite
import json
from pathlib import Path
from typing import List, Optional
from ..character.models import Character


class Database:
    """SQLite 数据库操作"""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._conn: Optional[aiosqlite.Connection] = None
    
    async def connect(self):
        """连接数据库"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self.db_path)
        await self._init_tables()
    
    async def close(self):
        """关闭连接"""
        if self._conn:
            await self._conn.close()
    
    async def _init_tables(self):
        """初始化表结构"""
        await self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS characters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, name)
            );
            
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id TEXT PRIMARY KEY,
                active_character TEXT,
                rule_name TEXT DEFAULT 'coc7',
                critical_threshold INTEGER DEFAULT 5,
                fumble_threshold INTEGER DEFAULT 96
            );
            
            CREATE INDEX IF NOT EXISTS idx_char_user ON characters(user_id);
        """)
        await self._conn.commit()

    async def save_character(self, char: Character):
        """保存角色卡"""
        await self._conn.execute(
            """INSERT OR REPLACE INTO characters (user_id, name, data) 
               VALUES (?, ?, ?)""",
            (char.user_id, char.name, char.to_json())
        )
        await self._conn.commit()
    
    async def get_character(self, user_id: str, name: str) -> Optional[Character]:
        """获取角色卡"""
        async with self._conn.execute(
            "SELECT data FROM characters WHERE user_id = ? AND name = ?",
            (user_id, name)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                data = json.loads(row[0])
                return Character.from_dict(data)
        return None
    
    async def list_characters(self, user_id: str) -> List[Character]:
        """列出用户所有角色卡"""
        chars = []
        async with self._conn.execute(
            "SELECT data FROM characters WHERE user_id = ?", (user_id,)
        ) as cursor:
            async for row in cursor:
                data = json.loads(row[0])
                chars.append(Character.from_dict(data))
        return chars
    
    async def delete_character(self, user_id: str, name: str) -> bool:
        """删除角色卡"""
        cursor = await self._conn.execute(
            "DELETE FROM characters WHERE user_id = ? AND name = ?",
            (user_id, name)
        )
        await self._conn.commit()
        return cursor.rowcount > 0
    
    async def get_active_character(self, user_id: str) -> Optional[str]:
        """获取当前激活角色名"""
        async with self._conn.execute(
            "SELECT active_character FROM user_settings WHERE user_id = ?",
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None
    
    async def set_active_character(self, user_id: str, name: str):
        """设置当前激活角色"""
        await self._conn.execute(
            """INSERT OR REPLACE INTO user_settings (user_id, active_character) 
               VALUES (?, ?)""",
            (user_id, name)
        )
        await self._conn.commit()
    
    async def get_user_rule(self, user_id: str) -> dict:
        """获取用户规则设置"""
        async with self._conn.execute(
            """SELECT rule_name, critical_threshold, fumble_threshold 
               FROM user_settings WHERE user_id = ?""",
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return {"rule": row[0], "critical": row[1], "fumble": row[2]}
        return {"rule": "coc7", "critical": 5, "fumble": 96}
    
    async def set_user_rule(self, user_id: str, rule: str = None, 
                           critical: int = None, fumble: int = None):
        """设置用户规则"""
        current = await self.get_user_rule(user_id)
        rule = rule or current["rule"]
        critical = critical if critical is not None else current["critical"]
        fumble = fumble if fumble is not None else current["fumble"]
        
        await self._conn.execute(
            """INSERT OR REPLACE INTO user_settings 
               (user_id, rule_name, critical_threshold, fumble_threshold)
               VALUES (?, ?, ?, ?)""",
            (user_id, rule, critical, fumble)
        )
        await self._conn.commit()
