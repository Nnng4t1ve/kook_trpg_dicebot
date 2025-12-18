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


class ApproveRequest(BaseModel):
    """审核通过请求"""
    char_name: str


class CreateCharacterRequest(BaseModel):
    """创建角色请求"""
    token: str
    char_name: str


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
    
    # 注意：提交审核后不使 token 失效，等审核通过后用户点击创建时才失效
    
    logger.info(f"角色卡审核提交: {body.char_name} by {user_id}")
    return {"success": True, "message": f"角色卡 {body.char_name} 已提交审核"}


@router.post("/create", response_model=ReviewResponse)
async def create_character(
    request: Request,
    body: CreateCharacterRequest,
):
    """
    创建已审核通过的角色
    
    用户在网页点击创建按钮时调用此接口
    """
    token_service = get_token_service(request)
    db = get_db(request)
    char_manager = get_char_manager(request)
    
    # 验证 token
    user_id = token_service.validate(body.token, "create")
    if not user_id:
        raise HTTPException(status_code=403, detail="链接已过期，请重新获取")
    
    # 获取审核记录
    review = await db.get_character_review(body.char_name)
    if not review:
        raise HTTPException(status_code=404, detail="未找到待审核角色卡")
    
    if review["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="无权操作此角色卡")
    
    if not review["approved"]:
        raise HTTPException(status_code=400, detail="角色卡尚未审核通过，请等待 KP 审核")
    
    # 创建角色
    char_data = review["char_data"]
    
    # 从 inventory 提取物品列表（物品名称 + 背包格内容）
    items = []
    for inv in char_data.get("inventory", []):
        if inv.get("item"):
            items.append(inv["item"])
        if inv.get("backpack"):
            items.append(inv["backpack"])
    
    # 提取武器列表
    weapons = char_data.get("weapons", [])
    
    char = Character(
        name=char_data["name"],
        user_id=user_id,
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
        items=items,
        weapons=weapons,
    )
    
    await char_manager.add(char)
    
    # 删除审核数据
    await db.delete_character_review(body.char_name)
    
    # 创建成功后使 token 失效
    token_service.invalidate(body.token)
    
    logger.info(f"角色卡创建成功: {body.char_name} by {user_id}")
    return {"success": True, "message": f"角色 {body.char_name} 创建成功！"}


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


@router.post("/approve", response_model=ReviewResponse)
async def approve_and_create_character(
    request: Request,
    body: ApproveRequest,
):
    """
    审核通过并自动创建角色
    
    审核员调用此接口后，角色会自动创建到数据库中
    """
    db = get_db(request)
    char_manager = get_char_manager(request)
    
    review = await db.get_character_review(body.char_name)
    if not review:
        raise HTTPException(status_code=404, detail="未找到待审核角色卡")
    
    # 创建角色
    char_data = review["char_data"]
    user_id = review["user_id"]
    
    # 从 inventory 提取物品列表（物品名称 + 背包格内容）
    items = []
    for inv in char_data.get("inventory", []):
        if inv.get("item"):
            items.append(inv["item"])
        if inv.get("backpack"):
            items.append(inv["backpack"])
    
    # 提取武器列表
    weapons = char_data.get("weapons", [])
    
    char = Character(
        name=char_data["name"],
        user_id=user_id,
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
        items=items,
        weapons=weapons,
    )
    
    await char_manager.add(char)
    
    # 删除审核数据
    await db.delete_character_review(body.char_name)
    
    logger.info(f"审核通过，角色卡创建成功: {body.char_name} by {user_id}")
    return {"success": True, "message": f"角色 {body.char_name} 审核通过并创建成功！"}


@router.post("/create-approved", response_model=ReviewResponse)
async def create_approved_character(
    request: Request,
    body: CreateApprovedRequest,
):
    """创建已审核通过的角色卡（旧接口，保留兼容）"""
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
    
    # 从 inventory 提取物品列表（物品名称 + 背包格内容）
    items = []
    for inv in char_data.get("inventory", []):
        if inv.get("item"):
            items.append(inv["item"])
        if inv.get("backpack"):
            items.append(inv["backpack"])
    
    # 提取武器列表
    weapons = char_data.get("weapons", [])
    
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
        items=items,
        weapons=weapons,
    )
    
    await char_manager.add(char)
    
    # 删除审核数据
    await db.delete_character_review(body.char_name)
    
    logger.info(f"角色卡创建成功: {body.char_name} by {body.user_id}")
    return {"success": True, "message": f"角色 {body.char_name} 创建成功！"}
