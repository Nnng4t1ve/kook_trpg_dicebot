"""骰点执行器"""
import random
from dataclasses import dataclass, field
from typing import List
from .parser import DiceExpression


@dataclass
class RollResult:
    """骰点结果"""
    expression: DiceExpression
    rolls: List[int] = field(default_factory=list)
    total: int = 0
    
    def __str__(self) -> str:
        if len(self.rolls) == 1 and self.expression.modifier == 0:
            return f"{self.expression.raw} = {self.total}"
        
        rolls_str = "+".join(map(str, self.rolls))
        if self.expression.modifier != 0:
            mod_str = f"{self.expression.modifier:+d}"
            return f"{self.expression.raw} = [{rolls_str}]{mod_str} = {self.total}"
        return f"{self.expression.raw} = [{rolls_str}] = {self.total}"


class DiceRoller:
    """骰点执行器"""
    
    @staticmethod
    def roll(expr: DiceExpression) -> RollResult:
        """执行骰点"""
        rolls = [random.randint(1, expr.sides) for _ in range(expr.count)]
        total = sum(rolls) + expr.modifier
        
        return RollResult(
            expression=expr,
            rolls=rolls,
            total=total
        )
    
    @staticmethod
    def roll_d100() -> int:
        """快速骰 1d100"""
        return random.randint(1, 100)
