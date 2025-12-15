"""COC 规则实现"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class SuccessLevel(Enum):
    """成功等级"""
    CRITICAL = "大成功"
    EXTREME = "极难成功"
    HARD = "困难成功"
    REGULAR = "成功"
    FAILURE = "失败"
    FUMBLE = "大失败"


@dataclass
class CheckResult:
    """检定结果"""
    roll: int
    target: int
    level: SuccessLevel
    rule_name: str
    
    def __str__(self) -> str:
        return f"D100={self.roll}/{self.target} [{self.level.value}]"
    
    @property
    def is_success(self) -> bool:
        return self.level in (
            SuccessLevel.CRITICAL,
            SuccessLevel.EXTREME,
            SuccessLevel.HARD,
            SuccessLevel.REGULAR
        )


class COCRule(ABC):
    """COC 规则基类"""
    
    def __init__(self, critical_threshold: int = 5, fumble_threshold: int = 96):
        self.critical_threshold = critical_threshold
        self.fumble_threshold = fumble_threshold
    
    @property
    @abstractmethod
    def name(self) -> str:
        """规则名称"""
        pass
    
    @abstractmethod
    def check(self, roll: int, target: int) -> CheckResult:
        """执行检定"""
        pass


class COC6Rule(COCRule):
    """COC6 规则"""
    
    @property
    def name(self) -> str:
        return "COC6"
    
    def check(self, roll: int, target: int) -> CheckResult:
        """COC6 检定: 只有成功/失败，加上大成功/大失败"""
        # 大成功
        if roll <= self.critical_threshold:
            level = SuccessLevel.CRITICAL
        # 大失败
        elif roll >= self.fumble_threshold:
            level = SuccessLevel.FUMBLE
        # 普通成功
        elif roll <= target:
            level = SuccessLevel.REGULAR
        # 失败
        else:
            level = SuccessLevel.FAILURE
        
        return CheckResult(roll=roll, target=target, level=level, rule_name=self.name)


class COC7Rule(COCRule):
    """COC7 规则"""
    
    @property
    def name(self) -> str:
        return "COC7"
    
    def check(self, roll: int, target: int) -> CheckResult:
        """COC7 检定: 有极难/困难/普通成功等级"""
        extreme = target // 5  # 极难成功阈值
        hard = target // 2     # 困难成功阈值
        
        # 大成功: 骰出 1-critical_threshold
        if roll <= self.critical_threshold:
            level = SuccessLevel.CRITICAL
        # 大失败: 技能值 < 50 时 fumble_threshold-100，>= 50 时仅 100
        elif (target < 50 and roll >= self.fumble_threshold) or (target >= 50 and roll == 100):
            level = SuccessLevel.FUMBLE
        # 极难成功
        elif roll <= extreme:
            level = SuccessLevel.EXTREME
        # 困难成功
        elif roll <= hard:
            level = SuccessLevel.HARD
        # 普通成功
        elif roll <= target:
            level = SuccessLevel.REGULAR
        # 失败
        else:
            level = SuccessLevel.FAILURE
        
        return CheckResult(roll=roll, target=target, level=level, rule_name=self.name)


def get_rule(rule_name: str, critical: int = 5, fumble: int = 96) -> COCRule:
    """获取规则实例"""
    rules = {
        "coc6": COC6Rule,
        "coc7": COC7Rule,
    }
    rule_class = rules.get(rule_name.lower(), COC7Rule)
    return rule_class(critical_threshold=critical, fumble_threshold=fumble)
