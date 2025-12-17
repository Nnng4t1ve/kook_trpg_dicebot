"""依赖注入模块"""
from typing import Optional

from fastapi import Depends, HTTPException, Request

from ..character import CharacterManager
from ..storage import Database


def get_db(request: Request) -> Database:
    """获取数据库实例"""
    db = getattr(request.app.state, "db", None)
    if not db:
        raise HTTPException(status_code=500, detail="数据库未初始化")
    return db


def get_char_manager(request: Request) -> CharacterManager:
    """获取角色管理器"""
    manager = getattr(request.app.state, "char_manager", None)
    if not manager:
        raise HTTPException(status_code=500, detail="角色管理器未初始化")
    return manager


def get_token_service(request: Request):
    """获取 Token 服务"""
    from ..services.token import TokenService
    service = getattr(request.app.state, "token_service", None)
    if not service:
        raise HTTPException(status_code=500, detail="Token 服务未初始化")
    return service


class TokenValidator:
    """Token 验证依赖"""
    
    def __init__(self, token_type: str = "create"):
        self.token_type = token_type
    
    def __call__(self, request: Request, token: str) -> str:
        """验证 token 并返回 user_id"""
        token_service = get_token_service(request)
        user_id = token_service.validate(token, self.token_type)
        if not user_id:
            raise HTTPException(status_code=403, detail="链接已过期或无效")
        return user_id


# 预定义的验证器
validate_create_token = TokenValidator("create")
validate_grow_token = TokenValidator("grow")
