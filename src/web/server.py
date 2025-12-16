"""Web 服务器"""
import time
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import secrets
from loguru import logger

from ..character import Character, CharacterManager
from ..storage import Database
from ..data import SKILLS_BY_CATEGORY


def create_app(db: Database, char_manager: CharacterManager) -> FastAPI:
    """创建 FastAPI 应用"""
    app = FastAPI(title="COC 角色卡创建器")
    
    # 模板目录
    templates_dir = Path(__file__).parent / "templates"
    templates = Jinja2Templates(directory=str(templates_dir))
    
    # 存储临时 token -> (user_id, created_at) 映射
    user_tokens: dict[str, tuple[str, float]] = {}
    TOKEN_EXPIRE_SECONDS = 600  # 10 分钟过期
    
    def get_user_from_token(token: str) -> str | None:
        """获取 token 对应的 user_id，检查过期"""
        data = user_tokens.get(token)
        if not data:
            return None
        user_id, created_at = data
        if time.time() - created_at > TOKEN_EXPIRE_SECONDS:
            del user_tokens[token]
            return None
        return user_id
    
    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        """首页"""
        return templates.TemplateResponse("index.html", {"request": request})
    
    @app.get("/create/{token}", response_class=HTMLResponse)
    async def create_page(request: Request, token: str):
        """角色卡创建页面"""
        logger.info(f"访问创建页面: token={token}, 当前tokens={list(user_tokens.keys())}")
        user_id = get_user_from_token(token)
        if not user_id:
            logger.warning(f"Token 无效或过期: {token}")
            raise HTTPException(status_code=404, detail="链接已过期或无效")
        logger.info(f"Token 验证成功: user_id={user_id}")
        return templates.TemplateResponse(
            "create.html", 
            {"request": request, "token": token, "user_id": user_id}
        )
    
    @app.post("/api/character/create")
    async def create_character(
        token: str = Form(...),
        name: str = Form(...),
        str_val: int = Form(50), con: int = Form(50), siz: int = Form(50),
        dex: int = Form(50), app: int = Form(50), int_val: int = Form(50),
        pow_val: int = Form(50), edu: int = Form(50), luk: int = Form(50),
        hp: int = Form(10), mp: int = Form(10), san: int = Form(50),
        skills: str = Form("")
    ):
        """创建角色卡 API"""
        user_id = get_user_from_token(token)
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
            luck=luk
        )
        
        await char_manager.add(char)
        
        # 删除已使用的 token
        del user_tokens[token]
        
        return {"success": True, "message": f"角色 {name} 创建成功！"}
    
    @app.get("/api/characters/{user_id}")
    async def list_characters(user_id: str):
        """获取用户角色列表"""
        chars = await char_manager.list_all(user_id)
        return {"characters": [c.to_dict() for c in chars]}
    
    @app.get("/api/skills")
    async def get_skills():
        """获取技能列表"""
        return {"skills": SKILLS_BY_CATEGORY}
    
    def generate_token(user_id: str) -> str:
        """生成用户创建链接的 token"""
        token = secrets.token_urlsafe(16)
        user_tokens[token] = (user_id, time.time())
        logger.info(f"生成 token: {token} -> user_id={user_id}, 当前tokens数量={len(user_tokens)}")
        return token
    
    # 将 generate_token 方法附加到 app
    app.generate_token = generate_token
    
    return app
