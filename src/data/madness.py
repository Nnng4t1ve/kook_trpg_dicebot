"""临时疯狂症状表"""
import random

# 临时疯狂症状 (1d10)
TEMPORARY_MADNESS = [
    {
        "name": "失忆",
        "description": "调查员会发现自己只记得最后身处的安全地点，却没有任何来到这里的记忆。",
        "duration": "1D10轮",
    },
    {
        "name": "假性残疾",
        "description": "调查员陷入了心理性的失明、失聪以及躯体缺失感中。",
        "duration": "1D10轮",
    },
    {
        "name": "暴力倾向",
        "description": "调查员陷入了六亲不认的暴力行为中，对周围的敌人与友方进行着无差别的攻击。",
        "duration": "1D10轮",
    },
    {
        "name": "偏执",
        "description": "调查员陷入了严重的偏执妄想之中。有人在暗中窥视着他们，同伴中有人背叛了他们，没有人可以信任，万事皆虚。",
        "duration": "1D10轮",
    },
    {
        "name": "人际依赖",
        "description": "守秘人适当参考调查员的背景中重要之人的条目，调查员因为一些原因而降他人误认为了他重要的人并且努力的会与那个人保持那种关系。",
        "duration": "1D10轮",
    },
    {
        "name": "昏厥",
        "description": "调查员当场昏倒，并需要1D10轮才能苏醒。",
        "duration": "1D10轮",
    },
    {
        "name": "逃避行为",
        "description": "调查员会用任何的手段试图逃离现在所处的位置，即使这意味着开走唯一一辆交通工具并将其它人抛诸脑后，调查员会试图逃离。",
        "duration": "1D10轮",
    },
    {
        "name": "竭嘶底里",
        "description": "调查员表现出大笑、哭泣、嘶吼、害怕等的极端情绪表现。",
        "duration": "1D10轮",
    },
    {
        "name": "恐惧",
        "description": "调查员通过一次D100或者由守秘人选择，来从恐惧症状表中选择一个恐惧源，就算这一恐惧的事物是并不存在的，调查员的症状会持续。",
        "duration": "1D10轮",
    },
    {
        "name": "躁狂",
        "description": "调查员通过一次D100或者由守秘人选择，来从躁狂症状表中选择一个躁狂的诱因，这个症状将会持续。",
        "duration": "1D10轮",
    },
]


def roll_temporary_madness() -> dict:
    """随机一个临时疯狂症状"""
    roll = random.randint(1, 10)
    symptom = TEMPORARY_MADNESS[roll - 1]
    duration_roll = random.randint(1, 10)
    return {
        "roll": roll,
        "name": symptom["name"],
        "description": symptom["description"],
        "duration": f"{duration_roll}轮",
        "duration_roll": duration_roll,
    }
