"""记事本命令"""
import json
from typing import Optional

from ...cards.builder import CardBuilder
from ...cards.components import CardComponents
from .base import BaseCommand, CommandContext, CommandResult
from .registry import command


# 用于存储用户当前选中的记事本
_user_active_notebook: dict[str, str] = {}


@command("note", aliases=["笔记", "记事"])
class NotebookCommand(BaseCommand):
    """记事本命令"""
    
    description = "记事本功能"
    usage = ".note c <名称> | .note s <名称> | .note i <内容> | .note list | .note w <序号>"
    
    async def execute(self, args: str) -> CommandResult:
        args = args.strip()
        if not args:
            return await self._show_current()
        
        parts = args.split(maxsplit=1)
        sub_cmd = parts[0].lower()
        sub_args = parts[1] if len(parts) > 1 else ""
        
        if sub_cmd == "c":
            return await self._create_notebook(sub_args)
        elif sub_cmd == "s":
            return await self._switch_notebook(sub_args)
        elif sub_cmd == "i":
            return await self._insert_entry(sub_args)
        elif sub_cmd == "list":
            return await self._list_entries(1)
        elif sub_cmd == "w":
            return await self._view_entry(sub_args)
        elif sub_cmd == "all":
            return await self._list_notebooks()
        elif sub_cmd == "help":
            return CommandResult.text(self._help_text())
        else:
            return CommandResult.text(self._help_text())
    
    def _help_text(self) -> str:
        return (
            "📒 **记事本命令**\n"
            "`.note` - 查看当前记事本\n"
            "`.note all` - 查看所有记事本\n"
            "`.note c <名称>` - 创建新记事本\n"
            "`.note s <名称>` - 切换记事本\n"
            "`.note i <内容>` - 记录内容\n"
            "`.note list` - 查看记录列表\n"
            "`.note w <序号>` - 查看具体内容"
        )
    
    async def _show_current(self) -> CommandResult:
        """显示当前所在的记事本"""
        notebook_name = _user_active_notebook.get(self.ctx.user_id)
        if not notebook_name:
            return CommandResult.text("📒 当前未选择记事本\n使用 `.note all` 查看所有记事本\n使用 `.note c <名称>` 创建新记事本")
        
        notebook = await self.ctx.db.notebooks.find_by_name(notebook_name)
        if not notebook:
            _user_active_notebook.pop(self.ctx.user_id, None)
            return CommandResult.text("📒 当前记事本已不存在，请重新选择")
        
        # 获取记录数
        _, total = await self.ctx.db.notebook_entries.get_entries_page(notebook.id, page=1, page_size=1)
        
        return CommandResult.text(f"📒 当前记事本: **{notebook_name}**\n共 {total} 条记录\n使用 `.note list` 查看记录列表")
    
    async def _list_notebooks(self) -> CommandResult:
        """列出所有记事本"""
        notebooks = await self.ctx.db.notebooks.find_many(order_by="created_at DESC")
        
        if not notebooks:
            return CommandResult.text("📒 暂无记事本\n使用 `.note c <名称>` 创建新记事本")
        
        current = _user_active_notebook.get(self.ctx.user_id)
        lines = ["📒 **所有记事本**", ""]
        for nb in notebooks:
            marker = "📌 " if nb.name == current else ""
            lines.append(f"{marker}**{nb.name}**")
        
        lines.append("")
        lines.append("使用 `.note s <名称>` 切换记事本")
        
        return CommandResult.text("\n".join(lines))
    
    async def _create_notebook(self, name: str) -> CommandResult:
        name = name.strip()
        if not name:
            return CommandResult.text("请指定记事本名称: `.note c <名称>`")
        
        existing = await self.ctx.db.notebooks.find_by_name(name)
        if existing:
            return CommandResult.text(f"记事本 **{name}** 已存在")
        
        notebook = await self.ctx.db.notebooks.create(name, self.ctx.user_id)
        _user_active_notebook[self.ctx.user_id] = name
        
        return CommandResult.text(f"📒 记事本 **{name}** 创建成功，已自动切换")
    
    async def _switch_notebook(self, name: str) -> CommandResult:
        name = name.strip()
        if not name:
            return CommandResult.text("请指定记事本名称: `.note s <名称>`")
        
        notebook = await self.ctx.db.notebooks.find_by_name(name)
        if not notebook:
            return CommandResult.text(f"记事本 **{name}** 不存在")
        
        _user_active_notebook[self.ctx.user_id] = name
        return CommandResult.text(f"📒 已切换到记事本 **{name}**")
    
    async def _insert_entry(self, content: str) -> CommandResult:
        content = content.strip()
        if not content:
            return CommandResult.text("请指定要记录的内容: `.note i <内容>`")
        
        notebook_name = _user_active_notebook.get(self.ctx.user_id)
        if not notebook_name:
            return CommandResult.text("请先创建或切换记事本: `.note c <名称>` 或 `.note s <名称>`")
        
        notebook = await self.ctx.db.notebooks.find_by_name(notebook_name)
        if not notebook:
            return CommandResult.text(f"记事本 **{notebook_name}** 不存在，请重新创建")
        
        entry = await self.ctx.db.notebook_entries.add_entry(
            notebook.id, content, self.ctx.user_id
        )
        
        return CommandResult.text(f"📝 已记录到 **{notebook_name}**")
    
    async def _list_entries(self, page: int) -> CommandResult:
        notebook_name = _user_active_notebook.get(self.ctx.user_id)
        if not notebook_name:
            return CommandResult.text("请先创建或切换记事本: `.note c <名称>` 或 `.note s <名称>`")
        
        notebook = await self.ctx.db.notebooks.find_by_name(notebook_name)
        if not notebook:
            return CommandResult.text(f"记事本 **{notebook_name}** 不存在")
        
        entries, total = await self.ctx.db.notebook_entries.get_entries_page(
            notebook.id, page=page, page_size=10
        )
        
        if total == 0:
            return CommandResult.text(f"📒 **{notebook_name}** 暂无记录")
        
        total_pages = (total + 9) // 10
        
        card = self._build_list_card(notebook_name, entries, page, total_pages, total)
        return CommandResult.card(card)
    
    async def _view_entry(self, index_str: str) -> CommandResult:
        index_str = index_str.strip()
        if not index_str or not index_str.isdigit():
            return CommandResult.text("请指定有效的序号: `.note w <序号>`")
        
        index = int(index_str)
        if index < 1:
            return CommandResult.text("序号必须大于 0")
        
        notebook_name = _user_active_notebook.get(self.ctx.user_id)
        if not notebook_name:
            return CommandResult.text("请先创建或切换记事本")
        
        notebook = await self.ctx.db.notebooks.find_by_name(notebook_name)
        if not notebook:
            return CommandResult.text(f"记事本 **{notebook_name}** 不存在")
        
        entry = await self.ctx.db.notebook_entries.get_entry_by_index(notebook.id, index)
        if not entry:
            return CommandResult.text(f"未找到第 {index} 条记录")
        
        card = self._build_entry_card(notebook_name, index, entry)
        return CommandResult.card(card)
    
    def _build_list_card(
        self, notebook_name: str, entries: list, page: int, total_pages: int, total: int
    ) -> str:
        builder = CardBuilder(theme="info")
        builder.header(f"📒 {notebook_name}")
        builder.divider()
        
        start_idx = (page - 1) * 10 + 1
        lines = []
        for i, entry in enumerate(entries):
            idx = start_idx + i
            content_preview = entry.content[:30] + "..." if len(entry.content) > 30 else entry.content
            lines.append(f"**{idx}.** {content_preview}")
        
        builder.section("\n".join(lines))
        builder.context(f"第 {page}/{total_pages} 页 · 共 {total} 条记录")
        
        # 分页按钮
        if total_pages > 1:
            prev_page = total_pages if page == 1 else page - 1
            next_page = 1 if page == total_pages else page + 1
            
            buttons = [
                CardComponents.button(
                    "⬅️ 上一页",
                    {"action": "notebook_page", "notebook": notebook_name, "page": prev_page},
                    theme="secondary"
                ),
                CardComponents.button(
                    "下一页 ➡️",
                    {"action": "notebook_page", "notebook": notebook_name, "page": next_page},
                    theme="secondary"
                ),
            ]
            builder.buttons(*buttons)
        
        return builder.build()
    
    def _build_entry_card(self, notebook_name: str, index: int, entry) -> str:
        builder = CardBuilder(theme="info")
        builder.header(f"📒 {notebook_name} - 第 {index} 条")
        builder.divider()
        builder.section(entry.content)
        builder.context(f"记录者: {entry.created_by} · {entry.created_at.strftime('%Y-%m-%d %H:%M')}")
        return builder.build()
