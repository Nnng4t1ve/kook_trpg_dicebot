# COC TRPG Dice Bot for KOOK

一个基于 KOOK 平台的 COC (Call of Cthulhu) TRPG 骰子机器人。

## 功能特性

- 🎲 **骰点功能**: 支持标准骰点语法 (如 `1d100`, `3d6`, `2d6+3`)
- 📋 **角色卡管理**: JSON 格式角色卡导入、用户隔离、多角色切换
- 🌐 **在线角色卡创建**: Web 界面创建角色卡，无需手写 JSON
- 🎯 **技能检定**: 支持 COC6/COC7 规则，可配置大成功/大失败村规
- 🖱️ **交互式检定**: KP 发起检定，玩家点击按钮即可骰点
- 👥 **用户隔离**: 每个用户独立管理自己的角色卡
- ⚙️ **规则切换**: 支持 COC6/COC7 规则切换，自定义村规

## 技术架构

- **语言**: Python 3.10+
- **异步框架**: asyncio + aiohttp
- **数据存储**: MySQL (异步 aiomysql)
- **Web 框架**: FastAPI + Jinja2
- **日志系统**: loguru
- **配置管理**: pydantic-settings

## 项目结构

```
trpg_dice_bot_in_kook/
├── src/
│   ├── main.py              # 入口文件
│   ├── config.py            # 配置管理
│   ├── bot/                 # Bot 核心
│   │   ├── client.py        # KOOK WebSocket 客户端
│   │   ├── handler.py       # 消息处理器
│   │   ├── card_builder.py  # 卡片消息构建
│   │   └── check_manager.py # 检定管理
│   ├── dice/                # 骰点系统
│   │   ├── parser.py        # 表达式解析
│   │   ├── roller.py        # 骰点执行
│   │   └── rules.py         # COC 规则
│   ├── character/           # 角色卡
│   │   ├── models.py        # 数据模型
│   │   ├── manager.py       # 角色管理
│   │   └── importer.py      # 导入器
│   ├── storage/             # 数据存储
│   │   └── database.py      # MySQL 操作
│   └── web/                 # Web 服务
│       ├── server.py        # FastAPI 应用
│       └── templates/       # 页面模板
├── logs/                    # 日志目录
├── requirements.txt
└── .env.example
```

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

复制 `.env.example` 为 `.env` 并填写配置:

```bash
cp .env.example .env
```

编辑 `.env` 文件:

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

启动后会同时运行 Bot 和 Web 服务。

## 命令列表

### 骰点命令

| 命令 | 说明 | 示例 |
|------|------|------|
| `.r / .rd <表达式>` | 基础骰点 | `.rd 1d100`, `.r 3d6+5` |
| `.ra <技能名>` | 技能检定 | `.ra 侦查` |
| `.rc <技能名> <值>` | 指定值检定 | `.rc 侦查 60` |

### KP 命令 (交互式检定)

| 命令 | 说明 | 示例 |
|------|------|------|
| `.check <技能名> [描述]` | 发起检定 | `.check 侦查 仔细搜索房间` |

KP 使用 `.check` 命令后，Bot 发送带按钮的卡片，玩家点击按钮即可自动检定。

### 角色卡命令

| 命令 | 说明 | 示例 |
|------|------|------|
| `.pc create` | 获取在线创建链接 | `.pc create` |
| `.pc new <JSON>` | 导入角色卡 | `.pc new {"name":"调查员",...}` |
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

## 在线角色卡创建

1. 在 KOOK 发送 `.pc create`
2. Bot 返回专属创建链接（10 分钟有效）
3. 打开链接，填写角色卡信息
4. 点击「创建角色卡」直接保存到数据库
5. 或点击「生成导入指令」复制 JSON 命令

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

## COC 规则说明

### COC7 规则 (默认)

- **大成功**: 1-5 (可配置)
- **大失败**: 技能值 < 50 时 96-100，≥ 50 时仅 100
- **成功等级**: 极难(≤1/5) / 困难(≤1/2) / 普通(≤技能值)

### COC6 规则

- **大成功**: 1-5 (可配置)
- **大失败**: 96-100 (可配置)
- **成功等级**: 成功(≤技能值) / 失败(>技能值)

## License

MIT License
