"""健康检查 API 路由"""
import time
from typing import Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from ..dependencies import get_db, get_token_service

router = APIRouter()

# 应用启动时间
_start_time: Optional[float] = None


def set_start_time():
    """设置启动时间"""
    global _start_time
    _start_time = time.time()


def get_uptime() -> float:
    """获取运行时间（秒）"""
    if _start_time is None:
        return 0.0
    return time.time() - _start_time


# ===== Pydantic 模型 =====

class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str  # "healthy" | "degraded" | "unhealthy"
    uptime_seconds: float
    bot_connected: bool
    db_connected: bool
    active_tokens: int
    recent_errors: int


class DetailedHealthResponse(HealthResponse):
    """详细健康检查响应"""
    token_stats: dict
    cache_stats: Optional[dict] = None


# ===== API 端点 =====

@router.get("", response_model=HealthResponse)
async def health_check(request: Request):
    """基础健康检查"""
    db = get_db(request)
    token_service = get_token_service(request)
    
    # 检查数据库连接
    db_connected = False
    try:
        if db._pool:
            async with db._pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT 1")
                    db_connected = True
    except Exception:
        pass
    
    # 获取 token 统计
    token_stats = token_service.get_stats()
    
    # 检查 bot 连接状态（从 app.state 获取）
    bot_connected = getattr(request.app.state, "bot_connected", False)
    
    # 获取最近错误数（从 app.state 获取）
    recent_errors = getattr(request.app.state, "recent_errors", 0)
    
    # 确定状态
    if db_connected and bot_connected:
        status = "healthy"
    elif db_connected or bot_connected:
        status = "degraded"
    else:
        status = "unhealthy"
    
    return {
        "status": status,
        "uptime_seconds": get_uptime(),
        "bot_connected": bot_connected,
        "db_connected": db_connected,
        "active_tokens": token_stats.get("total", 0),
        "recent_errors": recent_errors,
    }


@router.get("/detailed", response_model=DetailedHealthResponse)
async def detailed_health_check(request: Request):
    """详细健康检查"""
    db = get_db(request)
    token_service = get_token_service(request)
    char_manager = getattr(request.app.state, "char_manager", None)
    
    # 检查数据库连接
    db_connected = False
    try:
        if db._pool:
            async with db._pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT 1")
                    db_connected = True
    except Exception:
        pass
    
    # 获取 token 统计
    token_stats = token_service.get_stats()
    
    # 获取缓存统计
    cache_stats = None
    if char_manager:
        cache_stats = char_manager.get_cache_stats()
    
    # 检查 bot 连接状态
    bot_connected = getattr(request.app.state, "bot_connected", False)
    recent_errors = getattr(request.app.state, "recent_errors", 0)
    
    # 确定状态
    if db_connected and bot_connected:
        status = "healthy"
    elif db_connected or bot_connected:
        status = "degraded"
    else:
        status = "unhealthy"
    
    return {
        "status": status,
        "uptime_seconds": get_uptime(),
        "bot_connected": bot_connected,
        "db_connected": db_connected,
        "active_tokens": token_stats.get("total", 0),
        "recent_errors": recent_errors,
        "token_stats": token_stats,
        "cache_stats": cache_stats,
    }
