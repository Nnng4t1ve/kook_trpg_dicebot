"""角色卡导入器"""
import json
from typing import Optional, Tuple
from .models import Character


class CharacterImporter:
    """角色卡导入器"""
    
    @staticmethod
    def from_json(json_str: str, user_id: str) -> Tuple[Optional[Character], Optional[str]]:
        """从 JSON 字符串导入角色卡"""
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            return None, f"JSON 解析错误: {e}"
        
        # 验证必要字段
        if "name" not in data:
            return None, "缺少必要字段: name"

        # 提取属性
        attributes = data.get("attributes", {})
        skills = data.get("skills", {})

        # 确保克苏鲁神话技能存在且默认为0
        if "克苏鲁神话" not in skills:
            skills["克苏鲁神话"] = 0

        # 计算派生属性
        hp = data.get("hp", 0)
        mp = data.get("mp", 0)
        san = data.get("san", attributes.get("POW", 0))
        luck = attributes.get("LUK", data.get("luck", 0))
        
        # 提取物品（只保留名称，不保留部位信息）
        items = []
        raw_items = data.get("items", [])
        for item in raw_items:
            if isinstance(item, str):
                items.append(item)
            elif isinstance(item, dict):
                # 如果是 {"name": "xxx", "slot": "xxx"} 格式，只取名称
                items.append(item.get("name", str(item)))
        
        char = Character(
            name=data["name"],
            user_id=user_id,
            attributes=attributes,
            skills=skills,
            hp=hp, max_hp=hp,
            mp=mp, max_mp=mp,
            san=san, max_san=99,
            luck=luck,
            items=items,
        )
        
        return char, None
