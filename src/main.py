"""主入口"""
import argparse
import asyncio
import sys
from pathlib import Path

import uvicorn
from loguru import logger

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.bot import KookClient, MessageHandler
from src.character import CharacterManager
from src.config import settings
from src.logging import setup_logging as configure_logging
from src.services import TokenService
from src.storage import Database
from src.web import create_app
from src.web.routers.health import set_start_time


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="COC Dice Bot")
    parser.add_argument(
        "--debug", "-d",
        action="store_true",
        help="启用 DEBUG 日志级别"
    )
    return parser.parse_args()


async def main(debug: bool = False):
    """主函数"""
    # 确定日志级别：命令行 --debug 优先于 .env 配置
    log_level = "DEBUG" if debug else settings.log_level
    
    # 使用新的日志配置模块
    configure_logging(
        level=log_level,
        log_path=settings.log_path,
        rotation="10 MB",
        retention="7 days",
    )
    logger.info("COC Dice Bot 启动中...")
    
    # 记录启动时间
    set_start_time()
    
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
    
    # 加载管理员身份
    from src.bot.commands.admin import load_admin_id
    await load_admin_id(db)
    
    # 初始化角色管理器 (LRU 缓存，最多 500 个角色卡)
    char_manager = CharacterManager(db, cache_size=500)
    
    # 初始化 Token 服务
    token_service = TokenService()
    
    # 初始化客户端
    client = KookClient(settings.kook_token, settings.kook_api_base)
    
    # 加载机器人 ID（需要先初始化 client）
    from src.bot.bot_info import load_bot_id
    await load_bot_id(db, client)
    
    # 创建 Web 应用
    web_app = create_app(db, char_manager, token_service)
    
    # 设置 bot 连接状态（供健康检查使用）
    web_app.state.bot_connected = False
    web_app.state.recent_errors = 0
    
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
    
    async def run_bot():
        """运行 Bot 并更新连接状态"""
        try:
            web_app.state.bot_connected = True
            await client.start(handler.handle)
        except Exception as e:
            logger.error(f"Bot 运行错误: {e}")
            web_app.state.recent_errors += 1
        finally:
            web_app.state.bot_connected = False
    
    try:
        logger.info(f"Web 服务启动: {settings.web_base_url}")
        logger.info(f"API 文档: {settings.web_base_url}/docs")
        logger.info("正在连接 KOOK...")
        
        # 启动定时清理任务
        handler.check_manager.start_cleanup_task()
        token_service.start_cleanup_task()
        logger.info("定时清理任务已启动")
        
        # 同时运行 Web 服务和 Bot
        await asyncio.gather(
            web_server.serve(),
            run_bot()
        )
    except KeyboardInterrupt:
        logger.info("收到退出信号")
    finally:
        # 停止清理任务
        handler.check_manager.stop_cleanup_task()
        token_service.stop_cleanup_task()
        await client.stop()
        await db.close()
        logger.info("Bot 已停止")


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(main(debug=args.debug))
