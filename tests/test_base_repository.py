"""数据仓库基础操作单元测试"""
import pytest
import json
from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar

T = TypeVar("T")


class BaseRepository(ABC, Generic[T]):
    """基础仓库类 - 用于测试的简化版本"""
    
    table_name: str = ""
    model_class: Type[T] = None
    
    def __init__(self, pool):
        self._pool = pool
    
    @abstractmethod
    def _row_to_model(self, row: tuple, columns: List[str]) -> T:
        pass
    
    @abstractmethod
    def _model_to_row(self, entity: T) -> Dict[str, Any]:
        pass
    
    def _build_where_clause(self, conditions: Dict[str, Any]) -> tuple:
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
        if isinstance(data, str):
            return data
        return json.dumps(data, ensure_ascii=False)
    
    def _deserialize_json(self, data: Any) -> Any:
        if isinstance(data, str):
            return json.loads(data)
        return data


class ConcreteRepository(BaseRepository[dict]):
    """用于测试的具体仓库实现"""
    table_name = "test_table"
    
    def _row_to_model(self, row, columns):
        return dict(zip(columns, row))
    
    def _model_to_row(self, entity):
        return entity


class TestBaseRepositoryUtils:
    """测试基础仓库工具方法"""

    def test_build_where_clause_single(self):
        """测试构建单条件 WHERE 子句"""
        repo = ConcreteRepository(None)
        clause, params = repo._build_where_clause({"user_id": "123"})
        
        assert clause == "user_id = %s"
        assert params == ("123",)

    def test_build_where_clause_multiple(self):
        """测试构建多条件 WHERE 子句"""
        repo = ConcreteRepository(None)
        clause, params = repo._build_where_clause({
            "user_id": "123",
            "name": "test"
        })
        
        assert "user_id = %s" in clause
        assert "name = %s" in clause
        assert "AND" in clause
        assert len(params) == 2

    def test_build_where_clause_null(self):
        """测试构建 NULL 条件"""
        repo = ConcreteRepository(None)
        clause, params = repo._build_where_clause({"deleted_at": None})
        
        assert clause == "deleted_at IS NULL"
        assert params == ()

    def test_build_where_clause_in_list(self):
        """测试构建 IN 条件"""
        repo = ConcreteRepository(None)
        clause, params = repo._build_where_clause({"status": ["active", "pending"]})
        
        assert "status IN (%s, %s)" in clause
        assert params == ("active", "pending")

    def test_serialize_json_dict(self):
        """测试序列化字典为 JSON"""
        repo = ConcreteRepository(None)
        data = {"key": "value", "num": 123}
        result = repo._serialize_json(data)
        
        assert isinstance(result, str)
        assert json.loads(result) == data

    def test_serialize_json_string(self):
        """测试序列化已是字符串的数据"""
        repo = ConcreteRepository(None)
        data = '{"already": "json"}'
        result = repo._serialize_json(data)
        
        assert result == data

    def test_deserialize_json_string(self):
        """测试反序列化 JSON 字符串"""
        repo = ConcreteRepository(None)
        data = '{"key": "value"}'
        result = repo._deserialize_json(data)
        
        assert result == {"key": "value"}

    def test_deserialize_json_already_parsed(self):
        """测试反序列化已解析的数据"""
        repo = ConcreteRepository(None)
        data = {"key": "value"}
        result = repo._deserialize_json(data)
        
        assert result == data

    def test_model_to_row(self):
        """测试模型转换为行"""
        repo = ConcreteRepository(None)
        entity = {"id": 1, "name": "test", "value": 100}
        result = repo._model_to_row(entity)
        
        assert result == entity

    def test_row_to_model(self):
        """测试行转换为模型"""
        repo = ConcreteRepository(None)
        row = (1, "test", 100)
        columns = ["id", "name", "value"]
        result = repo._row_to_model(row, columns)
        
        assert result == {"id": 1, "name": "test", "value": 100}
