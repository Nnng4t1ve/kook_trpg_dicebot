"""Web 服务器"""
import asyncio
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
    CLEANUP_INTERVAL = 300  # 清理间隔 5 分钟
    
    # 清理任务引用
    cleanup_task = None
    
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
        mov: int = Form(8), build: int = Form(0), db: str = Form("0"),
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
            luck=luk,
            mov=mov,
            build=build,
            db=db
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

    # ===== 成长系统 =====
    # 存储成长 token -> (user_id, char_name, growable_skills, grown_skills, created_at)
    grow_tokens: dict[str, tuple[str, str, list, set, float]] = {}

    @app.get("/grow/{token}", response_class=HTMLResponse)
    async def grow_page(request: Request, token: str):
        """角色卡成长页面"""
        data = grow_tokens.get(token)
        if not data:
            raise HTTPException(status_code=404, detail="链接已过期或无效")

        user_id, char_name, growable_skills, grown_skills, created_at = data
        if time.time() - created_at > TOKEN_EXPIRE_SECONDS:
            del grow_tokens[token]
            raise HTTPException(status_code=404, detail="链接已过期")

        return templates.TemplateResponse(
            "grow.html",
            {
                "request": request,
                "token": token,
                "char_name": char_name,
                "growable_skills": growable_skills,
            },
        )

    @app.get("/api/grow/{token}/character")
    async def get_grow_character(token: str):
        """获取成长角色数据"""
        data = grow_tokens.get(token)
        if not data:
            raise HTTPException(status_code=404, detail="链接已过期或无效")

        user_id, char_name, growable_skills, grown_skills, created_at = data
        char = await char_manager.get(user_id, char_name)
        if not char:
            raise HTTPException(status_code=404, detail="角色不存在")

        return {"character": char.to_dict(), "growable_skills": growable_skills}

    @app.post("/api/grow/{token}/roll")
    async def do_grow_roll(token: str, request: Request):
        """执行成长检定"""
        import random

        data = grow_tokens.get(token)
        if not data:
            raise HTTPException(status_code=404, detail="链接已过期或无效")

        user_id, char_name, growable_skills, grown_skills, created_at = data

        body = await request.json()
        skill_name = body.get("skill_name")

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
        grown_skills.add(skill_name)

        return {
            "success": success,
            "roll": roll,
            "old_value": old_value,
            "new_value": new_value,
            "increase": increase,
        }

    def generate_token(user_id: str) -> str:
        """生成用户创建链接的 token"""
        token = secrets.token_urlsafe(16)
        user_tokens[token] = (user_id, time.time())
        logger.info(f"生成 token: {token} -> user_id={user_id}, 当前tokens数量={len(user_tokens)}")
        return token

    def generate_grow_token(user_id: str, char_name: str, skills: list) -> str:
        """生成成长链接的 token"""
        token = secrets.token_urlsafe(16)
        grow_tokens[token] = (user_id, char_name, skills, set(), time.time())
        logger.info(f"生成成长 token: {token} -> user={user_id}, char={char_name}, skills={skills}")
        return token

    def cleanup_expired_tokens() -> int:
        """清理过期的 token，返回清理数量"""
        now = time.time()
        count = 0
        
        # 清理创建 token
        expired = [k for k, v in user_tokens.items() if now - v[1] > TOKEN_EXPIRE_SECONDS]
        for k in expired:
            del user_tokens[k]
            count += 1
        
        # 清理成长 token
        expired = [k for k, v in grow_tokens.items() if now - v[4] > TOKEN_EXPIRE_SECONDS]
        for k in expired:
            del grow_tokens[k]
            count += 1
        
        return count
    
    async def periodic_cleanup():
        """定期清理过期 token"""
        while True:
            try:
                await asyncio.sleep(CLEANUP_INTERVAL)
                cleaned = cleanup_expired_tokens()
                if cleaned > 0:
                    logger.debug(f"清理了 {cleaned} 个过期 token")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Token 清理任务出错: {e}")
    
    def start_cleanup_task():
        """启动清理任务"""
        nonlocal cleanup_task
        if cleanup_task is None:
            cleanup_task = asyncio.create_task(periodic_cleanup())
            logger.info(f"Token 清理任务已启动，间隔 {CLEANUP_INTERVAL} 秒")
    
    def stop_cleanup_task():
        """停止清理任务"""
        nonlocal cleanup_task
        if cleanup_task:
            cleanup_task.cancel()
            cleanup_task = None
            logger.info("Token 清理任务已停止")
    
    def get_token_stats() -> dict:
        """获取 token 统计信息"""
        return {
            "user_tokens": len(user_tokens),
            "grow_tokens": len(grow_tokens)
        }

    # 将方法附加到 app
    app.generate_token = generate_token
    app.generate_grow_token = generate_grow_token
    app.start_cleanup_task = start_cleanup_task
    app.stop_cleanup_task = stop_cleanup_task
    app.get_token_stats = get_token_stats

    return app
