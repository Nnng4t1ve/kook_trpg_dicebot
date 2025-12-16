# COC TRPG Dice Bot for KOOK

一个功能完善的 KOOK 平台 COC (Call of Cthulhu) TRPG 骰子机器人。

## 功能特性

### 🎲 骰点系统
- 标准骰点语法 (`1d100`, `3d6`, `2d6+3`, `1d6+1d4`)
- 奖励骰/惩罚骰支持 (`r1`, `r2`, `p1`, `p2`)
- 紧凑格式支持 (`.rd100`, `.ra侦查50`)

### � 角色卡管理定
- Web 界面在线创建角色卡
- JSON 格式导入/导出
- 多角色切换
- 用户数据隔离

### 🎯 技能检定
- COC6/COC7 规则支持
- 大成功/大失败村规自定义
- 技能别名系统 (力量/力/str → STR)
- 奖励骰/惩罚骰

### 🖱️ 交互式检定
- KP 发起检定，玩家点击按钮骰点
- 对抗检定 (支持不同技能对抗)
- 检定结果卡片展示

### 💀 SAN Check
- 支持骰点表达式 (`.sc 0/1d6`, `.sc 1d4/2d6`)
- 自动扣减 SAN 值
- 触发临时疯狂判定 (单次损失≥5)
- 永久疯狂提示 (SAN归零)

### 📈 技能成长
- Web 界面成长检定
- D100 > 当前技能值 = 成功
- 成功后 +1D10

### ⚙️ 角色卡创建系统
- 🎲 随机属性生成 (COC7 标准公式)
- 自动计算派生属性 (HP/MP/SAN/MOV/体格/伤害加值)
- 职业点数/兴趣点数计算
- 可选属性勾选计算职业点数
- 自定义技能名称和初始值

## 命令列表

### 骰点命令

| 命令 | 说明 | 示例 |
|------|------|------|
| `.r / .rd <表达式>` | 基础骰点 | `.rd 1d100`, `.r 3d6+5` |
| `.rd r2 d100` | 带奖励骰 | `.rd r2 d100` |
| `.rd p1 d100` | 带惩罚骰 | `.rd p1 d100` |
| `.ra <技能名>` | 技能检定 | `.ra 侦查`, `.ra侦查50` |
| `.ra r2 <技能>` | 带奖励骰检定 | `.ra r2 侦查` |
| `.rc <技能> <值>` | 指定值检定 | `.rc 侦查 60` |
| `.sc <成功>/<失败>` | SAN Check | `.sc 0/1d6`, `.sc 1d4/2d6` |

### KP 命令

| 命令 | 说明 | 示例 |
|------|------|------|
| `.check <技能> [描述]` | 发起检定 | `.check 侦查 搜索房间` |
| `.ad @用户 <技能>` | 对抗检定 | `.ad @张三 力量` |
| `.ad @用户 <技能1> <技能2>` | 不同技能对抗 | `.ad @张三 斗殴 闪避` |

### 角色卡命令

| 命令 | 说明 | 示例 |
|------|------|------|
| `.pc create` | 获取在线创建链接 | `.pc create` |
| `.pc new <JSON>` | 导入角色卡 | `.pc new {"name":"调查员",...}` |
| `.pc grow <角色> <技能...>` | 技能成长 | `.pc grow 张三 侦查 聆听` |
| `.pc list` | 列出角色卡 | `.pc list` |
| `.pc switch <名称>` | 切换角色卡 | `.pc switch 调查员` |
| `.pc show` | 显示当前角色 | `.pc show` |
| `.pc del <名称>` | 删除角色卡 | `.pc del 调查员` |

### 规则命令

| 命令 | 说明 | 示例 |
|------|------|------|
| `.rule show` | 显示当前规则 | `.rule show` |
| `.rule coc6/coc7` | 切换规则 | `.rule coc7` |
| `.rule crit <值>` | 设置大成功阈值 | `.rule crit 5` |
| `.rule fumble <值>` | 设置大失败阈值 | `.rule fumble 96` |

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 创建 MySQL 数据库

```sql
CREATE DATABASE trpg_dicebot CHARACTER SET utf8mb4;
```

### 3. 配置

复制 `.env.example` 为 `.env` 并填写:

```env
KOOK_TOKEN=your_bot_token_here

# MySQL 配置
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=trpg_dicebot

# Web 服务配置
WEB_PORT=8080
WEB_BASE_URL=http://your-server-ip:8080
```

### 4. 运行

```bash
python -m src.main
```

## Docker 部署

### 使用 Docker Compose (推荐)

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env 填写 KOOK_TOKEN, DB_PASSWORD, WEB_BASE_URL

# 2. 启动服务
docker-compose up -d

# 3. 查看日志
docker-compose logs -f bot
```

### 单独构建镜像

```bash
# 构建
docker build -t coc-dice-bot .

# 运行 (需要外部 MySQL)
docker run -d \
  --name coc-dice-bot \
  -p 11021:11021 \
  -e KOOK_TOKEN=your_token \
  -e DB_HOST=your_mysql_host \
  -e DB_PASSWORD=your_password \
  -e WEB_BASE_URL=http://your-ip:11021 \
  coc-dice-bot
```

## 技术架构

- **语言**: Python 3.10+
- **异步框架**: asyncio + aiohttp
- **数据存储**: MySQL (aiomysql)
- **Web 框架**: FastAPI + Jinja2
- **日志**: loguru

## 项目结构

```
trpg_dice_bot_in_kook/
├── src/
│   ├── main.py              # 入口
│   ├── config.py            # 配置
│   ├── bot/                 # Bot 核心
│   │   ├── client.py        # WebSocket 客户端
│   │   ├── handler.py       # 消息处理
│   │   ├── card_builder.py  # 卡片构建
│   │   └── check_manager.py # 检定管理
│   ├── dice/                # 骰点系统
│   │   ├── parser.py        # 表达式解析
│   │   ├── roller.py        # 骰点执行
│   │   ├── rules.py         # COC 规则
│   │   └── skill_alias.py   # 技能别名
│   ├── character/           # 角色卡
│   │   ├── models.py        # 数据模型
│   │   ├── manager.py       # 角色管理
│   │   └── importer.py      # 导入器
│   ├── storage/             # 数据存储
│   │   └── database.py      # MySQL
│   ├── data/                # 数据定义
│   │   ├── skills.py        # 技能列表
│   │   └── madness.py       # 疯狂症状
│   └── web/                 # Web 服务
│       ├── server.py        # FastAPI
│       └── templates/       # 页面模板
├── requirements.txt
└── .env.example
```

## COC 规则说明

### COC7 规则 (默认)

- **大成功**: 1-5 (可配置)
- **大失败**: 技能值 < 50 时 96-100，≥ 50 时仅 100
- **成功等级**: 极难(≤1/5) / 困难(≤1/2) / 普通(≤技能值)

### COC6 规则

- **大成功**: 1-5 (可配置)
- **大失败**: 96-100 (可配置)
- **成功等级**: 成功(≤技能值) / 失败(>技能值)

## 角色卡 JSON 格式

```json
{
  "name": "调查员名称",
  "attributes": {
    "STR": 50, "CON": 60, "SIZ": 65,
    "DEX": 70, "APP": 55, "INT": 75,
    "POW": 60, "EDU": 80, "LUK": 50
  },
  "skills": {
    "侦查": 60,
    "图书馆": 50,
    "聆听": 40
  },
  "hp": 12,
  "mp": 12,
  "san": 60
}
```

## License

MIT License
