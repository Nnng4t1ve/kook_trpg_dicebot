"""技能别名系统"""

# 属性别名映射 -> 标准属性名
ATTRIBUTE_ALIASES = {
    # STR 力量
    "str": "STR", "力量": "STR", "力": "STR",
    # CON 体质
    "con": "CON", "体质": "CON", "体": "CON",
    # SIZ 体型
    "siz": "SIZ", "体型": "SIZ",
    # DEX 敏捷
    "dex": "DEX", "敏捷": "DEX", "敏": "DEX",
    # APP 外貌
    "app": "APP", "外貌": "APP", "外": "APP", "魅力": "APP",
    # INT 智力/灵感
    "int": "INT", "智力": "INT", "智": "INT", "灵感": "INT",
    # POW 意志
    "pow": "POW", "意志": "POW", "精神": "POW",
    # EDU 教育
    "edu": "EDU", "教育": "EDU", "知识": "EDU",
    # LUK 幸运
    "luk": "LUK", "luck": "LUK", "幸运": "LUK", "运气": "LUK",
}

# 技能别名映射 -> 标准技能名
SKILL_ALIASES = {
    # 侦查相关
    "侦查": "侦查", "检查": "侦查", "观察": "侦查", "搜索": "侦查",
    "spot": "侦查", "spot hidden": "侦查",
    # 聆听
    "聆听": "聆听", "倾听": "聆听", "听": "聆听", "listen": "聆听",
    # 图书馆
    "图书馆": "图书馆", "图书馆使用": "图书馆", "library": "图书馆",
    # 心理学
    "心理学": "心理学", "心理": "心理学", "psychology": "心理学",
    # 闪避
    "闪避": "闪避", "dodge": "闪避", "躲避": "闪避",
    # 斗殴
    "斗殴": "斗殴", "格斗": "斗殴", "肉搏": "斗殴", "brawl": "斗殴",
    # 潜行
    "潜行": "潜行", "隐匿": "潜行", "stealth": "潜行", "躲藏": "潜行",
    # 说服
    "说服": "说服", "劝说": "说服", "persuade": "说服",
    # 话术
    "话术": "话术", "快速交谈": "话术", "fast talk": "话术",
    # 魅惑
    "魅惑": "魅惑", "取悦": "魅惑", "charm": "魅惑",
    # 恐吓
    "恐吓": "恐吓", "威胁": "恐吓", "intimidate": "恐吓",
    # 急救
    "急救": "急救", "first aid": "急救",
    # 医学
    "医学": "医学", "medicine": "医学",
    # 驾驶
    "驾驶": "驾驶", "汽车驾驶": "驾驶", "drive": "驾驶",
    # 电气维修
    "电气维修": "电气维修", "电工": "电气维修", "electrical": "电气维修",
    # 机械维修
    "机械维修": "机械维修", "机修": "机械维修", "mechanical": "机械维修",
    # 攀爬
    "攀爬": "攀爬", "climb": "攀爬", "爬": "攀爬",
    # 游泳
    "游泳": "游泳", "swim": "游泳",
    # 跳跃
    "跳跃": "跳跃", "jump": "跳跃", "跳": "跳跃",
    # 投掷
    "投掷": "投掷", "throw": "投掷",
    # 神秘学
    "神秘学": "神秘学", "occult": "神秘学",
    # 克苏鲁神话
    "克苏鲁神话": "克苏鲁神话", "cm": "克苏鲁神话", "cthulhu": "克苏鲁神话",
}


class SkillResolver:
    """技能名称解析器"""
    
    def __init__(self):
        # 合并所有别名（小写化）
        self._aliases = {}
        for alias, standard in ATTRIBUTE_ALIASES.items():
            self._aliases[alias.lower()] = standard
        for alias, standard in SKILL_ALIASES.items():
            self._aliases[alias.lower()] = standard
    
    def resolve(self, name: str) -> str:
        """解析技能/属性名称，返回标准名称"""
        name_lower = name.lower().strip()
        
        # 先查别名表
        if name_lower in self._aliases:
            return self._aliases[name_lower]
        
        # 没找到就返回原名（可能是用户自定义技能）
        return name
    
    def is_attribute(self, name: str) -> bool:
        """判断是否为属性"""
        resolved = self.resolve(name)
        return resolved.upper() in ("STR", "CON", "SIZ", "DEX", "APP", "INT", "POW", "EDU", "LUK")
    
    def add_alias(self, alias: str, standard: str):
        """添加自定义别名"""
        self._aliases[alias.lower()] = standard


# 全局实例
skill_resolver = SkillResolver()
