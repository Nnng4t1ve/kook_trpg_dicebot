"""角色卡模型"""
from dataclasses import dataclass, field
from typing import Dict, Optional
import json


@dataclass
class Character:
    """角色卡"""
    name: str
    user_id: str
    attributes: Dict[str, int] = field(default_factory=dict)
    skills: Dict[str, int] = field(default_factory=dict)
    hp: int = 0
    max_hp: int = 0
    mp: int = 0
    max_mp: int = 0
    san: int = 0
    max_san: int = 0
    luck: int = 0
    
    def get_skill(self, name: str) -> Optional[int]:
        """获取技能值，支持属性和技能"""
        # 先查技能
        if name in self.skills:
            return self.skills[name]
        # 再查属性 (大写)
        upper_name = name.upper()
        if upper_name in self.attributes:
            return self.attributes[upper_name]
        return None
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "name": self.name,
            "user_id": self.user_id,
            "attributes": self.attributes,
            "skills": self.skills,
            "hp": self.hp, "max_hp": self.max_hp,
            "mp": self.mp, "max_mp": self.max_mp,
            "san": self.san, "max_san": self.max_san,
            "luck": self.luck
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)
    
    @classmethod
    def from_dict(cls, data: dict) -> "Character":
        return cls(**data)
