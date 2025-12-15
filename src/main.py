"""主入口"""
import asyncio
import sys
from pathlib import Path
from loguru import logger

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import settings
from src.bot import KookClient, MessageHandler
from src.character import CharacterManager
from src.storage import Database


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
    
    # 初始化数据库
    db = Database(settings.database_path)
    await db.connect()
    logger.info("数据库连接成功")
    
    # 初始化角色管理器
    char_manager = CharacterManager(db)
    
    # 初始化客户端
    client = KookClient(settings.kook_token, settings.kook_api_base)
    
    # 初始化消息处理器
    handler = MessageHandler(client, char_manager, db)
    
    try:
        logger.info("正在连接 KOOK...")
        await client.start(handler.handle)
    except KeyboardInterrupt:
        logger.info("收到退出信号")
    finally:
        await client.stop()
        await db.close()
        logger.info("Bot 已停止")


if __name__ == "__main__":
    asyncio.run(main())
