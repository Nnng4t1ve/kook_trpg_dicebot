"""骰点执行器"""
import random
from dataclasses import dataclass, field
from typing import List, Tuple

from .parser import DiceExpression


@dataclass
class RollResult:
    """骰点结果"""

    expression: DiceExpression
    rolls: List[Tuple[str, List[int], int]] = field(
        default_factory=list
    )  # [(描述, 骰点列表, 小计), ...]
    total: int = 0

    def __str__(self) -> str:
        # 简单情况：单个骰点无修正
        if len(self.rolls) == 1 and self.expression.modifier == 0:
            desc, dice_rolls, subtotal = self.rolls[0]
            if len(dice_rolls) == 1:
                return f"{self.expression.raw} = {self.total}"
            rolls_str = "+".join(map(str, dice_rolls))
            return f"{self.expression.raw} = [{rolls_str}] = {self.total}"

        # 复杂情况：多个骰点或有修正
        parts = []
        for desc, dice_rolls, subtotal in self.rolls:
            if len(dice_rolls) == 1:
                parts.append(f"{desc}={dice_rolls[0]}")
            else:
                rolls_str = "+".join(map(str, dice_rolls))
                parts.append(f"{desc}=[{rolls_str}]={subtotal}")

        if self.expression.modifier != 0:
            parts.append(f"({self.expression.modifier:+d})")

        detail = " ".join(parts)
        return f"{self.expression.raw} = {detail} = {self.total}"


class DiceRoller:
    """骰点执行器"""

    @staticmethod
    def roll(expr: DiceExpression) -> RollResult:
        """执行骰点"""
        rolls_info: List[Tuple[str, List[int], int]] = []
        total = 0

        for term in expr.terms:
            dice_rolls = [random.randint(1, term.sides) for _ in range(term.count)]
            subtotal = sum(dice_rolls)

            if term.negative:
                total -= subtotal
                desc = f"-{term.count}d{term.sides}"
            else:
                total += subtotal
                desc = f"{term.count}d{term.sides}"

            rolls_info.append((desc, dice_rolls, subtotal))

        total += expr.modifier

        return RollResult(expression=expr, rolls=rolls_info, total=total)

    @staticmethod
    def roll_d100() -> int:
        """快速骰 1d100"""
        return random.randint(1, 100)

    @staticmethod
    def roll_d100_with_bonus(bonus: int = 0, penalty: int = 0) -> "BonusRollResult":
        """
        带奖励骰/惩罚骰的 d100
        bonus: 奖励骰数量 (取十位最小)
        penalty: 惩罚骰数量 (取十位最大)
        """
        # 基础骰点：十位和个位分开
        tens_digit = random.randint(0, 9)  # 十位 0-9
        ones_digit = random.randint(0, 9)  # 个位 0-9

        # 额外的十位骰
        extra_count = max(bonus, penalty)
        extra_tens = [random.randint(0, 9) for _ in range(extra_count)]

        # 所有十位候选
        all_tens = [tens_digit] + extra_tens

        # 根据奖励/惩罚选择十位
        if bonus > penalty:
            # 奖励骰：取最小的十位
            chosen_tens = min(all_tens)
        elif penalty > bonus:
            # 惩罚骰：取最大的十位
            chosen_tens = max(all_tens)
        else:
            # 相等则抵消，用原始十位
            chosen_tens = tens_digit

        # 计算最终结果 (00 + 0 = 100)
        if chosen_tens == 0 and ones_digit == 0:
            final = 100
        else:
            final = chosen_tens * 10 + ones_digit

        return BonusRollResult(
            tens_digit=tens_digit,
            ones_digit=ones_digit,
            extra_tens=extra_tens,
            chosen_tens=chosen_tens,
            final=final,
            bonus=bonus,
            penalty=penalty,
        )


@dataclass
class BonusRollResult:
    """奖励骰/惩罚骰结果"""

    tens_digit: int  # 原始十位
    ones_digit: int  # 个位
    extra_tens: List[int]  # 额外十位骰
    chosen_tens: int  # 选中的十位
    final: int  # 最终结果
    bonus: int = 0  # 奖励骰数量
    penalty: int = 0  # 惩罚骰数量

    def __str__(self) -> str:
        all_tens = [self.tens_digit] + self.extra_tens
        tens_str = ", ".join(str(t * 10) for t in all_tens)

        if self.bonus > 0:
            bp_type = f"奖励骰×{self.bonus}"
        elif self.penalty > 0:
            bp_type = f"惩罚骰×{self.penalty}"
        else:
            bp_type = ""

        if bp_type:
            return f"D100={self.final} (十位:[{tens_str}]→{self.chosen_tens * 10}, 个位:{self.ones_digit}) {bp_type}"
        return f"D100={self.final}"
