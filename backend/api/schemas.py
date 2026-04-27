# backend/api/schemas.py
"""
Pydantic 数据模型定义，用于 API 请求和响应的数据验证与序列化。
所有模型均用于 FastAPI 的自动文档生成（Swagger UI）和类型检查。
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ========== 通用响应结构 ==========
class MessageResponse(BaseModel):
    """通用消息响应"""
    message: str = Field(..., description="操作结果信息")
    success: bool = Field(..., description="操作是否成功")
    details: Optional[Dict[str, Any]] = Field(None, description="附加详情")


# ========== 集合管理相关 ==========
class CollectionInfo(BaseModel):
    """集合信息"""
    name: str = Field(..., description="集合名称")
    document_count: int = Field(..., description="文档片段数量")


class CreateCollectionRequest(BaseModel):
    """创建集合请求"""
    name: str = Field(..., description="集合名称", min_length=1, max_length=100)


class ClearCollectionResponse(BaseModel):
    """清空集合响应"""
    collection_name: str = Field(..., description="清空的集合名称")
    deleted_count: int = Field(..., description="删除的文档片段数")
    success: bool = Field(..., description="是否成功")


# ========== 文档上传与索引相关 ==========
class UploadDocumentRequest(BaseModel):
    """文档上传请求（用于 JSON body，但实际文件上传使用 multipart/form-data，此模型不直接使用，仅作文档说明）"""
    collection_name: str = Field(..., description="目标集合名称")
    min_chunk_size: Optional[int] = Field(512, description="最小分块大小（字符数）", ge=100, le=1000)
    max_chunk_size: Optional[int] = Field(2048, description="最大分块大小（字符数）", ge=500, le=4000)
    record_stats: Optional[bool] = Field(True, description="是否记录分块统计到 CSV")


class UploadResponse(BaseModel):
    """文档上传与索引响应"""
    success: bool = Field(..., description="索引是否成功")
    collection_name: str = Field(..., description="目标集合名称")
    filename: str = Field(..., description="原始文件名")
    total_chunks: int = Field(..., description="分块总数")
    avg_chunk_length: float = Field(..., description="平均每个块的长度（字符数）")
    error: Optional[str] = Field(None, description="错误信息（若成功则为 None）")


# ========== 问答相关 ==========
class QueryRequest(BaseModel):
    """问答请求"""
    question: str = Field(..., description="用户问题", min_length=1, max_length=2000)
    collection_name: str = Field(..., description="使用的集合名称", min_length=1)
    # 可选：动态覆盖检索参数
    initial_k: Optional[int] = Field(None, description="初始召回文档数（覆盖默认值）", ge=1, le=100)
    final_top_k: Optional[int] = Field(None, description="重排序后最终使用的文档数", ge=1, le=20)
    adaptive_enabled: Optional[bool] = Field(False, description="是否开启自适应检索")


class QueryResponse(BaseModel):
    """问答响应"""
    question: str = Field(..., description="原始问题")
    answer_markdown: str = Field(..., description="回答（Markdown 格式）")
    answer_plain: str = Field(..., description="回答纯文本版本（不含 Markdown 标记）")
    contexts_count: int = Field(..., description="参考的上下文片段数量")
    processing_time_ms: float = Field(..., description="处理耗时（毫秒）")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="其他元数据（如集合名、检索参数）")


# ========== 系统状态相关 ==========
class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str = Field(..., description="服务状态", example="healthy")
    version: str = Field(..., description="API 版本")
    collections_available: int = Field(..., description="可用的集合总数")


# ========== 错误响应 ==========
class ErrorResponse(BaseModel):
    """标准错误响应"""
    error: str = Field(..., description="错误类型")
    message: str = Field(..., description="详细错误信息")
    details: Optional[Dict[str, Any]] = Field(None, description="附加错误详情")