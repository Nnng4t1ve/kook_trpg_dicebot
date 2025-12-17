"""FastAPI 应用工厂"""
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .middleware import ErrorHandlerMiddleware, RequestLoggingMiddleware

if TYPE_CHECKING:
    from ..character import CharacterManager
    from ..services.token import TokenService
    from ..storage import Database


def create_app(
    db: "Database",
    char_manager: "CharacterManager",
    token_service: "TokenService" = None,
) -> FastAPI:
    """
    创建 FastAPI 应用
    
    Args:
        db: 数据库实例
        char_manager: 角色管理器
        token_service: Token 服务（可选，不传则自动创建）
    
    Returns:
        配置好的 FastAPI 应用实例
    """
    app = FastAPI(
        title="COC 角色卡服务",
        description="TRPG Dice Bot 角色卡管理 API",
        version="2.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    
    # 添加中间件
    app.add_middleware(ErrorHandlerMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    
    # 模板目录
    templates_dir = Path(__file__).parent / "templates"
    templates = Jinja2Templates(directory=str(templates_dir))
    
    # 静态文件目录
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    
    # 延迟导入避免循环依赖
    from ..services.token import TokenService
    
    # 如果没有传入 token_service，创建一个
    if token_service is None:
        token_service = TokenService()
    
    # 存储到 app.state 供依赖注入使用
    app.state.db = db
    app.state.char_manager = char_manager
    app.state.token_service = token_service
    app.state.templates = templates
    
    # 注册路由
    from .routers import character_router, grow_router, health_router, review_router
    
    app.include_router(character_router, prefix="/api/character", tags=["character"])
    app.include_router(review_router, prefix="/api/review", tags=["review"])
    app.include_router(grow_router, prefix="/api/grow", tags=["grow"])
    app.include_router(health_router, prefix="/health", tags=["health"])
    
    # 注册页面路由
    from .routers.pages import pages_router
    app.include_router(pages_router, tags=["pages"])
    
    # ===== 向后兼容的路由 =====
    from fastapi import Request
    from fastapi.responses import RedirectResponse
    
    @app.get("/api/skills")
    async def get_skills_legacy():
        """获取技能列表（兼容旧路径）"""
        from ..data import SKILLS_BY_CATEGORY
        return {"skills": SKILLS_BY_CATEGORY}
    
    @app.get("/api/characters/{user_id}")
    async def list_characters_legacy(user_id: str, request: Request):
        """获取用户角色列表（兼容旧路径）"""
        chars = await char_manager.list_all(user_id)
        return {"characters": [c.to_dict() for c in chars]}
    
    @app.post("/api/character/review")
    async def submit_review_legacy(request: Request):
        """提交角色卡审核（兼容旧路径）"""
        from .routers.review import ReviewSubmitRequest, submit_review
        body = await request.json()
        review_request = ReviewSubmitRequest(**body)
        return await submit_review(request, review_request)
    
    @app.get("/api/character/review/{char_name}")
    async def get_review_legacy(char_name: str, request: Request):
        """获取待审核角色卡（兼容旧路径）"""
        review = await db.get_character_review(char_name)
        if not review:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="未找到待审核角色卡")
        return {
            "char_name": review["char_name"],
            "user_id": review["user_id"],
            "char_data": review["char_data"],
            "approved": review["approved"],
        }
    
    @app.post("/api/character/create-approved")
    async def create_approved_legacy(request: Request):
        """创建已审核通过的角色卡（兼容旧路径）"""
        from .routers.review import CreateApprovedRequest, create_approved_character
        body = await request.json()
        create_request = CreateApprovedRequest(**body)
        return await create_approved_character(request, create_request)
    
    # 暴露便捷方法（兼容旧接口）
    app.generate_token = token_service.generate_create_token
    app.generate_grow_token = token_service.generate_grow_token
    app.start_cleanup_task = token_service.start_cleanup_task
    app.stop_cleanup_task = token_service.stop_cleanup_task
    app.get_token_stats = token_service.get_stats
    app.db = db
    
    return app
