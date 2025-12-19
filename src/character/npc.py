"""NPC 角色管理"""
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, TYPE_CHECKING
from .models import Character

if TYPE_CHECKING:
    from ..storage.repositories import NPCTemplate


# NPC 模板配置（保留用于兼容旧代码）
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


def _calc_derived_stats(attributes: dict) -> tuple:
    """计算派生属性"""
    hp = (attributes["CON"] + attributes["SIZ"]) // 10
    mp = attributes["POW"] // 5
    san = attributes["POW"]
    
    str_siz = attributes["STR"] + attributes["SIZ"]
    if str_siz <= 64:
        build, db = -2, "-2"
    elif str_siz <= 84:
        build, db = -1, "-1"
    elif str_siz <= 124:
        build, db = 0, "0"
    elif str_siz <= 164:
        build, db = 1, "+1D4"
    elif str_siz <= 204:
        build, db = 2, "+1D6"
    else:
        build, db = 3, "+2D6"
    
    return hp, mp, san, build, db


def generate_npc_from_template(
    name: str,
    template: "NPCTemplate",
    user_id: str = "npc"
) -> Character:
    """
    根据数据库模板生成 NPC 角色
    
    Args:
        name: NPC 名称
        template: NPCTemplate 对象
        user_id: 所属用户 ID
    
    Returns:
        生成的 Character 对象
    """
    # 使用自定义属性列表或默认列表
    attr_list = template.custom_attributes if template.custom_attributes else BASE_ATTRIBUTES
    skill_list = template.custom_skills if template.custom_skills else COMBAT_SKILLS
    
    # 生成基础属性 (5的倍数)
    attributes = {}
    for attr in attr_list:
        raw_value = random.randint(template.attr_min, template.attr_max)
        attributes[attr] = _round_to_5(raw_value)
    
    # 确保基础属性存在（用于计算派生属性）
    for attr in BASE_ATTRIBUTES:
        if attr not in attributes:
            raw_value = random.randint(template.attr_min, template.attr_max)
            attributes[attr] = _round_to_5(raw_value)
    
    # 生成技能
    skills = {}
    for skill in skill_list:
        raw_value = random.randint(template.skill_min, template.skill_max)
        skills[skill] = _round_to_5(raw_value)
    
    hp, mp, san, build, db = _calc_derived_stats(attributes)

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
        build=build,
        db=db,
    )


def generate_npc(name: str, template_id: int = 1, user_id: str = "npc") -> Optional[Character]:
    """
    根据模板 ID 生成 NPC 角色（兼容旧接口）
    
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
    
    hp, mp, san, build, db = _calc_derived_stats(attributes)

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
        build=build,
        db=db,
    )


class NPCManager:
    """NPC 管理器 - 数据库存储，按频道隔离"""

    def __init__(self, db):
        self.db = db

    async def create(
        self, channel_id: str, name: str, template_id: int = 1
    ) -> Optional[Character]:
        """创建 NPC（兼容旧接口）"""
        npc = generate_npc(name, template_id, user_id=f"npc:{channel_id}")
        if npc:
            await self.db.save_npc(channel_id, npc, template_id)
        return npc

    async def create_from_template(
        self, channel_id: str, name: str, template: "NPCTemplate"
    ) -> Character:
        """根据数据库模板创建 NPC"""
        npc = generate_npc_from_template(name, template, user_id=f"npc:{channel_id}")
        await self.db.save_npc(channel_id, npc, 0)  # template_id=0 表示自定义模板
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
