"""NPC 模板仓库"""
import json
import random
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .base import BaseRepository


def roll_dice(expr: str) -> int:
    """
    解析并执行骰子表达式
    支持格式: 3d6, 3d6+6, 2d10-5, d100 等
    """
    expr = expr.lower().strip()
    
    # 匹配骰子表达式: NdM 或 dM
    match = re.match(r"^(\d*)d(\d+)([+-]\d+)?$", expr)
    if not match:
        raise ValueError(f"无效的骰子表达式: {expr}")
    
    num_dice = int(match.group(1)) if match.group(1) else 1
    dice_sides = int(match.group(2))
    modifier = int(match.group(3)) if match.group(3) else 0
    
    total = sum(random.randint(1, dice_sides) for _ in range(num_dice))
    return total + modifier


def parse_value_expr(expr: str) -> int:
    """
    解析值表达式，返回计算结果
    
    支持格式:
    - 骰子公式: "3d6+6" -> roll * 5
    - 范围: "20-30" -> random.randint(20, 30)
    - 固定值: "50" -> 50
    """
    expr = expr.strip()
    
    # 检查是否是范围格式 (如 20-30)
    range_match = re.match(r"^(\d+)-(\d+)$", expr)
    if range_match:
        min_val = int(range_match.group(1))
        max_val = int(range_match.group(2))
        return random.randint(min_val, max_val)
    
    # 检查是否是固定数值
    if expr.isdigit():
        return int(expr)
    
    # 尝试解析为骰子表达式，结果 × 5
    try:
        roll_result = roll_dice(expr)
        return roll_result * 5
    except ValueError:
        raise ValueError(f"无法解析表达式: {expr}")


@dataclass
class NPCTemplate:
    """NPC 模板数据模型"""
    name: str  # 模板名称（唯一标识）
    # 新格式：属性定义 {"STR": "3d6+6", "CON": "3d6+20", ...}
    attributes: Dict[str, str] = field(default_factory=dict)
    # 新格式：技能定义 {"格斗": "3d6", "闪避": "20-30", ...}
    skills: Dict[str, str] = field(default_factory=dict)
    description: str = ""
    # 是否为内置模板
    is_builtin: bool = False
    # 兼容旧格式
    attr_min: int = 0
    attr_max: int = 0
    skill_min: int = 0
    skill_max: int = 0
    
    def is_legacy_format(self) -> bool:
        """是否为旧格式模板"""
        return not self.attributes and self.attr_min > 0
    
    def generate_attributes(self) -> Dict[str, int]:
        """根据模板生成属性值"""
        result = {}
        for attr_name, expr in self.attributes.items():
            result[attr_name] = parse_value_expr(expr)
        return result
    
    def generate_skills(self) -> Dict[str, int]:
        """根据模板生成技能值"""
        result = {}
        for skill_name, expr in self.skills.items():
            result[skill_name] = parse_value_expr(expr)
        return result


class NPCTemplateRepository(BaseRepository[NPCTemplate]):
    """NPC 模板仓库"""
    
    table_name = "npc_templates"
    model_class = NPCTemplate
    
    def _row_to_model(self, row: tuple, columns: List[str]) -> NPCTemplate:
        """将数据库行转换为模板对象"""
        data = dict(zip(columns, row))
        
        # 解析新格式字段
        attributes = self._deserialize_json(data.get("custom_attributes")) or {}
        skills = self._deserialize_json(data.get("custom_skills")) or {}
        
        # 兼容：如果是列表格式，转换为空字典（旧格式）
        if isinstance(attributes, list):
            attributes = {}
        if isinstance(skills, list):
            skills = {}
        
        return NPCTemplate(
            name=data["name"],
            attributes=attributes,
            skills=skills,
            description=data.get("description", ""),
            is_builtin=bool(data.get("is_builtin", False)),
            attr_min=data.get("attr_min", 0),
            attr_max=data.get("attr_max", 0),
            skill_min=data.get("skill_min", 0),
            skill_max=data.get("skill_max", 0),
        )
    
    def _model_to_row(self, entity: NPCTemplate) -> Dict[str, Any]:
        """将模板对象转换为数据库行"""
        return {
            "name": entity.name,
            "attr_min": entity.attr_min,
            "attr_max": entity.attr_max,
            "skill_min": entity.skill_min,
            "skill_max": entity.skill_max,
            "description": entity.description,
            "custom_attributes": self._serialize_json(entity.attributes) if entity.attributes else None,
            "custom_skills": self._serialize_json(entity.skills) if entity.skills else None,
            "is_builtin": entity.is_builtin,
        }
    
    async def find_by_name(self, name: str) -> Optional[NPCTemplate]:
        """根据名称查找模板"""
        return await self.find_one(name=name)
    
    async def list_all(self) -> List[NPCTemplate]:
        """列出所有模板"""
        return await self.find_many(order_by="is_builtin DESC, name ASC")
    
    async def save(self, template: NPCTemplate) -> int:
        """保存模板（插入或更新）"""
        return await self.upsert(template, unique_keys=["name"])
    
    async def delete_by_name(self, name: str) -> bool:
        """删除模板"""
        count = await self.delete(name=name)
        return count > 0
