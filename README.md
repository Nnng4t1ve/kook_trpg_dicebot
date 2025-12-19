# 🎲 COC TRPG Dice Bot for KOOK

一个功能（待）完善的 KOOK 平台 COC (Call of Cthulhu) TRPG 骰子机器人。

## ✨ 功能特性

### 🎲 骰点系统
- 标准骰点语法 (`1d100`, `3d6`, `2d6+3`, `1d6+1d4`)
- 奖励骰/惩罚骰支持 (`r1`, `r2`, `p1`, `p2`)
- 紧凑格式支持 (`.rd100`, `.ra侦查50`)

### 👤 角色卡管理
- Web 界面在线创建角色卡
- JSON 格式导入/导出
- 多角色切换与用户数据隔离
- 在线车卡与快捷审卡系统

### 🎯 技能检定
- COC6/COC7 规则支持
- 大成功/大失败村规自定义
- 技能别名系统 (力量/力/str → STR)
- 交互式检定 (KP 发起，玩家点击按钮骰点)
- 对抗检定 (支持不同技能对抗)

### 💀 SAN Check
- 支持骰点表达式 (`.sc 0/1d6`, `.sc 1d4/2d6`)
- 自动扣减 SAN 值
- 触发临时疯狂判定 (单次损失≥5)
- 永久疯狂提示 (SAN归零)

### 📈 技能成长
- Web 界面成长检定
- D100 > 当前技能值 = 成功
- 成功后 +1D10

### 🤖 AI 背景故事生成
- 根据角色属性、技能、背景要素自动生成详细经历
- 支持 OpenAI 兼容 API
- 5分钟请求冷却机制

### 🤖 NPC 系统
- 快速创建 NPC (支持难度模板)
- NPC 技能检定与对抗
- 按频道隔离存储

---

## 📋 命令列表

### 骰点命令

| 命令 | 说明 | 示例 |
|------|------|------|
| `.r / .rd <表达式>` | 基础骰点 | `.rd 1d100`, `.r 3d6+5` |
| `.rd r2 d100` | 带奖励骰 | `.rd r2 d100` |
| `.rd p1 d100` | 带惩罚骰 | `.rd p1 d100` |
| `.gun <技能> [奖励骰/惩罚骰] t<波数>` | 全自动枪械连发 | `.gun 步枪 r1 t7`, `.gun 冲锋枪 p1 t3` |
| `.ra <技能名>` | 技能检定 | `.ra 侦查`, `.ra侦查50` |
| `.ra r2 <技能>` | 带奖励骰检定 | `.ra r2 侦查` |
| `.ra p1 <技能> t<轮数>` | 多轮检定 | `.ra p1 手枪 t3` |
| `.rc <技能> <值>` | 指定值检定 | `.rc 侦查 60` |
| `.sc <成功>/<失败>` | SAN Check | `.sc 0/1d6`, `.sc 1d4/2d6` |

### 暗骰命令

| 命令 | 说明 | 示例 |
|------|------|------|
| `.rhd <表达式>` | 暗骰（结果私聊发送） | `.rhd 1d100`, `.rhd100`, `.rhd6+d4+3` |
| `.rha <技能>` | 暗骰技能检定 | `.rha侦查`, `.rha侦查50` |
| `.rha r2 <技能>` | 带奖励骰暗骰检定 | `.rhar2侦查`, `.rha r2 侦查` |
| `.rha p1 <技能> t<轮数>` | 多轮暗骰检定 | `.rhap1聆听60`, `.rha p1 t3 聆听` |

**说明:** 暗骰结果私聊发送给发起者，频道只显示"XX 进行了暗骰"

### KP 命令

| 命令 | 说明 | 示例 |
|------|------|------|
| `.check <技能> [描述]` | 发起检定 | `.check 侦查 搜索房间` |
| `.ad @用户 <技能>` | 对抗检定 | `.ad @张三 力量` |
| `.ad @用户 <技能1> <技能2>` | 不同技能对抗 | `.ad @张三 斗殴 闪避` |
| `.ad npc <NPC名> <技能>` | 向 NPC 发起对抗 | `.ad npc 守卫 斗殴` |
| `.ri @用户1 @用户2 npc <NPC名>` | 先攻顺序表 | `.ri @张三 @李四 npc 守卫` |

### NPC 命令

| 命令 | 说明 | 示例 |
|------|------|------|
| `.npc create <名称> [模板]` | 创建 NPC | `.npc create 守卫 困难` |
| `.npc <名称> ra <技能>` | NPC 技能检定 | `.npc 守卫 ra力量` |
| `.npc <名称> gun <技能> [r] t<波数>` | NPC 全自动枪械连发 | `.npc 守卫 gun 冲锋枪 r1 t5` |
| `.npc <名称> ad @用户 <技能>` | NPC 向玩家发起对抗 | `.npc 守卫 ad @张三 斗殴` |
| `.npc list` | 列出当前频道 NPC | `.npc list` |
| `.npc del <名称>` | 删除 NPC | `.npc del 守卫` |
| `.npc <名称>` | 查看 NPC 属性 | `.npc 守卫` |
| `.npc <名称> rha <技能>` | NPC 暗骰检定 | `.npc 守卫 rha 侦查`, `.npc 守卫 rha p1 t3 聆听` |

**NPC 模板管理:**

| 命令 | 说明 | 示例 |
|------|------|------|
| `.npc templates` | 列出所有模板 | `.npc templates` |
| `.npc show <模板名>` | 查看模板详情 | `.npc show 困难` |
| `.npc add <模板名> <定义>` | 添加自定义模板 | 见下方示例 |
| `.npc add help` | 查看模板格式帮助 | `.npc add help` |

**模板定义格式:**
- 骰子公式: `3d6+6` → 结果×5
- 范围: `20-30` → 随机整数
- 固定值: `50`

**示例:** `.npc add 深潜者 力量 3d6+6 体质 3d6+20 敏捷 3d6 格斗 3d6 闪避 20-30`

**内置模板:** `普通`(40-60) / `困难`(50-70) / `极难`(60-80)

**NPC 暗骰:** 结果私聊发送给命令发起者（KP），频道只显示"NPC XX 进行了暗骰检定"

### 角色卡命令

| 命令 | 说明 | 示例 |
|------|------|------|
| `.pc create` | 获取在线创建链接 | `.pc create` |
| `.pc create <上限>` | 带技能上限的创建链接 | `.pc create 75` |
| `.pc create <本职>/<非本职>` | 本职/非本职技能上限 | `.pc create 75/49` |
| `.pc new <JSON>` | 导入角色卡 | `.pc new {"name":"调查员",...}` |
| `.pc grow <技能...>` | 技能成长 | `.pc grow 侦查 聆听` |
| `.pc list` | 列出角色卡 | `.pc list` |
| `.pc switch <名称>` | 切换角色卡 | `.pc switch 调查员` |
| `.pc show` | 显示当前角色 | `.pc show` |
| `.pc del <名称>` | 删除角色卡 | `.pc del 调查员` |
| `.cc <角色名> @KP` | 发起角色卡审核 | `.cc 张三 @KP` |
| `.cc <角色名> @机器人` | 自动审核通过 | `.cc 张三 @机器人` |

**角色卡审核流程:**
1. 在网页上创建角色卡并提交审核
2. 使用 `.cc <角色名> @KP` 发起审核，@ 指定的 KP
3. KP 点击卡片按钮进行审核（通过/拒绝）
4. 审核通过后在网页点击创建，自动保存至数据库无需手动导入

**快速创建（跳过审核）:** 使用 `.cc <角色名> @机器人` 可自动审核通过并创建角色

**技能上限:** 使用 `.pc create 75` 或 `.pc create 75/49` 可设置技能成功率上限，超出上限的技能无法提交审核

### 规则命令

| 命令 | 说明 | 示例 |
|------|------|------|
| `.rule show` | 显示当前规则 | `.rule show` |
| `.rule coc6/coc7` | 切换规则 | `.rule coc7` |
| `.rule crit <值>` | 设置大成功阈值 | `.rule crit 5` |
| `.rule fumble <值>` | 设置大失败阈值 | `.rule fumble 96` |

### 记事本命令

| 命令 | 说明 | 示例 |
|------|------|------|
| `.note` | 查看当前记事本 | `.note` |
| `.note all` | 查看所有记事本 | `.note all` |
| `.note c <名称>` | 创建新记事本 | `.note c 线索` |
| `.note s <名称>` | 切换记事本 | `.note s 线索` |
| `.note i <内容>` | 记录内容 | `.note i 发现了一把钥匙` |
| `.note img <名称>` | 记录图片（发图时附带命令） | `.note img 地图` |
| `.note list` | 查看记录列表 | `.note list` |
| `.note w <序号>` | 查看具体内容 | `.note w 1` |

**说明:** 记事本数据全局共享，同一记事本中所有玩家都能看到彼此添加的内容

### 置顶公告命令

| 命令 | 说明 | 示例 |
|------|------|------|
| `.push` | 将下一条消息发布为卡片并置顶 | `.push` |

**使用流程:**
1. 在频道中发送 `.push`
2. 机器人提示等待内容
3. 发送要置顶的内容（支持 KMarkdown 格式）
4. 机器人自动将内容转为卡片并置顶

**注意:** 此命令只能在频道中使用，私聊无效

### 预定时间投票命令

| 命令 | 说明 | 示例 |
|------|------|------|
| `.pre <时间> @用户1 @用户2 [描述]` | 发起预定时间投票 | `.pre 202602230830 @张三 @李四 开团` |

**时间格式:**
- `YYYYMMDDHHMM` - 完整格式，如 `202602230830` 表示 2026年2月23日 8:30
- `MMDDHHMM` - 省略年份，默认当前年，如 `02230830`

**功能说明:**
- 只有被 @ 的用户可以投票
- 每人只能投票一次（同意/拒绝）
- 投票后实时显示结果统计

### 游戏日志命令

| 命令 | 说明 | 示例 |
|------|------|------|
| `.log start @用户1 @用户2` | 开始记录日志，记录提及用户、BOT和发起人的消息 | `.log start @张三 @李四` |
| `.log save` | 暂停记录 | `.log save` |
| `.log load` | 继续记录 | `.log load` |
| `.log end` | 结束记录 | `.log end` |
| `.log list` | 查看日志列表 | `.log list` |
| `.log o <名称>` | 导出JSON文件 | `.log o 20251218_162308_xxx` |
| `.log a <名称>` | 分析统计骰点数据 | `.log a 20251218_162308_xxx` |

**功能说明:**
- 自动记录发起者、被 @ 用户和 Bot 的所有发言
- 日志名称自动生成：`时间戳_频道ID`
- 分析功能统计每个用户的骰点成功/失败/大成功/大失败次数
- 日志保存14天后自动清理

### 管理员命令

| 命令 | 说明 | 示例 |
|------|------|------|
| `.admin bind` | 绑定为机器人管理员（仅首次有效） | `.admin bind` |
| `.admin friend list` | 查看好友申请列表 | `.admin friend list` |
| `.admin friend accept <申请ID>` | 同意好友申请 | `.admin friend accept 12345` |
| `.admin friend reject <申请ID>` | 拒绝好友申请 | `.admin friend reject 12345` |

**说明:** 管理员只能绑定一次，后续绑定请求会被拒绝。好友管理命令仅管理员可用。

---

## 🚀 快速开始

### 环境

- Python 3.10
- MySQL 8.4

其他版本没有试过，这是我个人使用的版本，如果有问题请提 Issue

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 创建数据库

```sql
CREATE DATABASE trpg_dicebot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 3. 配置环境变量

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

# LLM 服务配置 (可选，用于AI生成背景故事)
LLM_SERVICE=False
LLM_API_URL=https://api.openai.com/v1
LLM_API_TOKEN=your-api-token
LLM_MODEL=gpt-3.5-turbo
```

### 4. 运行

```bash
python -m src.main
```

---

## 🐳 Docker 部署

### 使用 Docker Compose (推荐)

```bash
# 配置环境变量
cp .env.example .env
# 编辑 .env 填写配置

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f bot
```

### 单独构建镜像

```bash
docker build -t coc-dice-bot .

docker run -d \
  --name coc-dice-bot \
  -p 8080:8080 \
  -e KOOK_TOKEN=your_token \
  -e DB_HOST=your_mysql_host \
  -e DB_PASSWORD=your_password \
  -e WEB_BASE_URL=http://your-ip:8080 \
  coc-dice-bot
```

---

## 🏗️ 项目架构

```
src/
├── main.py                    # 应用入口
├── config.py                  # 配置管理 (Pydantic Settings)
│
├── bot/                       # Bot 核心模块
│   ├── client.py              # KOOK WebSocket 客户端
│   ├── handler.py             # 消息处理器
│   ├── check_manager.py       # 检定管理器
│   └── commands/              # 命令系统
│       ├── base.py            # 命令基类 (BaseCommand)
│       ├── registry.py        # 命令注册器
│       └── handlers/          # 具体命令实现
│
├── cards/                     # 卡片消息系统
│   ├── components.py          # 基础组件 (CardComponents)
│   ├── builder.py             # 卡片构建器 (CardBuilder)
│   └── templates/             # 卡片模板
│
├── character/                 # 角色系统
│   ├── models.py              # 角色数据模型
│   ├── manager.py             # 角色管理器 (带缓存)
│   ├── importer.py            # 角色导入器
│   └── npc.py                 # NPC 管理
│
├── dice/                      # 骰点系统
│   ├── parser.py              # 表达式解析器
│   ├── roller.py              # 骰点执行器
│   ├── rules.py               # COC 规则引擎
│   └── skill_alias.py         # 技能别名映射
│
├── storage/                   # 数据存储层
│   ├── database.py            # 数据库连接管理
│   └── repositories/          # 数据仓库
│       └── base.py            # 基础仓库类 (CRUD)
│
├── services/                  # 业务服务
│   ├── token.py               # Token 服务 (链接生成/验证)
│   └── llm.py                 # LLM 服务 (AI生成背景故事)
│
├── logging/                   # 日志系统
│   ├── config.py              # 日志配置
│   └── handlers.py            # 自定义处理器
│
├── data/                      # 静态数据
│   ├── skills.py              # 技能定义
│   ├── madness.py             # 疯狂症状表
│   └── npc_status.py          # NPC 状态描述
│
└── web/                       # Web 服务
    ├── app.py                 # FastAPI 应用工厂
    ├── server.py              # 服务器启动
    ├── middleware.py          # 中间件
    ├── dependencies.py        # 依赖注入
    ├── routers/               # API 路由
    │   ├── character.py       # 角色 API
    │   ├── review.py          # 审核 API
    │   ├── grow.py            # 成长 API
    │   ├── health.py          # 健康检查
    │   └── pages.py           # 页面路由
    ├── templates/             # Jinja2 模板
    └── static/                # 静态资源
```

---

## 📖 COC 规则说明

### COC7 规则 (默认)

| 判定 | 条件 |
|------|------|
| 大成功 | 1-5 (可配置) |
| 极难成功 | ≤ 技能值/5 |
| 困难成功 | ≤ 技能值/2 |
| 普通成功 | ≤ 技能值 |
| 大失败 | 技能值<50: 96-100 / 技能值≥50: 仅100 |

### COC6 规则

| 判定 | 条件 |
|------|------|
| 大成功 | 1-5 (可配置) |
| 成功 | ≤ 技能值 |
| 失败 | > 技能值 |
| 大失败 | 96-100 (可配置) |

---

## 📝 角色卡 JSON 格式

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

---

## 🔧 技术栈

| 组件 | 技术 |
|------|------|
| 语言 | Python 3.10 |
| 异步框架 | asyncio + aiohttp |
| Web 框架 | FastAPI + Jinja2 |
| 数据库 | MySQL (aiomysql) |
| 配置管理 | Pydantic Settings |
| 日志 | Loguru |

---
