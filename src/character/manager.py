"""角色卡管理器"""
from typing import Dict, List, Optional
from .models import Character


class CharacterManager:
    """角色卡管理器 - 内存缓存 + 数据库持久化"""
    
    def __init__(self, db):
        self.db = db
        # 缓存: user_id -> {char_name -> Character}
        self._cache: Dict[str, Dict[str, Character]] = {}
        # 当前选中: user_id -> char_name
        self._active: Dict[str, str] = {}
    
    async def add(self, char: Character) -> bool:
        """添加角色卡"""
        user_id = char.user_id
        if user_id not in self._cache:
            self._cache[user_id] = {}
        
        self._cache[user_id][char.name] = char
        await self.db.save_character(char)
        
        # 如果是第一个角色，自动设为当前
        if len(self._cache[user_id]) == 1:
            await self.set_active(user_id, char.name)
        
        return True
    
    async def get(self, user_id: str, name: str) -> Optional[Character]:
        """获取指定角色卡"""
        if user_id in self._cache and name in self._cache[user_id]:
            return self._cache[user_id][name]
        
        char = await self.db.get_character(user_id, name)
        if char:
            if user_id not in self._cache:
                self._cache[user_id] = {}
            self._cache[user_id][name] = char
        return char
    
    async def get_active(self, user_id: str) -> Optional[Character]:
        """获取当前激活的角色卡"""
        if user_id not in self._active:
            active_name = await self.db.get_active_character(user_id)
            if active_name:
                self._active[user_id] = active_name
        
        if user_id in self._active:
            return await self.get(user_id, self._active[user_id])
        return None

    async def set_active(self, user_id: str, name: str) -> bool:
        """设置当前激活的角色卡"""
        char = await self.get(user_id, name)
        if not char:
            return False
        
        self._active[user_id] = name
        await self.db.set_active_character(user_id, name)
        return True
    
    async def list_all(self, user_id: str) -> List[Character]:
        """列出用户所有角色卡"""
        chars = await self.db.list_characters(user_id)
        
        # 更新缓存
        if user_id not in self._cache:
            self._cache[user_id] = {}
        for char in chars:
            self._cache[user_id][char.name] = char
        
        return chars
    
    async def delete(self, user_id: str, name: str) -> bool:
        """删除角色卡"""
        if user_id in self._cache and name in self._cache[user_id]:
            del self._cache[user_id][name]
        
        if self._active.get(user_id) == name:
            del self._active[user_id]
        
        return await self.db.delete_character(user_id, name)
    
    async def load_user_data(self, user_id: str):
        """预加载用户数据"""
        await self.list_all(user_id)
        await self.get_active(user_id)
