"""Token 服务"""
import asyncio
import secrets
import time
from dataclasses import dataclass, field
from typing import Optional

from loguru import logger


@dataclass
class TokenData:
    """Token 数据"""
    user_id: str
    created_at: float
    token_type: str  # "create" | "grow"
    extra_data: dict = field(default_factory=dict)


class TokenService:
    """
    Token 管理服务
    
    负责 token 的生成、验证、清理和统计
    """
    
    TOKEN_EXPIRE_SECONDS = 7200  # 2 小时过期（创建人物卡需要较长时间）
    CLEANUP_INTERVAL = 600  # 清理间隔 10 分钟
    
    def __init__(self, expire_seconds: int = None, cleanup_interval: int = None):
        self._tokens: dict[str, TokenData] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
        
        if expire_seconds:
            self.TOKEN_EXPIRE_SECONDS = expire_seconds
        if cleanup_interval:
            self.CLEANUP_INTERVAL = cleanup_interval
    
    def generate(self, user_id: str, token_type: str, **extra_data) -> str:
        """
        生成 token
        
        Args:
            user_id: 用户 ID
            token_type: token 类型 ("create" | "grow")
            **extra_data: 额外数据
        
        Returns:
            生成的 token 字符串
        """
        token = secrets.token_urlsafe(16)
        self._tokens[token] = TokenData(
            user_id=user_id,
            created_at=time.time(),
            token_type=token_type,
            extra_data=extra_data,
        )
        logger.info(f"生成 {token_type} token: {token} -> user_id={user_id}")
        return token
    
    def generate_create_token(
        self, 
        user_id: str,
        skill_limit: int = None,
        occ_limit: int = None,
        non_occ_limit: int = None
    ) -> str:
        """生成角色创建 token"""
        return self.generate(
            user_id, 
            "create",
            skill_limit=skill_limit,
            occ_limit=occ_limit,
            non_occ_limit=non_occ_limit
        )
    
    def generate_grow_token(self, user_id: str, char_name: str, skills: list) -> str:
        """生成角色成长 token"""
        return self.generate(
            user_id, 
            "grow",
            char_name=char_name,
            growable_skills=skills,
            grown_skills=set(),
        )
    
    def validate(self, token: str, expected_type: str = None) -> Optional[str]:
        """
        验证 token
        
        Args:
            token: token 字符串
            expected_type: 期望的 token 类型（可选）
        
        Returns:
            user_id 如果有效，否则 None
        """
        data = self._tokens.get(token)
        if not data:
            return None
        
        # 检查过期
        if time.time() - data.created_at > self.TOKEN_EXPIRE_SECONDS:
            del self._tokens[token]
            return None
        
        # 检查类型
        if expected_type and data.token_type != expected_type:
            return None
        
        return data.user_id
    
    def get_data(self, token: str) -> Optional[TokenData]:
        """获取 token 完整数据"""
        data = self._tokens.get(token)
        if not data:
            return None
        
        # 检查过期
        if time.time() - data.created_at > self.TOKEN_EXPIRE_SECONDS:
            del self._tokens[token]
            return None
        
        return data
    
    def invalidate(self, token: str) -> bool:
        """使 token 失效"""
        if token in self._tokens:
            del self._tokens[token]
            return True
        return False
    
    def cleanup_expired(self) -> int:
        """清理过期的 token，返回清理数量"""
        now = time.time()
        expired = [
            k for k, v in self._tokens.items()
            if now - v.created_at > self.TOKEN_EXPIRE_SECONDS
        ]
        for k in expired:
            del self._tokens[k]
        return len(expired)
    
    async def _periodic_cleanup(self):
        """定期清理过期 token"""
        while True:
            try:
                await asyncio.sleep(self.CLEANUP_INTERVAL)
                cleaned = self.cleanup_expired()
                if cleaned > 0:
                    logger.debug(f"清理了 {cleaned} 个过期 token")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Token 清理任务出错: {e}")
    
    def start_cleanup_task(self):
        """启动清理任务"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
            logger.info(f"Token 清理任务已启动，间隔 {self.CLEANUP_INTERVAL} 秒")
    
    def stop_cleanup_task(self):
        """停止清理任务"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            self._cleanup_task = None
            logger.info("Token 清理任务已停止")
    
    def get_stats(self) -> dict:
        """获取 token 统计信息"""
        create_count = sum(1 for t in self._tokens.values() if t.token_type == "create")
        grow_count = sum(1 for t in self._tokens.values() if t.token_type == "grow")
        return {
            "total": len(self._tokens),
            "user_tokens": create_count,
            "grow_tokens": grow_count,
        }
    
    def update_grow_data(self, token: str, grown_skill: str) -> bool:
        """更新成长 token 的已成长技能"""
        data = self.get_data(token)
        if not data or data.token_type != "grow":
            return False
        
        grown_skills = data.extra_data.get("grown_skills", set())
        grown_skills.add(grown_skill)
        data.extra_data["grown_skills"] = grown_skills
        return True
