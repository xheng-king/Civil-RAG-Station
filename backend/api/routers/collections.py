# backend/api/routers/collections.py
"""
集合管理路由
提供对 ChromaDB 集合的增删查改操作
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from backend.api.dependencies import get_db_manager
from backend.api.schemas import CollectionInfo, CreateCollectionRequest, MessageResponse, ClearCollectionResponse
from backend.core.database_manager import DatabaseManager

router = APIRouter()


@router.get("/", response_model=List[CollectionInfo])
async def list_collections(db: DatabaseManager = Depends(get_db_manager)):
    """
    列出所有集合及其文档数量
    """
    collections_list = db.list_collections()
    result = []
    for name in collections_list:
        info = db.get_collection_info(name)
        if info:
            result.append(CollectionInfo(name=name, document_count=info.get("count", 0)))
        else:
            result.append(CollectionInfo(name=name, document_count=0))
    return result


@router.post("/", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def create_collection(
    request: CreateCollectionRequest,
    db: DatabaseManager = Depends(get_db_manager)
):
    """
    创建一个新的空集合
    """
    success = db.create_empty_collection(request.name)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建集合 '{request.name}' 失败"
        )
    return MessageResponse(
        message=f"集合 '{request.name}' 已创建或已存在",
        success=True
    )


@router.get("/{collection_name}", response_model=CollectionInfo)
async def get_collection(
    collection_name: str,
    db: DatabaseManager = Depends(get_db_manager)
):
    """
    获取指定集合的详细信息
    """
    info = db.get_collection_info(collection_name)
    if info is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"集合 '{collection_name}' 不存在"
        )
    return CollectionInfo(name=info["name"], document_count=info["count"])


@router.post("/{collection_name}/clear", response_model=ClearCollectionResponse)
async def clear_collection(
    collection_name: str,
    db: DatabaseManager = Depends(get_db_manager)
):
    """
    清空指定集合中的所有文档（但保留集合本身）
    """
    # 先检查集合是否存在
    info = db.get_collection_info(collection_name)
    if info is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"集合 '{collection_name}' 不存在"
        )
    
    old_count = info["count"]
    success = db.clear_collection(collection_name)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"清空集合 '{collection_name}' 失败"
        )
    
    return ClearCollectionResponse(
        collection_name=collection_name,
        deleted_count=old_count,
        success=True
    )


@router.delete("/{collection_name}", response_model=MessageResponse)
async def delete_collection(
    collection_name: str,
    db: DatabaseManager = Depends(get_db_manager)
):
    """
    完全删除集合（包括所有文档和元数据）
    """
    # 先检查集合是否存在
    info = db.get_collection_info(collection_name)
    if info is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"集合 '{collection_name}' 不存在"
        )
    
    success = db.delete_collection(collection_name)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除集合 '{collection_name}' 失败"
        )
    
    return MessageResponse(
        message=f"集合 '{collection_name}' 已删除",
        success=True
    )