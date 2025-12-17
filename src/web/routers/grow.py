"""成长 API 路由"""
import random

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from ..dependencies import get_char_manager, get_token_service

router = APIRouter()


# ===== Pydantic 模型 =====

class GrowCharacterResponse(BaseModel):
    """成长角色数据响应"""
    character: dict
    growable_skills: list


class GrowRollRequest(BaseModel):
    """成长检定请求"""
    skill_name: str


class GrowRollResponse(BaseModel):
    """成长检定响应"""
    success: bool
    roll: int
    old_value: int
    new_value: int
    increase: int


# ===== API 端点 =====

@router.get("/{token}/character", response_model=GrowCharacterResponse)
async def get_grow_character(
    token: str,
    request: Request,
):
    """获取成长角色数据"""
    token_service = get_token_service(request)
    char_manager = get_char_manager(request)
    
    data = token_service.get_data(token)
    if not data or data.token_type != "grow":
        raise HTTPException(status_code=404, detail="链接已过期或无效")
    
    user_id = data.user_id
    char_name = data.extra_data.get("char_name")
    growable_skills = data.extra_data.get("growable_skills", [])
    
    char = await char_manager.get(user_id, char_name)
    if not char:
        raise HTTPException(status_code=404, detail="角色不存在")
    
    return {"character": char.to_dict(), "growable_skills": growable_skills}


@router.post("/{token}/roll", response_model=GrowRollResponse)
async def do_grow_roll(
    token: str,
    body: GrowRollRequest,
    request: Request,
):
    """执行成长检定"""
    token_service = get_token_service(request)
    char_manager = get_char_manager(request)
    
    data = token_service.get_data(token)
    if not data or data.token_type != "grow":
        raise HTTPException(status_code=404, detail="链接已过期或无效")
    
    user_id = data.user_id
    char_name = data.extra_data.get("char_name")
    growable_skills = data.extra_data.get("growable_skills", [])
    grown_skills = data.extra_data.get("grown_skills", set())
    
    skill_name = body.skill_name
    
    if not skill_name:
        raise HTTPException(status_code=400, detail="缺少技能名称")
    
    if skill_name not in growable_skills:
        raise HTTPException(status_code=400, detail="该技能不可成长")
    
    if skill_name in grown_skills:
        raise HTTPException(status_code=400, detail="该技能已经成长过了")
    
    # 获取角色
    char = await char_manager.get(user_id, char_name)
    if not char:
        raise HTTPException(status_code=404, detail="角色不存在")
    
    old_value = char.skills.get(skill_name, 0)
    
    # 成长检定: D100 > 当前技能值 = 成功
    roll = random.randint(1, 100)
    success = roll > old_value
    
    new_value = old_value
    increase = 0
    
    if success:
        # 成长成功，+1D10
        increase = random.randint(1, 10)
        new_value = old_value + increase
        char.skills[skill_name] = new_value
        await char_manager.add(char)
    
    # 标记已成长
    token_service.update_grow_data(token, skill_name)
    
    return {
        "success": success,
        "roll": roll,
        "old_value": old_value,
        "new_value": new_value,
        "increase": increase,
    }
