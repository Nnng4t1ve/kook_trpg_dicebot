"""NPC 角色管理"""
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from .models import Character


# NPC 模板配置
NPC_TEMPLATES = {
    1: {
        "name": "普通",
        "attr_min": 40,
        "attr_max": 60,
        "skill_min": 40,
        "skill_max": 50,
    },
    2: {
        "name": "困难",
        "attr_min": 50,
        "attr_max": 70,
        "skill_min": 50,
        "skill_max": 60,
    },
    3: {
        "name": "极难",
        "attr_min": 60,
        "attr_max": 80,
        "skill_min": 60,
        "skill_max": 70,
    },
}

# 基础属性列表
BASE_ATTRIBUTES = ["STR", "CON", "SIZ", "DEX", "APP", "INT", "POW", "EDU"]

# 常用战斗技能
COMBAT_SKILLS = ["斗殴", "闪避", "射击", "投掷", "格斗"]


def _round_to_5(value: int) -> int:
    """将数值四舍五入到5的倍数"""
    return round(value / 5) * 5


def generate_npc(name: str, template_id: int = 1, user_id: str = "npc") -> Optional[Character]:
    """
    根据模板生成 NPC 角色
    
    Args:
        name: NPC 名称
        template_id: 模板 ID (1=普通, 2=困难, 3=极难)
        user_id: 所属用户 ID (默认 "npc")
    
    Returns:
        生成的 Character 对象，模板不存在返回 None
    """
    template = NPC_TEMPLATES.get(template_id)
    if not template:
        return None
    
    # 生成基础属性 (5的倍数)
    attributes = {}
    for attr in BASE_ATTRIBUTES:
        raw_value = random.randint(template["attr_min"], template["attr_max"])
        attributes[attr] = _round_to_5(raw_value)
    
    # 生成技能
    skills = {}
    for skill in COMBAT_SKILLS:
        raw_value = random.randint(template["skill_min"], template["skill_max"])
        skills[skill] = _round_to_5(raw_value)
    
    # 计算派生属性
    hp = (attributes["CON"] + attributes["SIZ"]) // 10
    mp = attributes["POW"] // 5
    san = attributes["POW"]
    
    return Character(
        name=name,
        user_id=user_id,
        attributes=attributes,
        skills=skills,
        hp=hp,
        max_hp=hp,
        mp=mp,
        max_mp=mp,
        san=san,
        max_san=99,
        luck=random.randint(15, 90),
    )


class NPCManager:
    """NPC 管理器 - 数据库存储，按频道隔离"""

    def __init__(self, db):
        self.db = db

    async def create(
        self, channel_id: str, name: str, template_id: int = 1
    ) -> Optional[Character]:
        """创建 NPC"""
        npc = generate_npc(name, template_id, user_id=f"npc:{channel_id}")
        if npc:
            await self.db.save_npc(channel_id, npc, template_id)
        return npc

    async def get(self, channel_id: str, name: str) -> Optional[Character]:
        """获取 NPC"""
        return await self.db.get_npc(channel_id, name)

    async def delete(self, channel_id: str, name: str) -> bool:
        """删除 NPC"""
        return await self.db.delete_npc(channel_id, name)

    async def list_all(self, channel_id: str) -> List[Character]:
        """列出频道内所有 NPC"""
        return await self.db.list_npcs(channel_id)

    async def clear_channel(self, channel_id: str) -> int:
        """清空频道内所有 NPC"""
        return await self.db.clear_channel_npcs(channel_id)
