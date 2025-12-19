"""NPC 模板仓库"""
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .base import BaseRepository


@dataclass
class NPCTemplate:
    """NPC 模板数据模型"""
    name: str  # 模板名称（唯一标识）
    attr_min: int = 40
    attr_max: int = 60
    skill_min: int = 40
    skill_max: int = 50
    description: str = ""
    # 可选：自定义属性列表
    custom_attributes: List[str] = field(default_factory=list)
    # 可选：自定义技能列表
    custom_skills: List[str] = field(default_factory=list)
    # 是否为内置模板
    is_builtin: bool = False


class NPCTemplateRepository(BaseRepository[NPCTemplate]):
    """NPC 模板仓库"""
    
    table_name = "npc_templates"
    model_class = NPCTemplate
    
    def _row_to_model(self, row: tuple, columns: List[str]) -> NPCTemplate:
        """将数据库行转换为模板对象"""
        data = dict(zip(columns, row))
        return NPCTemplate(
            name=data["name"],
            attr_min=data["attr_min"],
            attr_max=data["attr_max"],
            skill_min=data["skill_min"],
            skill_max=data["skill_max"],
            description=data.get("description", ""),
            custom_attributes=self._deserialize_json(data.get("custom_attributes")) or [],
            custom_skills=self._deserialize_json(data.get("custom_skills")) or [],
            is_builtin=bool(data.get("is_builtin", False)),
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
            "custom_attributes": self._serialize_json(entity.custom_attributes) if entity.custom_attributes else None,
            "custom_skills": self._serialize_json(entity.custom_skills) if entity.custom_skills else None,
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
