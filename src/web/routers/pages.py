"""页面路由"""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from ..dependencies import get_token_service

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """首页"""
    templates = request.app.state.templates
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/create/{token}", response_class=HTMLResponse)
async def create_page(request: Request, token: str):
    """角色卡创建页面"""
    from loguru import logger
    
    token_service = get_token_service(request)
    templates = request.app.state.templates
    
    logger.info(f"访问创建页面: token={token}")
    
    # 获取完整token数据
    token_data = token_service.get_data(token)
    if not token_data or token_data.token_type != "create":
        logger.warning(f"Token 无效或过期: {token}")
        raise HTTPException(status_code=404, detail="链接已过期或无效")
    
    user_id = token_data.user_id
    skill_limit = token_data.extra_data.get("skill_limit")
    occ_limit = token_data.extra_data.get("occ_limit")
    non_occ_limit = token_data.extra_data.get("non_occ_limit")
    
    logger.info(f"Token 验证成功: user_id={user_id}, limits={skill_limit}/{occ_limit}/{non_occ_limit}")
    return templates.TemplateResponse(
        "create.html",
        {
            "request": request, 
            "token": token, 
            "user_id": user_id,
            "skill_limit": skill_limit,
            "occ_limit": occ_limit,
            "non_occ_limit": non_occ_limit
        }
    )


@router.get("/grow/{token}", response_class=HTMLResponse)
async def grow_page(request: Request, token: str):
    """角色卡成长页面"""
    token_service = get_token_service(request)
    templates = request.app.state.templates
    
    data = token_service.get_data(token)
    if not data or data.token_type != "grow":
        raise HTTPException(status_code=404, detail="链接已过期或无效")
    
    char_name = data.extra_data.get("char_name")
    growable_skills = data.extra_data.get("growable_skills", [])
    
    return templates.TemplateResponse(
        "grow.html",
        {
            "request": request,
            "token": token,
            "char_name": char_name,
            "growable_skills": growable_skills,
        },
    )


# 导出为 pages_router
pages_router = router
