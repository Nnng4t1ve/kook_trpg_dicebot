"""NPC 状态描述 - 根据 HP 百分比显示不同状态"""
import random
from typing import Tuple

# HP > 50% 的状态描述
STATUS_HEALTHY = [
    "看起来还很精神",
    "状态良好，战意正盛",
    "看起来只是些皮外伤,还能继续战斗",
    "伤势不重，依然警觉",
    "受了点小伤，但无大碍",
    "略显疲惫，但仍有余力",
]

# HP 25% ~ 50% 的状态描述
STATUS_WOUNDED = [
    "伤势不轻，动作开始迟缓",
    "鲜血淋漓，呼吸急促",
    "步履蹒跚，但仍在坚持",
    "伤痕累累，眼神中透着痛苦",
    "身上多处负伤，行动受阻",
    "喘息粗重，明显体力不支",
    "伤口在流血，脸色苍白",
    "摇摇欲坠，但还没倒下",
]

# HP 1% ~ 25% 的状态描述
STATUS_CRITICAL = [
    "奄奄一息，随时可能倒下",
    "浑身是血，几乎站不稳",
    "似乎命悬一线，眼神涣散",
    "伤痕累累，几乎最后一口气",
    "身体摇晃，随时会倒下",
]

# HP = 0 的状态描述
STATUS_DEAD = [
    "倒在血泊中，一动不动",
    "闭上了眼睛",
    "躺在地上，胸膛没有了起伏",
    "身体瘫软，毫无反应",
]


def get_hp_status(current_hp: int, max_hp: int) -> Tuple[str, str]:
    """
    根据 HP 百分比获取状态描述
    
    Args:
        current_hp: 当前 HP
        max_hp: 最大 HP
    
    Returns:
        (状态等级, 随机状态描述)
        状态等级: "健康", "负伤", "重伤", "死亡"
    """
    if max_hp <= 0:
        return ("未知", "状态未知")
    
    if current_hp <= 0:
        return ("死亡", random.choice(STATUS_DEAD))
    
    hp_percent = current_hp / max_hp
    
    if hp_percent > 0.5:
        return ("健康", random.choice(STATUS_HEALTHY))
    elif hp_percent > 0.25:
        return ("负伤", random.choice(STATUS_WOUNDED))
    else:
        return ("重伤", random.choice(STATUS_CRITICAL))


def get_hp_bar(current_hp: int, max_hp: int, length: int = 10, hidden: bool = False) -> str:
    """
    生成 HP 条形图
    
    Args:
        current_hp: 当前 HP
        max_hp: 最大 HP
        length: 条形图长度
        hidden: 是否隐藏实际血量（用于 NPC，只显示空条）
    
    Returns:
        HP 条形图字符串，如 "████████░░" 或 "░░░░░░░░░░"（隐藏模式）
    """
    if hidden:
        return "░" * length
    
    if max_hp <= 0:
        return "░" * length
    
    filled = int((current_hp / max_hp) * length)
    filled = max(0, min(filled, length))
    empty = length - filled
    
    return "█" * filled + "░" * empty
