"""基础仓库类 - 提供通用 CRUD 操作"""
import json
from abc import ABC, abstractmethod
from dataclasses import asdict, is_dataclass
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar

import aiomysql

T = TypeVar("T")


class BaseRepository(ABC, Generic[T]):
    """
    基础仓库类 - 封装通用数据库操作
    
    子类需要实现:
    - table_name: 表名
    - model_class: 模型类
    - _row_to_model: 将数据库行转换为模型
    - _model_to_row: 将模型转换为数据库行
    """
    
    table_name: str = ""
    model_class: Type[T] = None
    
    def __init__(self, pool: aiomysql.Pool):
        self._pool = pool
    
    @abstractmethod
    def _row_to_model(self, row: tuple, columns: List[str]) -> T:
        """将数据库行转换为模型对象"""
        pass
    
    @abstractmethod
    def _model_to_row(self, entity: T) -> Dict[str, Any]:
        """将模型对象转换为数据库行字典"""
        pass
    
    async def find_one(self, **conditions) -> Optional[T]:
        """
        查询单条记录
        
        Args:
            **conditions: 查询条件，如 user_id="123", name="test"
        
        Returns:
            模型对象或 None
        """
        if not conditions:
            return None
        
        where_clause, params = self._build_where_clause(conditions)
        sql = f"SELECT * FROM {self.table_name} WHERE {where_clause} LIMIT 1"
        
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, params)
                row = await cur.fetchone()
                if row:
                    columns = [desc[0] for desc in cur.description]
                    return self._row_to_model(row, columns)
        return None
    
    async def find_many(
        self,
        order_by: str = None,
        limit: int = None,
        offset: int = None,
        **conditions
    ) -> List[T]:
        """
        查询多条记录
        
        Args:
            order_by: 排序字段，如 "created_at DESC"
            limit: 限制返回数量
            offset: 偏移量
            **conditions: 查询条件
        
        Returns:
            模型对象列表
        """
        if conditions:
            where_clause, params = self._build_where_clause(conditions)
            sql = f"SELECT * FROM {self.table_name} WHERE {where_clause}"
        else:
            sql = f"SELECT * FROM {self.table_name}"
            params = ()
        
        if order_by:
            sql += f" ORDER BY {order_by}"
        if limit:
            sql += f" LIMIT {limit}"
        if offset:
            sql += f" OFFSET {offset}"
        
        results = []
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, params)
                rows = await cur.fetchall()
                if rows:
                    columns = [desc[0] for desc in cur.description]
                    for row in rows:
                        results.append(self._row_to_model(row, columns))
        return results

    async def insert(self, entity: T) -> int:
        """
        插入记录
        
        Args:
            entity: 模型对象
        
        Returns:
            插入的行 ID
        """
        data = self._model_to_row(entity)
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["%s"] * len(data))
        sql = f"INSERT INTO {self.table_name} ({columns}) VALUES ({placeholders})"
        
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, tuple(data.values()))
                return cur.lastrowid
    
    async def update(self, entity: T, **conditions) -> int:
        """
        更新记录
        
        Args:
            entity: 模型对象
            **conditions: 更新条件
        
        Returns:
            受影响的行数
        """
        if not conditions:
            raise ValueError("Update requires at least one condition")
        
        data = self._model_to_row(entity)
        set_clause = ", ".join([f"{k} = %s" for k in data.keys()])
        where_clause, where_params = self._build_where_clause(conditions)
        
        sql = f"UPDATE {self.table_name} SET {set_clause} WHERE {where_clause}"
        params = tuple(data.values()) + where_params
        
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, params)
                return cur.rowcount
    
    async def upsert(self, entity: T, unique_keys: List[str]) -> int:
        """
        插入或更新记录 (ON DUPLICATE KEY UPDATE)
        
        Args:
            entity: 模型对象
            unique_keys: 唯一键字段列表，用于判断是否存在
        
        Returns:
            受影响的行数
        """
        data = self._model_to_row(entity)
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["%s"] * len(data))
        
        # 构建更新部分，排除唯一键
        update_fields = [k for k in data.keys() if k not in unique_keys]
        update_clause = ", ".join([f"{k} = VALUES({k})" for k in update_fields])
        
        sql = f"""
            INSERT INTO {self.table_name} ({columns}) 
            VALUES ({placeholders})
            ON DUPLICATE KEY UPDATE {update_clause}
        """
        
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, tuple(data.values()))
                return cur.rowcount
    
    async def delete(self, **conditions) -> int:
        """
        删除记录
        
        Args:
            **conditions: 删除条件
        
        Returns:
            删除的行数
        """
        if not conditions:
            raise ValueError("Delete requires at least one condition")
        
        where_clause, params = self._build_where_clause(conditions)
        sql = f"DELETE FROM {self.table_name} WHERE {where_clause}"
        
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, params)
                return cur.rowcount
    
    async def execute(self, sql: str, params: tuple = None) -> Any:
        """
        执行原始 SQL
        
        Args:
            sql: SQL 语句
            params: 参数元组
        
        Returns:
            查询结果或受影响行数
        """
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, params or ())
                if sql.strip().upper().startswith("SELECT"):
                    return await cur.fetchall()
                return cur.rowcount
    
    async def count(self, **conditions) -> int:
        """
        统计记录数
        
        Args:
            **conditions: 查询条件
        
        Returns:
            记录数量
        """
        if conditions:
            where_clause, params = self._build_where_clause(conditions)
            sql = f"SELECT COUNT(*) FROM {self.table_name} WHERE {where_clause}"
        else:
            sql = f"SELECT COUNT(*) FROM {self.table_name}"
            params = ()
        
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, params)
                row = await cur.fetchone()
                return row[0] if row else 0
    
    async def exists(self, **conditions) -> bool:
        """
        检查记录是否存在
        
        Args:
            **conditions: 查询条件
        
        Returns:
            是否存在
        """
        return await self.count(**conditions) > 0
    
    def _build_where_clause(self, conditions: Dict[str, Any]) -> tuple:
        """
        构建 WHERE 子句
        
        Args:
            conditions: 条件字典
        
        Returns:
            (where_clause, params) 元组
        """
        clauses = []
        params = []
        
        for key, value in conditions.items():
            if value is None:
                clauses.append(f"{key} IS NULL")
            elif isinstance(value, (list, tuple)):
                placeholders = ", ".join(["%s"] * len(value))
                clauses.append(f"{key} IN ({placeholders})")
                params.extend(value)
            else:
                clauses.append(f"{key} = %s")
                params.append(value)
        
        return " AND ".join(clauses), tuple(params)
    
    def _serialize_json(self, data: Any) -> str:
        """序列化为 JSON 字符串"""
        if isinstance(data, str):
            return data
        return json.dumps(data, ensure_ascii=False)
    
    def _deserialize_json(self, data: Any) -> Any:
        """反序列化 JSON 字符串"""
        if isinstance(data, str):
            return json.loads(data)
        return data
