"""骰点表达式解析器"""
import re
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class DiceTerm:
    """单个骰点项"""

    count: int = 1  # 骰子数量
    sides: int = 100  # 骰子面数
    negative: bool = False  # 是否为负数项


@dataclass
class DiceExpression:
    """骰点表达式"""

    terms: List[DiceTerm] = field(default_factory=list)  # 骰点项列表
    modifier: int = 0  # 常数修正值
    raw: str = ""  # 原始表达式

    # 兼容旧接口
    @property
    def count(self) -> int:
        return self.terms[0].count if self.terms else 1

    @property
    def sides(self) -> int:
        return self.terms[0].sides if self.terms else 100


class DiceParser:
    """骰点表达式解析器"""

    # 匹配单个骰点项: 1d6, d20, 2d10
    DICE_TERM_PATTERN = re.compile(r"(\d*)d(\d+)", re.IGNORECASE)

    @classmethod
    def parse(cls, expression: str) -> Optional[DiceExpression]:
        """解析骰点表达式，支持 1d6+1d4+5, 2d6-1d4-2 等"""
        expression = expression.strip().lower()
        if not expression:
            return None

        terms: List[DiceTerm] = []
        modifier = 0
        raw = expression

        # 将表达式拆分为各个项（保留符号）
        # 例如: "1d6+1d4-2" -> ["+1d6", "+1d4", "-2"]
        # 先在开头加 + 号方便处理
        expr = "+" + expression.replace(" ", "")

        # 匹配所有项: +1d6, -1d4, +5, -2
        token_pattern = re.compile(r"([+-])(\d*d\d+|\d+)", re.IGNORECASE)
        tokens = token_pattern.findall(expr)

        if not tokens:
            return None

        has_dice = False
        for sign, value in tokens:
            negative = sign == "-"

            # 检查是否是骰点项
            dice_match = cls.DICE_TERM_PATTERN.fullmatch(value)
            if dice_match:
                has_dice = True
                count_str, sides_str = dice_match.groups()
                count = int(count_str) if count_str else 1
                sides = int(sides_str)

                # 验证合理性
                if count < 1 or count > 100:
                    return None
                if sides < 1 or sides > 1000:
                    return None

                terms.append(DiceTerm(count=count, sides=sides, negative=negative))
            else:
                # 常数项
                num = int(value)
                if negative:
                    modifier -= num
                else:
                    modifier += num

        # 必须至少有一个骰点项
        if not has_dice:
            return None

        return DiceExpression(terms=terms, modifier=modifier, raw=raw)

    @classmethod
    def is_valid(cls, expression: str) -> bool:
        """检查表达式是否有效"""
        return cls.parse(expression) is not None
