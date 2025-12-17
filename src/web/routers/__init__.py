"""路由模块"""
from .character import router as character_router
from .grow import router as grow_router
from .health import router as health_router
from .review import router as review_router

__all__ = [
    "character_router",
    "review_router",
    "grow_router",
    "health_router",
]
