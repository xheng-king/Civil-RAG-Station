# backend/api/routers/documents.py
"""
文档上传与索引路由
支持上传 .md / .txt 文件，自动分块、向量化并存入指定 ChromaDB 集合
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from typing import Optional
import os
import tempfile

from backend.api.dependencies import get_indexer
from backend.api.schemas import UploadResponse
from backend.core.indexer import QwenIndexer

router = APIRouter()

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {".md", ".txt", ".markdown"}
# 最大文件大小 (10 MB)
MAX_FILE_SIZE = 10 * 1024 * 1024


def validate_file(filename: str) -> None:
    """验证文件扩展名是否合法"""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的文件类型 '{ext}'，仅支持 {', '.join(ALLOWED_EXTENSIONS)}"
        )


@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(..., description="要上传的 .md 或 .txt 文件"),
    collection_name: str = Form(..., description="目标集合名称"),
    min_chunk_size: Optional[int] = Form(512, description="最小分块大小（字符数）", ge=100, le=1000),
    max_chunk_size: Optional[int] = Form(2048, description="最大分块大小（字符数）", ge=500, le=4000),
    record_stats: Optional[bool] = Form(True, description="是否记录分块统计到 CSV"),
    indexer: QwenIndexer = Depends(get_indexer)
):
    """
    上传并索引一个文档文件

    流程：
    1. 验证文件类型和大小
    2. 读取文件内容（文本）
    3. 调用 Indexer 分块、生成向量并存入 ChromaDB 集合
    4. 返回分块统计信息

    注意：本接口同步处理，大文件可能导致超时，建议配合后台任务或增加超时配置。
    """
    # 1. 验证文件扩展名
    validate_file(file.filename)

    # 2. 检查文件大小（先读取一部分？FastAPI 已缓存到内存，但尚未完整读取）
    # 注意：UploadFile 的 size 属性不一定可用，这里先读取内容再判断
    try:
        content = await file.read()
        file_size = len(content)
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"文件过大，最大允许 {MAX_FILE_SIZE // (1024*1024)} MB，当前 {file_size / (1024*1024):.2f} MB"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"读取文件失败: {str(e)}"
        )

    # 3. 解码为文本（假设 UTF-8）
    try:
        text_content = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="文件编码不是 UTF-8，请转换后重试"
        )

    # 4. 调用 Indexer 进行索引
    try:
        result = indexer.index_text_to_collection(
            text=text_content,
            filename=file.filename,
            collection_name=collection_name,
            min_chunk_size=min_chunk_size,
            max_chunk_size=max_chunk_size,
            record_stats=record_stats
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"索引过程中出错: {str(e)}"
        )

    if not result.get("success"):
        error_msg = result.get("error", "未知错误")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"索引失败: {error_msg}"
        )

    return UploadResponse(
        success=True,
        collection_name=collection_name,
        filename=file.filename,
        total_chunks=result["total_chunks"],
        avg_chunk_length=result["avg_chunk_length"]
    )