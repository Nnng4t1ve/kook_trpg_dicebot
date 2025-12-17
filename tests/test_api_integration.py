"""API 端点集成测试"""
import pytest
from unittest.mock import MagicMock, AsyncMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport


# 创建测试用的 FastAPI 应用
def create_test_app():
    """创建测试用的 FastAPI 应用"""
    app = FastAPI(title="Test App")
    
    # 模拟依赖
    app.state.db = MagicMock()
    app.state.db._pool = None  # 模拟无数据库连接
    app.state.char_manager = MagicMock()
    app.state.char_manager.get_cache_stats = MagicMock(return_value={"hits": 0, "misses": 0})
    app.state.bot_connected = False
    app.state.recent_errors = 0
    
    # 模拟 token service
    token_service = MagicMock()
    token_service.get_stats = MagicMock(return_value={"total": 5, "create": 3, "grow": 2})
    token_service.generate_create_token = MagicMock(return_value="test_token")
    token_service.validate = MagicMock(return_value="user123")
    app.state.token_service = token_service
    
    # 健康检查路由
    @app.get("/health")
    async def health_check():
        db_connected = app.state.db._pool is not None
        bot_connected = app.state.bot_connected
        token_stats = app.state.token_service.get_stats()
        
        if db_connected and bot_connected:
            status = "healthy"
        elif db_connected or bot_connected:
            status = "degraded"
        else:
            status = "unhealthy"
        
        return {
            "status": status,
            "uptime_seconds": 100.0,
            "bot_connected": bot_connected,
            "db_connected": db_connected,
            "active_tokens": token_stats.get("total", 0),
            "recent_errors": app.state.recent_errors,
        }
    
    @app.get("/api/skills")
    async def get_skills():
        return {"skills": {"combat": ["格斗", "射击"], "social": ["说服", "魅惑"]}}
    
    return app


class TestHealthEndpoint:
    """测试健康检查端点"""

    def test_health_check_unhealthy(self):
        """测试不健康状态"""
        app = create_test_app()
        client = TestClient(app)
        
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "unhealthy"
        assert data["bot_connected"] is False
        assert data["db_connected"] is False
        assert data["active_tokens"] == 5

    def test_health_check_degraded(self):
        """测试降级状态"""
        app = create_test_app()
        app.state.bot_connected = True
        client = TestClient(app)
        
        response = client.get("/health")
        data = response.json()
        
        assert data["status"] == "degraded"
        assert data["bot_connected"] is True

    def test_health_response_structure(self):
        """测试健康检查响应结构"""
        app = create_test_app()
        client = TestClient(app)
        
        response = client.get("/health")
        data = response.json()
        
        # 验证响应包含所有必需字段
        assert "status" in data
        assert "uptime_seconds" in data
        assert "bot_connected" in data
        assert "db_connected" in data
        assert "active_tokens" in data
        assert "recent_errors" in data


class TestSkillsEndpoint:
    """测试技能列表端点"""

    def test_get_skills(self):
        """测试获取技能列表"""
        app = create_test_app()
        client = TestClient(app)
        
        response = client.get("/api/skills")
        assert response.status_code == 200
        data = response.json()
        
        assert "skills" in data
        assert "combat" in data["skills"]
        assert "social" in data["skills"]


class TestAPIErrorHandling:
    """测试 API 错误处理"""

    def test_not_found(self):
        """测试 404 错误"""
        app = create_test_app()
        client = TestClient(app)
        
        response = client.get("/nonexistent")
        assert response.status_code == 404

    def test_method_not_allowed(self):
        """测试 405 错误"""
        app = create_test_app()
        client = TestClient(app)
        
        response = client.post("/health")
        assert response.status_code == 405
