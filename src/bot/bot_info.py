"""机器人信息管理"""
from loguru import logger

# 内存缓存机器人 ID
_bot_id: str | None = None


async def load_bot_id(db, client) -> str | None:
    """
    启动时加载机器人 ID
    
    如果数据库中没有，则从 API 获取并保存
    """
    global _bot_id
    
    # 先从数据库加载
    _bot_id = await db.get_bot_id()
    if _bot_id:
        logger.info(f"已加载机器人 ID: {_bot_id}")
        return _bot_id
    
    # 数据库中没有，从 API 获取
    logger.info("数据库中无机器人 ID，正在从 API 获取...")
    me = await client.get_me()
    if me and me.get("id"):
        _bot_id = me["id"]
        await db.set_bot_id(_bot_id)
        logger.info(f"机器人 ID 已保存: {_bot_id}")
        return _bot_id
    
    logger.warning("无法获取机器人 ID")
    return None


def get_bot_id() -> str | None:
    """获取机器人 ID（同步方法，从缓存读取）"""
    return _bot_id


def is_bot(user_id: str) -> bool:
    """检查是否是机器人自己"""
    return _bot_id is not None and _bot_id == user_id
