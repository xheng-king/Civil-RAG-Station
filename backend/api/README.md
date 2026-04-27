api/__init__.py: (模块级) 导出 api_router、get_rag_engine、get_indexer、get_db_manager、QueryRequest、QueryResponse、UploadResponse、CollectionInfo、MessageResponse。

api/dependencies.py:get_rag_engine() -> RAGEngine: 获取 RAGEngine 单例实例，首次调用时创建并返回。
api/dependencies.py:get_indexer() -> QwenIndexer: 获取 QwenIndexer 单例实例，用于文档索引。
api/dependencies.py:get_db_manager() -> DatabaseManager: 获取 DatabaseManager 单例实例，用于集合管理。

api/schemas.py:MessageResponse:__init__(self, message: str, success: bool, details: Optional[Dict[str, Any]] = None) -> None: 通用消息响应模型。
api/schemas.py:CollectionInfo:__init__(self, name: str, document_count: int) -> None: 集合信息模型。
api/schemas.py:CreateCollectionRequest:__init__(self, name: str) -> None: 创建集合请求模型。
api/schemas.py:ClearCollectionResponse:__init__(self, collection_name: str, deleted_count: int, success: bool) -> None: 清空集合响应模型。
api/schemas.py:UploadDocumentRequest:__init__(self, collection_name: str, min_chunk_size: Optional[int] = 512, max_chunk_size: Optional[int] = 2048, record_stats: Optional[bool] = True) -> None: 文档上传请求模型（说明用）。
api/schemas.py:UploadResponse:__init__(self, success: bool, collection_name: str, filename: str, total_chunks: int, avg_chunk_length: float, error: Optional[str] = None) -> None: 文档上传响应模型。
api/schemas.py:QueryRequest:__init__(self, question: str, collection_name: str, initial_k: Optional[int] = None, final_top_k: Optional[int] = None) -> None: 问答请求模型。
api/schemas.py:QueryResponse:__init__(self, question: str, answer_markdown: str, answer_plain: str, contexts_count: int, processing_time_ms: float, metadata: Dict[str, Any] = {}) -> None: 问答响应模型。
api/schemas.py:HealthResponse:__init__(self, status: str, version: str, collections_available: int) -> None: 健康检查响应模型。
api/schemas.py:ErrorResponse:__init__(self, error: str, message: str, details: Optional[Dict[str, Any]] = None) -> None: 错误响应模型。

api/routers/__init__.py: (模块级) 导出 collections、documents、query 子路由模块。

api/routers/collections.py:list_collections(db: DatabaseManager = Depends(get_db_manager)) -> List[CollectionInfo]: GET / 列出所有集合及其文档数。
api/routers/collections.py:create_collection(request: CreateCollectionRequest, db: DatabaseManager = Depends(get_db_manager)) -> MessageResponse: POST / 创建新的空集合。
api/routers/collections.py:get_collection(collection_name: str, db: DatabaseManager = Depends(get_db_manager)) -> CollectionInfo: GET /{collection_name} 获取指定集合详细信息。
api/routers/collections.py:clear_collection(collection_name: str, db: DatabaseManager = Depends(get_db_manager)) -> ClearCollectionResponse: POST /{collection_name}/clear 清空集合内所有文档。
api/routers/collections.py:delete_collection(collection_name: str, db: DatabaseManager = Depends(get_db_manager)) -> MessageResponse: DELETE /{collection_name} 彻底删除集合。

api/routers/documents.py:validate_file(filename: str) -> None: 验证文件扩展名是否合法，若不合法抛出 HTTPException。
api/routers/documents.py:upload_document(file: UploadFile = File(...), collection_name: str = Form(...), min_chunk_size: Optional[int] = Form(512), max_chunk_size: Optional[int] = Form(2048), record_stats: Optional[bool] = Form(True), indexer: QwenIndexer = Depends(get_indexer)) -> UploadResponse: POST /upload 上传并索引文档文件。

api/routers/query.py:query_endpoint(request: QueryRequest, rag: RAGEngine = Depends(get_rag_engine)) -> QueryResponse: POST / 提交问题，获取基于 RAG 的 Markdown 答案。
api/routers/query.py:_strip_markdown(text: str) -> str: 内部辅助函数，移除 Markdown 标记，返回纯文本。