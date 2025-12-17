"""记事本仓库"""
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import aiomysql

from .base import BaseRepository


@dataclass
class Notebook:
    """记事本模型"""
    name: str
    created_by: str
    created_at: datetime = None
    id: int = None


@dataclass
class NotebookEntry:
    """记事本条目模型"""
    notebook_id: int
    content: str
    created_by: str
    created_at: datetime = None
    id: int = None


class NotebookRepository(BaseRepository[Notebook]):
    """记事本仓库"""
    
    table_name = "notebooks"
    model_class = Notebook
    
    def _row_to_model(self, row: tuple, columns: List[str]) -> Notebook:
        data = dict(zip(columns, row))
        return Notebook(
            id=data.get("id"),
            name=data.get("name"),
            created_by=data.get("created_by"),
            created_at=data.get("created_at"),
        )
    
    def _model_to_row(self, entity: Notebook) -> Dict[str, Any]:
        return {
            "name": entity.name,
            "created_by": entity.created_by,
        }
    
    async def find_by_name(self, name: str) -> Optional[Notebook]:
        """根据名称查找记事本"""
        return await self.find_one(name=name)
    
    async def create(self, name: str, created_by: str) -> Notebook:
        """创建记事本"""
        notebook = Notebook(name=name, created_by=created_by)
        notebook_id = await self.insert(notebook)
        notebook.id = notebook_id
        return notebook


class NotebookEntryRepository(BaseRepository[NotebookEntry]):
    """记事本条目仓库"""
    
    table_name = "notebook_entries"
    model_class = NotebookEntry
    
    def _row_to_model(self, row: tuple, columns: List[str]) -> NotebookEntry:
        data = dict(zip(columns, row))
        return NotebookEntry(
            id=data.get("id"),
            notebook_id=data.get("notebook_id"),
            content=data.get("content"),
            created_by=data.get("created_by"),
            created_at=data.get("created_at"),
        )
    
    def _model_to_row(self, entity: NotebookEntry) -> Dict[str, Any]:
        return {
            "notebook_id": entity.notebook_id,
            "content": entity.content,
            "created_by": entity.created_by,
        }
    
    async def add_entry(self, notebook_id: int, content: str, created_by: str) -> NotebookEntry:
        """添加条目"""
        entry = NotebookEntry(
            notebook_id=notebook_id,
            content=content,
            created_by=created_by,
        )
        entry_id = await self.insert(entry)
        entry.id = entry_id
        return entry
    
    async def get_entries_page(
        self, notebook_id: int, page: int = 1, page_size: int = 10
    ) -> tuple[List[NotebookEntry], int]:
        """获取分页条目列表，返回 (条目列表, 总数)"""
        total = await self.count(notebook_id=notebook_id)
        offset = (page - 1) * page_size
        entries = await self.find_many(
            notebook_id=notebook_id,
            order_by="id ASC",
            limit=page_size,
            offset=offset,
        )
        return entries, total
    
    async def get_entry_by_index(self, notebook_id: int, index: int) -> Optional[NotebookEntry]:
        """根据序号获取条目（从1开始）"""
        entries = await self.find_many(
            notebook_id=notebook_id,
            order_by="id ASC",
            limit=1,
            offset=index - 1,
        )
        return entries[0] if entries else None
