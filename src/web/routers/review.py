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
    occupation_skills: list = []  # 本职技能列表
    random_sets: list = []  # 随机属性组


class CacheRequest(BaseModel):
    """缓存请求"""
    token: str
    char_name: str
    char_data: dict  # 角色数据
    occupation_skills: list = []  # 本职技能列表
    random_sets: list = []  # 随机属性组


class CacheResponse(BaseModel):
    """缓存响应"""
    success: bool
    message: str
    cached_at: str = None  # ISO格式时间戳


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


class GenerateBackstoryRequest(BaseModel):
    """AI生成背景故事请求"""
    token: str
    char_info: dict  # 角色信息


class GenerateBackstoryResponse(BaseModel):
    """AI生成背景故事响应"""
    success: bool
    content: str = ""
    error: str = ""
    cooldown_remaining: int = 0  # 剩余冷却秒数


class PolishBackstoryRequest(BaseModel):
    """AI润色背景故事请求"""
    token: str
    char_info: dict  # 角色信息


class PolishBackstoryResponse(BaseModel):
    """AI润色背景故事响应"""
    success: bool
    data: dict = {}  # 润色后的各项内容
    error: str = ""
    cooldown_remaining: int = 0


class LLMStatusResponse(BaseModel):
    """LLM服务状态响应"""
    enabled: bool
    cooldown_remaining: int = 0


# ===== API 端点 =====

@router.post("/cache", response_model=CacheResponse)
async def cache_character(
    request: Request,
    body: CacheRequest,
):
    """缓存角色卡数据（自动保存/手动保存）"""
    from datetime import datetime

    token_service = get_token_service(request)
    db = get_db(request)

    user_id = token_service.validate(body.token, "create")
    if not user_id:
        raise HTTPException(status_code=403, detail="链接已过期，请重新获取")

    if not body.char_name or not body.char_data:
        raise HTTPException(status_code=400, detail="缺少必要参数")

    # 标记为缓存数据
    char_data = body.char_data.copy()
    char_data["_cached"] = True

    # 保存到数据库（使用draft_only=True，仅当状态为草稿时才更新，防止覆盖已提交的数据）
    await db.save_character_review(
        char_name=body.char_name,
        user_id=user_id,
        image_data=None,
        char_data=char_data,
        token=body.token,
        occupation_skills=body.occupation_skills,
        random_sets=body.random_sets,
        status=0,  # 草稿状态
        draft_only=True,  # 仅当状态为草稿时才更新
    )

    cached_at = datetime.now().isoformat()
    logger.info(
        f"角色卡缓存: {body.char_name} by {user_id}, 本职技能: {len(body.occupation_skills)}个, 随机组: {len(body.random_sets)}个"
    )
    return {
        "success": True,
        "message": f"角色卡 {body.char_name} 已缓存",
        "cached_at": cached_at,
    }


@router.get("/cache/{token}")
async def get_cached_character(
    request: Request,
    token: str,
):
    """获取缓存的角色卡数据（根据token查找）"""
    token_service = get_token_service(request)
    db = get_db(request)

    token_data = token_service.get_data(token)
    if not token_data or token_data.token_type != "create":
        raise HTTPException(status_code=403, detail="链接已过期，请重新获取")

    # 根据token查找缓存数据
    review = await db.reviews.find_by_token(token)

    # 返回草稿(status=0)或已提交(status=1)的数据
    if review and review.status in (0, 1):
        return {
            "success": True,
            "char_name": review.char_name,
            "char_data": review.char_data,
            "occupation_skills": review.occupation_skills or [],
            "random_sets": review.random_sets or [],
            "status": review.status,  # 返回状态码，前端可据此判断
            "created_at": (
                review.created_at.isoformat() if review.created_at else None
            ),
        }

    return {"success": False, "message": "没有找到缓存数据"}


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
    
    # 获取已缓存的数据，如果前端没传 occupation_skills/random_sets，使用缓存的
    occupation_skills = body.occupation_skills
    random_sets = body.random_sets
    
    if not occupation_skills or not random_sets:
        existing = await db.reviews.find_by_token(body.token)
        if existing:
            if not occupation_skills:
                occupation_skills = existing.occupation_skills or []
            if not random_sets:
                random_sets = existing.random_sets or []
    
    # 标记为正式提交
    char_data = body.char_data.copy()
    char_data["_cached"] = False

    # 保存到数据库（status=1 表示已提交待审核，后续自动保存不会覆盖）
    await db.save_character_review(
        char_name=body.char_name,
        user_id=user_id,
        image_data=body.image_data,
        char_data=char_data,
        token=body.token,
        occupation_skills=occupation_skills,
        random_sets=random_sets,
        status=1,  # 已提交待审核
    )
    
    logger.info(
        f"角色卡审核提交: {body.char_name} by {user_id}, "
        f"本职技能: {len(occupation_skills)}个, 图片大小: {len(body.image_data)}字节"
    )
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
        image_url=review.get("image_url"),
    )
    
    await char_manager.add(char)
    
    # 删除审核数据
    await db.delete_character_review(body.char_name)
    
    # 创建成功后使 token 失效（当前token和保存的token都失效）
    token_service.invalidate(body.token)
    saved_token = review.get("token")
    if saved_token and saved_token != body.token:
        token_service.invalidate(saved_token)
    
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
        image_url=review.get("image_url"),
    )
    
    await char_manager.add(char)
    
    # 使原token失效
    saved_token = review.get("token")
    if saved_token:
        token_service = get_token_service(request)
        token_service.invalidate(saved_token)

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

    # 使原token失效
    saved_token = review.get("token")
    if saved_token:
        token_service = get_token_service(request)
        token_service.invalidate(saved_token)

    # 删除审核数据
    await db.delete_character_review(body.char_name)

    logger.info(f"角色卡创建成功: {body.char_name} by {body.user_id}")
    return {"success": True, "message": f"角色 {body.char_name} 创建成功！"}


# ===== LLM 相关端点 =====

@router.get("/llm/status", response_model=LLMStatusResponse)
async def get_llm_status(
    request: Request,
    token: str,
):
    """获取LLM服务状态和冷却时间"""
    from ...services.llm import get_llm_service
    
    token_service = get_token_service(request)
    user_id = token_service.validate(token, "create")
    if not user_id:
        raise HTTPException(status_code=403, detail="链接已过期，请重新获取")
    
    llm = get_llm_service()
    return {
        "enabled": llm.enabled,
        "cooldown_remaining": llm.get_cooldown_remaining(user_id)
    }


@router.post("/llm/generate-backstory", response_model=GenerateBackstoryResponse)
async def generate_backstory(
    request: Request,
    body: GenerateBackstoryRequest,
):
    """AI生成角色详细经历"""
    from ...services.llm import get_llm_service
    
    token_service = get_token_service(request)
    user_id = token_service.validate(body.token, "create")
    if not user_id:
        raise HTTPException(status_code=403, detail="链接已过期，请重新获取")
    
    llm = get_llm_service()
    
    if not llm.enabled:
        return {
            "success": False,
            "error": "AI生成功能未启用",
            "cooldown_remaining": 0
        }
    
    # 检查冷却
    remaining = llm.get_cooldown_remaining(user_id)
    if remaining > 0:
        return {
            "success": False,
            "error": f"请求冷却中",
            "cooldown_remaining": remaining
        }
    
    # 构建提示词并生成
    prompt = llm.build_backstory_prompt(body.char_info)
    result = await llm.generate(prompt, user_id)
    
    return {
        "success": result.success,
        "content": result.content,
        "error": result.error,
        "cooldown_remaining": llm.get_cooldown_remaining(user_id)
    }


@router.post("/llm/polish-backstory", response_model=PolishBackstoryResponse)
async def polish_backstory(
    request: Request,
    body: PolishBackstoryRequest,
):
    """AI润色背景故事要素"""
    from ...services.llm import get_llm_service
    
    token_service = get_token_service(request)
    user_id = token_service.validate(body.token, "create")
    if not user_id:
        raise HTTPException(status_code=403, detail="链接已过期，请重新获取")
    
    llm = get_llm_service()
    
    if not llm.enabled:
        return {
            "success": False,
            "error": "AI润色功能未启用",
            "cooldown_remaining": 0
        }
    
    # 检查冷却
    remaining = llm.get_cooldown_remaining(user_id)
    if remaining > 0:
        return {
            "success": False,
            "error": f"请求冷却中",
            "cooldown_remaining": remaining
        }
    
    # 构建提示词并生成
    prompt = llm.build_polish_backstory_prompt(body.char_info)
    result = await llm.generate(prompt, user_id)
    
    if not result.success:
        return {
            "success": False,
            "error": result.error,
            "cooldown_remaining": llm.get_cooldown_remaining(user_id)
        }
    
    # 解析JSON响应
    parsed_data = llm.parse_polish_response(result.content)
    
    if not parsed_data:
        return {
            "success": False,
            "error": "AI返回格式解析失败，请重试",
            "cooldown_remaining": llm.get_cooldown_remaining(user_id)
        }
    
    return {
        "success": True,
        "data": parsed_data,
        "cooldown_remaining": llm.get_cooldown_remaining(user_id)
    }
