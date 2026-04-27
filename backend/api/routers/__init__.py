# backend/api/routers/__init__.py
"""
API 路由子模块聚合
各子模块定义了自己的 APIRouter 实例，在此统一导出以便在上级 __init__.py 中注册。
"""
from backend.api.routers import collections, documents, query

# 导出各个路由模块（可选，便于直接引用）
__all__ = ["collections", "documents", "query"]