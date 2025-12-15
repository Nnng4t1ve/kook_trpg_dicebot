"""骰点表达式解析器"""
import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class DiceExpression:
    """骰点表达式"""
    count: int = 1      # 骰子数量
    sides: int = 100    # 骰子面数
    modifier: int = 0   # 修正值
    raw: str = ""       # 原始表达式


class DiceParser:
    """骰点表达式解析器"""
    
    # 匹配骰点表达式: 1d100, 3d6+5, d20-2, 2d6
    DICE_PATTERN = re.compile(
        r'^(\d*)d(\d+)([+-]\d+)?$',
        re.IGNORECASE
    )
    
    @classmethod
    def parse(cls, expression: str) -> Optional[DiceExpression]:
        """解析骰点表达式"""
        expression = expression.strip().lower()
        match = cls.DICE_PATTERN.match(expression)
        
        if not match:
            return None
        
        count_str, sides_str, modifier_str = match.groups()
        
        count = int(count_str) if count_str else 1
        sides = int(sides_str)
        modifier = int(modifier_str) if modifier_str else 0
        
        # 验证合理性
        if count < 1 or count > 100:
            return None
        if sides < 1 or sides > 1000:
            return None
        
        return DiceExpression(
            count=count,
            sides=sides,
            modifier=modifier,
            raw=expression
        )
    
    @classmethod
    def is_valid(cls, expression: str) -> bool:
        """检查表达式是否有效"""
        return cls.parse(expression) is not None
