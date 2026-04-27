# backend/api/__init__.py
from fastapi import APIRouter
from backend.api.routers import collections, documents, query

# 创建主路由
api_router = APIRouter(prefix="/api")

# 注册子路由
api_router.include_router(collections.router, prefix="/collections", tags=["collections"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(query.router, prefix="/query", tags=["query"])

# 导出常用组件，方便外部导入
from backend.api.dependencies import get_rag_engine, get_indexer, get_db_manager
from backend.api.schemas import (
    QueryRequest,
    QueryResponse,
    UploadResponse,
    CollectionInfo,
    MessageResponse,
)

__all__ = [
    "api_router",
    "get_rag_engine",
    "get_indexer",
    "get_db_manager",
    "QueryRequest",
    "QueryResponse",
    "UploadResponse",
    "CollectionInfo",
    "MessageResponse",
]