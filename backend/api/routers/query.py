# backend/api/routers/query.py
"""
问答路由
处理用户查询请求，调用 RAG 引擎生成答案并返回 Markdown 格式的结果
"""
import time
from fastapi import APIRouter, Depends, HTTPException, status

from backend.api.dependencies import get_rag_engine
from backend.api.schemas import QueryRequest, QueryResponse
from backend.core.rag_engine import RAGEngine

router = APIRouter()


@router.post("/", response_model=QueryResponse)
async def query_endpoint(
    request: QueryRequest,
    rag: RAGEngine = Depends(get_rag_engine)
):
    """
    提交问题并获取基于 RAG 的回答

    - **question**: 用户问题（必填）
    - **collection_name**: 要查询的向量集合名称（必填）
    - **initial_k**: （可选）覆盖默认的初始召回文档数
    - **final_top_k**: （可选）覆盖默认的重排序后保留文档数
    - **adaptive_enabled**: （可选）是否启用自适应检索
    返回的回答包含 Markdown 格式和纯文本版本，以及处理耗时。
    """
    start_time = time.time()

    # 1. 切换到目标集合
    success = rag.set_collection(request.collection_name)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"集合 '{request.collection_name}' 不存在或无法访问"
        )

    # 2. 可选：覆盖检索参数
    if request.initial_k is not None or request.final_top_k is not None:
        rag.set_retrieval_params(
            initial_k=request.initial_k,
            final_top_k=request.final_top_k
        )

    # 3. 执行问答
    try:
        answer, metadata = rag.query(request.question, adaptive_enabled=request.adaptive_enabled)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成回答时出错: {str(e)}"
        )

    # 4. 计算耗时
    processing_time_ms = (time.time() - start_time) * 1000

    # 5. 提取纯文本（去除 Markdown 标记，简单实现）
    answer_plain = _strip_markdown(answer)

    # 6. 构造响应
    return QueryResponse(
        question=request.question,
        answer_markdown=answer,
        answer_plain=answer_plain,
        contexts_count=metadata.get("num_contexts", 0),
        processing_time_ms=round(processing_time_ms, 2),
        metadata={
            "collection_name": request.collection_name,
            "initial_k": request.initial_k or rag.retriever.initial_retrieve_k,
            "final_top_k": request.final_top_k or rag.retriever.final_top_k,
            **metadata
        }
    )


def _strip_markdown(text: str) -> str:
    """
    简单去除 Markdown 标记，保留纯文本
    适用于显示或复制
    """
    import re
    # 去除标题标记 #
    text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
    # 去除加粗/斜体 **xxx** 或 *xxx*
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    # 去除引用块开头的 >
    text = re.sub(r'^>\s+', '', text, flags=re.MULTILINE)
    # 去除链接 [text](url) -> text
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
    # 去除代码块标记 ```...```
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    # 去除行内代码 `code`
    text = re.sub(r'`(.*?)`', r'\1', text)
    # 去除有序/无序列表标记
    text = re.sub(r'^[\*\-\+]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\d+\.\s+', '', text, flags=re.MULTILINE)
    return text.strip()