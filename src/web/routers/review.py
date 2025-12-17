"""审核 API 路由"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from loguru import logger
from pydantic import BaseModel

from ...character import Character
from ..dependencies import get_char_manager, get_db, get_token_service

router = APIRouter()


# ===== Pydantic 模型 =====

class ReviewSubmitRequest(BaseModel):
    """审核提交请求"""
    token: str
    char_name: str
    image_data: str  # base64 编码的图片
    char_data: dict  # 角色数据


class ReviewResponse(BaseModel):
    """审核响应"""
    success: bool
    message: str


class ReviewDetailResponse(BaseModel):
    """审核详情响应"""
    char_name: str
    user_id: str
    char_data: dict
    approved: bool


class CreateApprovedRequest(BaseModel):
    """创建已审核角色请求"""
    char_name: str
    user_id: str


# ===== API 端点 =====

@router.post("/submit", response_model=ReviewResponse)
async def submit_review(
    request: Request,
    body: ReviewSubmitRequest,
):
    """提交角色卡审核"""
    token_service = get_token_service(request)
    db = get_db(request)
    
    user_id = token_service.validate(body.token, "create")
    if not user_id:
        raise HTTPException(status_code=403, detail="链接已过期，请重新获取")
    
    if not body.char_name or not body.image_data or not body.char_data:
        raise HTTPException(status_code=400, detail="缺少必要参数")
    
    # 保存到数据库
    await db.save_character_review(
        char_name=body.char_name,
        user_id=user_id,
        image_data=body.image_data,
        char_data=body.char_data,
    )
    
    logger.info(f"角色卡审核提交: {body.char_name} by {user_id}")
    return {"success": True, "message": f"角色卡 {body.char_name} 已提交审核"}


@router.get("/{char_name}", response_model=ReviewDetailResponse)
async def get_review(
    char_name: str,
    db=Depends(get_db),
):
    """获取待审核角色卡"""
    review = await db.get_character_review(char_name)
    if not review:
        raise HTTPException(status_code=404, detail="未找到待审核角色卡")
    return {
        "char_name": review["char_name"],
        "user_id": review["user_id"],
        "char_data": review["char_data"],
        "approved": review["approved"],
    }


@router.post("/create-approved", response_model=ReviewResponse)
async def create_approved_character(
    request: Request,
    body: CreateApprovedRequest,
):
    """创建已审核通过的角色卡"""
    db = get_db(request)
    char_manager = get_char_manager(request)
    
    review = await db.get_character_review(body.char_name)
    if not review:
        raise HTTPException(status_code=404, detail="未找到待审核角色卡")
    
    if review["user_id"] != body.user_id:
        raise HTTPException(status_code=403, detail="无权操作")
    
    if not review["approved"]:
        raise HTTPException(status_code=400, detail="角色卡尚未审核通过")
    
    # 创建角色
    char_data = review["char_data"]
    char = Character(
        name=char_data["name"],
        user_id=body.user_id,
        attributes=char_data["attributes"],
        skills=char_data["skills"],
        hp=char_data["hp"],
        max_hp=char_data["hp"],
        mp=char_data["mp"],
        max_mp=char_data["mp"],
        san=char_data["san"],
        max_san=99,
        luck=char_data["attributes"].get("LUK", 50),
        mov=char_data.get("mov", 8),
        build=char_data.get("build", 0),
        db=char_data.get("db", "0"),
    )
    
    await char_manager.add(char)
    
    # 删除审核数据
    await db.delete_character_review(body.char_name)
    
    logger.info(f"角色卡创建成功: {body.char_name} by {body.user_id}")
    return {"success": True, "message": f"角色 {body.char_name} 创建成功！"}
