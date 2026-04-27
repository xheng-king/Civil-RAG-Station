# backend/api/dependencies.py
"""
依赖注入模块：提供全局单例实例，避免重复初始化。
所有依赖函数通过 FastAPI 的 Depends() 机制注入到路由处理器中。
"""
from backend.core.rag_engine import RAGEngine
from backend.core.indexer import QwenIndexer
from backend.core.database_manager import DatabaseManager

# 全局单例变量（模块级别，首次导入时创建）
_rag_engine: RAGEngine = None
_indexer: QwenIndexer = None
_db_manager: DatabaseManager = None


def get_rag_engine() -> RAGEngine:
    """
    获取 RAGEngine 单例实例
    用于问答路由
    """
    global _rag_engine
    if _rag_engine is None:
        # 初始化时不指定集合，后续通过 set_collection 动态切换
        _rag_engine = RAGEngine(collection_name=None)
    return _rag_engine


def get_indexer() -> QwenIndexer:
    """
    获取 QwenIndexer 单例实例
    用于文档上传和索引路由
    """
    global _indexer
    if _indexer is None:
        _indexer = QwenIndexer()
    return _indexer


def get_db_manager() -> DatabaseManager:
    """
    获取 DatabaseManager 单例实例
    用于集合管理路由（列出、创建、清空、删除集合）
    """
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager