"""COC7 技能数据"""

# 从技能表.json整理的完整技能列表
# 格式: (技能名, 初始值, 分类, 是否可自定义名称, 是否可自定义初始值)
# 可自定义名称的技能格式为 "技能名:" 表示需要填写具体名称
COC7_SKILLS = [
    # 常用技能
    ("侦查", 25, "常用", False, False),
    ("聆听", 20, "常用", False, False),
    ("图书馆使用", 20, "常用", False, False),
    ("心理学", 10, "常用", False, False),
    ("闪避", 0, "常用", False, False),  # 基础值=DEX/2，前端特殊处理
    ("急救", 30, "常用", False, False),
    
    # 交涉技能
    ("说服", 10, "交涉", False, False),
    ("话术", 5, "交涉", False, False),
    ("取悦", 15, "交涉", False, False),
    ("恐吓", 15, "交涉", False, False),
    ("信用评级", 0, "交涉", False, False),
    
    # 学识技能
    ("会计", 5, "学识", False, False),
    ("人类学", 1, "学识", False, False),
    ("考古学", 1, "学识", False, False),
    ("历史", 5, "学识", False, False),
    ("法律", 5, "学识", False, False),
    ("博物学", 10, "学识", False, False),
    ("神秘学", 5, "学识", False, False),
    ("克苏鲁神话", 0, "学识", False, False),
    
    # 调查技能
    ("估价", 5, "调查", False, False),
    ("追踪", 10, "调查", False, False),
    ("导航", 10, "调查", False, False),
    ("读唇", 1, "调查", False, False),
    
    # 运动技能
    ("攀爬", 20, "运动", False, False),
    ("跳跃", 20, "运动", False, False),
    ("游泳", 20, "运动", False, False),
    ("投掷", 20, "运动", False, False),
    ("骑术", 5, "运动", False, False),
    ("潜水", 1, "运动", False, False),
    ("潜行", 20, "运动", False, False),
    
    # 技术技能
    ("汽车驾驶", 20, "技术", False, False),
    ("驾驶:", 1, "技术", True, False),
    ("电气维修", 10, "技术", False, False),
    ("机械维修", 10, "技术", False, False),
    ("操作重型机械", 1, "技术", False, False),
    ("锁匠", 1, "技术", False, False),
    ("乔装", 5, "技术", False, False),
    ("计算机使用Ω", 5, "技术", False, False),
    ("电子学Ω", 1, "技术", False, False),

    # 医疗技能
    ("医学", 1, "医疗", False, False),
    ("精神分析", 1, "医疗", False, False),
    ("催眠", 1, "医疗", False, False),
    
    # 科学技能 - 可自定义名称和初始值
    ("科学:", 1, "科学", True, True),
    ("科学:", 1, "科学", True, True),
    ("科学:", 1, "科学", True, True),
    
    # 艺术/手艺 - 可自定义名称和初始值
    ("技艺:", 5, "艺术", True, True),
    ("技艺:", 5, "艺术", True, True),
    ("技艺:", 5, "艺术", True, True),
    
    # 战斗技能
    ("格斗：斗殴", 25, "战斗", False, False),
    ("格斗：斧", 15, "战斗", False, False),
    ("格斗：剑", 20, "战斗", False, False),
    ("格斗:", 0, "战斗", True, True),  # 可自定义
    ("射击：手枪", 20, "战斗", False, False),
    ("射击：步枪/霰弹枪", 25, "战斗", False, False),
    ("射击：冲锋枪", 15, "战斗", False, False),
    ("射击:", 0, "战斗", True, True),  # 可自定义
    
    # 其他
    ("妙手", 10, "其他", False, False),
    ("生存:", 10, "其他", True, False),
    ("驯兽", 5, "其他", False, False),
    ("炮术", 1, "其他", False, False),
    ("爆破", 1, "其他", False, False),
    
    # 语言 - 母语基础值=EDU，外语可自定义名称
    ("母语:", 0, "语言", True, False),  # 基础值=EDU，前端特殊处理
    ("外语:", 1, "语言", True, False),
    ("外语:", 1, "语言", True, False),
    ("外语:", 1, "语言", True, False),
]

# 按分类组织，包含完整信息
SKILLS_BY_CATEGORY = {}
for name, initial, category, custom_name, custom_base in COC7_SKILLS:
    if category not in SKILLS_BY_CATEGORY:
        SKILLS_BY_CATEGORY[category] = []
    SKILLS_BY_CATEGORY[category].append({
        "name": name,
        "initial": initial,
        "customName": custom_name,  # 是否可自定义名称
        "customBase": custom_base,  # 是否可自定义初始值
    })
