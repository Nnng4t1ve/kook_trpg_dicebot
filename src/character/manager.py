"""角色卡管理器"""
from collections import OrderedDict
from typing import Dict, List, Optional
from .models import Character


class LRUCache:
    """简单的 LRU 缓存"""
    
    def __init__(self, max_size: int = 500):
        self.max_size = max_size
        self._cache: OrderedDict[str, Character] = OrderedDict()
    
    def _make_key(self, user_id: str, name: str) -> str:
        return f"{user_id}:{name}"
    
    def get(self, user_id: str, name: str) -> Optional[Character]:
        key = self._make_key(user_id, name)
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        return None
    
    def set(self, char: Character):
        key = self._make_key(char.user_id, char.name)
        if key in self._cache:
            self._cache.move_to_end(key)
        self._cache[key] = char
        # 超出容量时移除最旧的
        while len(self._cache) > self.max_size:
            self._cache.popitem(last=False)
    
    def delete(self, user_id: str, name: str):
        key = self._make_key(user_id, name)
        self._cache.pop(key, None)
    
    def get_user_chars(self, user_id: str) -> List[Character]:
        prefix = f"{user_id}:"
        return [c for k, c in self._cache.items() if k.startswith(prefix)]
    
    def clear(self):
        self._cache.clear()
    
    def __len__(self):
        return len(self._cache)


class CharacterManager:
    """角色卡管理器 - LRU 缓存 + 数据库持久化"""
    
    def __init__(self, db, cache_size: int = 500):
        self.db = db
        self._cache = LRUCache(max_size=cache_size)
        # 当前选中: user_id -> char_name
        self._active: Dict[str, str] = {}
    
    async def add(self, char: Character) -> bool:
        """添加角色卡"""
        # 检查是否是用户第一个角色
        existing = await self.db.list_characters(char.user_id)
        is_first = len(existing) == 0
        
        self._cache.set(char)
        await self.db.save_character(char)
        
        # 如果是第一个角色，自动设为当前
        if is_first:
            await self.set_active(char.user_id, char.name)
        
        return True
    
    async def get(self, user_id: str, name: str) -> Optional[Character]:
        """获取指定角色卡"""
        # 先查缓存
        char = self._cache.get(user_id, name)
        if char:
            return char
        
        # 缓存未命中，查数据库
        char = await self.db.get_character(user_id, name)
        if char:
            self._cache.set(char)
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
        for char in chars:
            self._cache.set(char)
        
        return chars
    
    async def delete(self, user_id: str, name: str) -> bool:
        """删除角色卡"""
        self._cache.delete(user_id, name)
        
        if self._active.get(user_id) == name:
            del self._active[user_id]
        
        return await self.db.delete_character(user_id, name)
    
    async def load_user_data(self, user_id: str):
        """预加载用户数据"""
        await self.list_all(user_id)
        await self.get_active(user_id)
    
    def get_cache_stats(self) -> dict:
        """获取缓存统计信息"""
        return {
            "cache_size": len(self._cache),
            "max_size": self._cache.max_size,
            "active_users": len(self._active)
        }
