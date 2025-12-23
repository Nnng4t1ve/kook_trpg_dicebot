"""推送置顶命令"""
import json
from typing import Dict, Tuple
from loguru import logger
from .base import BaseCommand, CommandResult
from .registry import command


# 存储等待推送的用户状态: {(user_id, channel_id): True}
_pending_push: Dict[Tuple[str, str], bool] = {}


def is_pending_push(user_id: str, channel_id: str) -> bool:
    """检查用户是否在等待推送"""
    return _pending_push.get((user_id, channel_id), False)


def set_pending_push(user_id: str, channel_id: str, pending: bool = True):
    """设置用户推送等待状态"""
    if pending:
        _pending_push[(user_id, channel_id)] = True
    else:
        _pending_push.pop((user_id, channel_id), None)


def clear_pending_push(user_id: str, channel_id: str):
    """清除用户推送等待状态"""
    _pending_push.pop((user_id, channel_id), None)


@command("push")
class PushCommand(BaseCommand):
    """推送置顶命令"""
    
    description = "将下一条消息发布为卡片并置顶"
    usage = ".push"
    
    async def execute(self, args: str) -> CommandResult:
        """
        推送置顶命令
        用户发送 .push 后，记录状态，等待下一条消息
        """
        if self.ctx.channel_type != "GROUP":
            return CommandResult.text("此命令只能在频道中使用")
        
        # 设置等待状态
        set_pending_push(self.ctx.user_id, self.ctx.channel_id)
        logger.info(f"PUSH_PENDING | user={self.ctx.user_id} | channel={self.ctx.channel_id}")
        
        return CommandResult.text("📌 请发送要置顶的内容，我会将其发布为卡片并置顶")


def unescape_kmarkdown(text: str) -> str:
    """还原 KOOK 转义的 KMarkdown 特殊字符"""
    import re
    
    # KOOK 会把 KMarkdown 特殊字符转义，需要还原
    # 常见转义: \* \_ \` \~ \> \[ \] \( \) \\ 等
    result = text
    result = result.replace('\\*', '*')
    result = result.replace('\\_', '_')
    result = result.replace('\\`', '`')
    result = result.replace('\\~', '~')
    result = result.replace('\\>', '>')
    result = result.replace('\\[', '[')
    result = result.replace('\\]', ']')
    result = result.replace('\\(', '(')
    result = result.replace('\\)', ')')
    result = result.replace('\\-', '-')
    result = result.replace('\\\\', '\\')  # 最后处理反斜杠
    
    # 修复引用语法：行首的 > 后面需要空格
    # 匹配行首的 > 后面紧跟非空格字符的情况
    result = re.sub(r'^>', '> ', result, flags=re.MULTILINE)
    # 去掉多余的空格（如果原本就有空格会变成两个）
    result = re.sub(r'^> +', '> ', result, flags=re.MULTILINE)
    
    return result


def build_push_card(content: str, user_name: str) -> str:
    """构建推送卡片"""
    # 还原 KOOK 转义的特殊字符
    processed_content = unescape_kmarkdown(content)
    # 处理多行文本，确保换行符正确
    processed_content = processed_content.replace('\r\n', '\n').replace('\r', '\n')
    
    # 提取第一行作为标题，剩余内容作为正文
    lines = processed_content.split('\n', 1)
    title = f"📌 {lines[0].strip()}"
    # 保留正文的换行格式，只去掉首尾空白行
    body_content = lines[1].strip('\n') if len(lines) > 1 else ""
    
    modules = [
        {
            "type": "header",
            "text": {
                "type": "plain-text",
                "content": title
            }
        },
        {
            "type": "divider"
        }
    ]
    
    # 只有当有正文内容时才添加正文模块
    if body_content:
        modules.append({
            "type": "section",
            "text": {
                "type": "kmarkdown",
                "content": body_content
            }
        })
    
    modules.append({
        "type": "context",
        "elements": [
            {
                "type": "kmarkdown",
                "content": f"发布者: {user_name}"
            }
        ]
    })
    
    card = {
        "type": "card",
        "theme": "info",
        "size": "lg",
        "modules": modules
    }
    result = json.dumps([card], ensure_ascii=False)
    logger.debug(f"PUSH_CARD | json={result}")
    return result
