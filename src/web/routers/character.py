"""角色 API 路由"""
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from pydantic import BaseModel

from ...character import Character
from ...data import SKILLS_BY_CATEGORY
from ..dependencies import get_char_manager, get_token_service

router = APIRouter()


# ===== Pydantic 模型 =====

class CharacterCreateRequest(BaseModel):
    """角色创建请求"""
    token: str
    name: str
    str_val: int = 50
    con: int = 50
    siz: int = 50
    dex: int = 50
    app: int = 50
    int_val: int = 50
    pow_val: int = 50
    edu: int = 50
    luk: int = 50
    hp: int = 10
    mp: int = 10
    san: int = 50
    mov: int = 8
    build: int = 0
    db: str = "0"
    skills: str = ""


class CharacterResponse(BaseModel):
    """角色响应"""
    success: bool
    message: str


class CharacterListResponse(BaseModel):
    """角色列表响应"""
    characters: list


class SkillsResponse(BaseModel):
    """技能列表响应"""
    skills: dict


# ===== API 端点 =====

@router.post("/create", response_model=CharacterResponse)
async def create_character(
    request: Request,
    token: str = Form(...),
    name: str = Form(...),
    str_val: int = Form(50),
    con: int = Form(50),
    siz: int = Form(50),
    dex: int = Form(50),
    app: int = Form(50),
    int_val: int = Form(50),
    pow_val: int = Form(50),
    edu: int = Form(50),
    luk: int = Form(50),
    hp: int = Form(10),
    mp: int = Form(10),
    san: int = Form(50),
    mov: int = Form(8),
    build: int = Form(0),
    db: str = Form("0"),
    skills: str = Form(""),
):
    """创建角色卡 API"""
    token_service = get_token_service(request)
    char_manager = get_char_manager(request)
    
    user_id = token_service.validate(token, "create")
    if not user_id:
        raise HTTPException(status_code=403, detail="链接已过期，请重新获取")
    
    # 解析技能
    skills_dict = {}
    if skills.strip():
        for line in skills.strip().split("\n"):
            if ":" in line or "：" in line:
                line = line.replace("：", ":")
                k, v = line.split(":", 1)
                try:
                    skills_dict[k.strip()] = int(v.strip())
                except ValueError:
                    pass
    
    # 确保克苏鲁神话技能存在且默认为0
    if "克苏鲁神话" not in skills_dict:
        skills_dict["克苏鲁神话"] = 0
    
    # 创建角色
    char = Character(
        name=name,
        user_id=user_id,
        attributes={
            "STR": str_val, "CON": con, "SIZ": siz,
            "DEX": dex, "APP": app, "INT": int_val,
            "POW": pow_val, "EDU": edu, "LUK": luk
        },
        skills=skills_dict,
        hp=hp, max_hp=hp,
        mp=mp, max_mp=mp,
        san=san, max_san=99,
        luck=luk,
        mov=mov,
        build=build,
        db=db
    )
    
    await char_manager.add(char)
    
    # 删除已使用的 token
    token_service.invalidate(token)
    
    return {"success": True, "message": f"角色 {name} 创建成功！"}


@router.get("/{user_id}", response_model=CharacterListResponse)
async def list_characters(
    user_id: str,
    char_manager=Depends(get_char_manager),
):
    """获取用户角色列表"""
    chars = await char_manager.list_all(user_id)
    return {"characters": [c.to_dict() for c in chars]}


@router.get("/skills/list", response_model=SkillsResponse)
async def get_skills():
    """获取技能列表"""
    return {"skills": SKILLS_BY_CATEGORY}
