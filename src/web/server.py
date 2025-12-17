"""Web 服务器 - 兼容层

此模块保留用于向后兼容，实际实现已迁移到 app.py
"""
from .app import create_app

__all__ = ["create_app"]
