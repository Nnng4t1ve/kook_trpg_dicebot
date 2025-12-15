# COC TRPG Dice Bot for KOOK

一个基于 KOOK 平台的 COC (Call of Cthulhu) TRPG 骰子机器人。

## 功能特性

- 🎲 **骰点功能**: 支持标准骰点语法 (如 `1d100`, `3d6`, `2d6+3`)
- 📋 **角色卡管理**: JSON 格式角色卡导入、用户隔离、多角色切换
- 🎯 **技能检定**: 支持 COC6/COC7 规则，可配置大成功/大失败村规
- 👥 **用户隔离**: 每个用户独立管理自己的角色卡
- ⚙️ **规则切换**: 支持 COC6/COC7 规则切换，自定义村规

## 技术架构

- **语言**: Python 3.10+
- **异步框架**: asyncio + aiohttp
- **数据存储**: SQLite (异步 aiosqlite)
- **日志系统**: loguru
- **配置管理**: pydantic-settings

## 项目结构

```
trpg_dice_bot_in_kook/
├── src/
│   ├── __init__.py
│   ├── main.py              # 入口文件
│   ├── config.py            # 配置管理
│   ├── bot/
│   │   ├── __init__.py
│   │   ├── client.py        # KOOK WebSocket 客户端
│   │   └── handler.py       # 消息处理器
│   ├── dice/
│   │   ├── __init__.py
│   │   ├── parser.py        # 骰点表达式解析
│   │   ├── roller.py        # 骰点执行
│   │   └── rules.py         # COC 规则实现
│   ├── character/
│   │   ├── __init__.py
│   │   ├── models.py        # 角色卡模型
│   │   ├── manager.py       # 角色卡管理
│   │   └── importer.py      # 角色卡导入
│   └── storage/
│       ├── __init__.py
│       └── database.py      # 数据库操作
├── data/                    # 数据存储目录
├── logs/                    # 日志目录
├── requirements.txt
├── .env.example
└── README.md
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置

复制 `.env.example` 为 `.env` 并填写配置:

```bash
cp .env.example .env
```

编辑 `.env` 文件:

```env
KOOK_TOKEN=your_bot_token_here
```

### 3. 运行

```bash
python -m src.main
```

## 命令列表

### 骰点命令

| 命令 | 说明 | 示例 |
|------|------|------|
| `.r <表达式>` | 基础骰点 | `.r 1d100`, `.r 3d6+5` |
| `.ra <技能名>` | 技能检定 | `.ra 侦查`, `.ra 图书馆` |
| `.rc <技能名> <值>` | 指定值检定 | `.rc 侦查 60` |

### KP 命令 (交互式检定)

| 命令 | 说明 | 示例 |
|------|------|------|
| `.check <技能名> [描述]` | 发起检定 (玩家点击按钮) | `.check 侦查 仔细搜索房间` |

KP 使用 `.check` 命令后，Bot 会发送一个带按钮的卡片消息，玩家点击按钮即可自动进行检定，无需每个人都输入命令。

### 角色卡命令

| 命令 | 说明 | 示例 |
|------|------|------|
| `.pc new <JSON>` | 导入角色卡 | `.pc new {"name":"调查员",...}` |
| `.pc list` | 列出角色卡 | `.pc list` |
| `.pc switch <名称>` | 切换角色卡 | `.pc switch 调查员` |
| `.pc show` | 显示当前角色 | `.pc show` |
| `.pc del <名称>` | 删除角色卡 | `.pc del 调查员` |

### 规则命令

| 命令 | 说明 | 示例 |
|------|------|------|
| `.rule coc6` | 切换到 COC6 规则 | `.rule coc6` |
| `.rule coc7` | 切换到 COC7 规则 | `.rule coc7` |
| `.rule show` | 显示当前规则 | `.rule show` |
| `.rule crit <值>` | 设置大成功阈值 | `.rule crit 5` |
| `.rule fumble <值>` | 设置大失败阈值 | `.rule fumble 96` |

### 帮助命令

| 命令 | 说明 |
|------|------|
| `.help` | 显示帮助信息 |

## 角色卡格式

```json
{
  "name": "调查员名称",
  "attributes": {
    "STR": 50,
    "CON": 60,
    "SIZ": 65,
    "DEX": 70,
    "APP": 55,
    "INT": 75,
    "POW": 60,
    "EDU": 80,
    "LUK": 50
  },
  "skills": {
    "侦查": 60,
    "图书馆": 50,
    "聆听": 40,
    "心理学": 35
  },
  "hp": 12,
  "mp": 12,
  "san": 60
}
```

## COC 规则说明

### COC7 规则 (默认)

- **大成功**: 骰出 1-5 (可配置)
- **大失败**: 骰出 96-100 (可配置)，技能值 < 50 时为 96-100，≥ 50 时仅 100
- **成功等级**:
  - 极难成功: ≤ 技能值/5
  - 困难成功: ≤ 技能值/2
  - 普通成功: ≤ 技能值
  - 失败: > 技能值

### COC6 规则

- **大成功**: 骰出 1-5 (可配置)
- **大失败**: 骰出 96-100 (可配置)
- **成功等级**:
  - 普通成功: ≤ 技能值
  - 失败: > 技能值

## License

MIT License
