"""主入口"""
import asyncio
import sys
from pathlib import Path
from loguru import logger
import uvicorn

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import settings
from src.bot import KookClient, MessageHandler
from src.character import CharacterManager
from src.storage import Database
from src.web import create_app


def setup_logging():
    """配置日志"""
    logger.remove()
    logger.add(
        sys.stderr,
        level=settings.log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan> - "
               "<level>{message}</level>"
    )
    
    settings.log_path.mkdir(parents=True, exist_ok=True)
    logger.add(
        settings.log_path / "bot_{time:YYYY-MM-DD}.log",
        rotation="00:00",
        retention="7 days",
        level="DEBUG"
    )


async def main():
    """主函数"""
    setup_logging()
    logger.info("COC Dice Bot 启动中...")
    
    # 初始化 MySQL 数据库
    db = Database(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_password,
        database=settings.db_name,
    )
    await db.connect()
    logger.info("MySQL 数据库连接成功")
    
    # 初始化角色管理器 (LRU 缓存，最多 500 个角色卡)
    char_manager = CharacterManager(db, cache_size=500)
    
    # 初始化客户端
    client = KookClient(settings.kook_token, settings.kook_api_base)
    
    # 创建 Web 应用
    web_app = create_app(db, char_manager)
    
    # 初始化消息处理器，传入 web_app 以生成创建链接
    handler = MessageHandler(client, char_manager, db, web_app)
    
    # 启动 Web 服务器
    web_config = uvicorn.Config(
        web_app,
        host=settings.web_host,
        port=settings.web_port,
        log_level="warning"
    )
    web_server = uvicorn.Server(web_config)
    
    try:
        logger.info(f"Web 服务启动: {settings.web_base_url}")
        logger.info("正在连接 KOOK...")
        
        # 启动定时清理任务
        handler.check_manager.start_cleanup_task()
        web_app.start_cleanup_task()
        logger.info("定时清理任务已启动")
        
        # 同时运行 Web 服务和 Bot
        await asyncio.gather(
            web_server.serve(),
            client.start(handler.handle)
        )
    except KeyboardInterrupt:
        logger.info("收到退出信号")
    finally:
        # 停止清理任务
        handler.check_manager.stop_cleanup_task()
        web_app.stop_cleanup_task()
        await client.stop()
        await db.close()
        logger.info("Bot 已停止")


if __name__ == "__main__":
    asyncio.run(main())
