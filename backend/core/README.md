settings.py: (配置变量) 包含 Embedding、Rerank、LLM 的 API 密钥、URL、模型名称；向量数据库路径；分块大小；检索参数；自适应检索开关及步长；查询日志路径等。

database_manager.py:DatabaseManager:__init__(self, persist_directory: str = None) -> None: 初始化 ChromaDB 客户端，持久化目录优先使用参数，否则从 settings 读取。
database_manager.py:DatabaseManager:list_collections(self) -> List[str]: 列出所有集合名称，并在控制台打印每个集合的文档数量，返回名称列表。
database_manager.py:DatabaseManager:get_collection_info(self, collection_name: str) -> Dict[str, Any]: 获取指定集合的名称和文档数量，失败时返回 None。
database_manager.py:DatabaseManager:clear_collection(self, collection_name: str) -> bool: 清空指定集合中的所有文档，成功返回 True，失败返回 False。
database_manager.py:DatabaseManager:create_empty_collection(self, collection_name: str) -> bool: 创建新的空集合（若已存在则直接返回），成功返回 True，失败返回 False。
database_manager.py:DatabaseManager:delete_collection(self, collection_name: str) -> bool: 完全删除指定集合，成功返回 True，失败返回 False。
database_manager.py:DatabaseManager:get_collection(self, collection_name: str): 获取 ChromaDB 原生集合对象，若不存在则返回 None。

indexer.py:QwenIndexer:__init__(self) -> None: 初始化 Embedding API 客户端（OpenAI 风格）、ChromaDB 客户端，并确保向量存储目录存在。
indexer.py:QwenIndexer:blocks(self, text: str) -> List[str]: 基于条款号正则表达式将文本切分为初步块，若无匹配则返回整个文本。
indexer.py:QwenIndexer:connect(self, str1: str, str2: str) -> str: 拼接两个字符串，处理空值，中间加换行符。
indexer.py:QwenIndexer:cut_string(self, s: str, start: int, end: int) -> str: 截取字符串指定区间。
indexer.py:QwenIndexer:structural_chunk(self, text: str, min_chunk_size: int = 512, max_chunk_size: int = 2048) -> List[str]: 执行结构化分块，合并短块、切割长块，使每块长度在指定范围内。
indexer.py:QwenIndexer:read_and_chunk_file(self, file_path: str, min_chunk_size: int = 512, max_chunk_size: int = 2048) -> List[str]: 读取文件内容并调用 structural_chunk 返回分块列表。
indexer.py:QwenIndexer:create_embeddings(self, texts: List[str]) -> List[List[float]]: 调用 Embedding API 为每个文本生成向量，返回向量列表。
indexer.py:QwenIndexer:index_text_to_collection(self, text: str, filename: str, collection_name: str, min_chunk_size: int = 512, max_chunk_size: int = 2048, record_stats: bool = True) -> Dict[str, Any]: 将文本内容分块、嵌入并存入指定集合，返回索引统计信息（成功标志、块数、平均长度等）。
indexer.py:QwenIndexer:index_single_file_to_collection(self, file_path: str, collection_name: str, min_chunk_size: int = 512, max_chunk_size: int = 2048, record_stats: bool = True) -> Dict[str, Any]: 从本地文件读取内容并索引到集合（内部调用 index_text_to_collection）。
indexer.py:QwenIndexer:_record_chunk_stats(self, filename: str, segments: List[str]) -> None: 将分块详细信息追加写入项目根目录的 chunk_details.csv。

retriever_generator.py:QwenRetrieverGenerator:__init__(self, collection_name: Optional[str] = None, log_file_path: Optional[str] = None) -> None: 初始化 Embedding、LLM、Rerank 客户端及 ChromaDB 连接，加载自适应检索配置，可选设置集合和日志路径。
retriever_generator.py:QwenRetrieverGenerator:set_collection(self, collection_name: str) -> bool: 设置当前查询的集合，成功返回 True，失败返回 False。
retriever_generator.py:QwenRetrieverGenerator:list_collections(self) -> List[str]: 返回所有集合名称列表。
retriever_generator.py:QwenRetrieverGenerator:get_collection_info(self, collection_name: str) -> Dict[str, Any]: 获取集合信息（名称和文档数）。
retriever_generator.py:QwenRetrieverGenerator:_log_interaction(self, user_input: str, response: str, round_num: int = 1, status: str = "Final") -> None: 将问答交互记录追加写入 Markdown 日志文件。
retriever_generator.py:QwenRetrieverGenerator:embed_query(self, query_text: str) -> List[float]: 调用 Embedding API 将查询文本转换为向量。
retriever_generator.py:QwenRetrieverGenerator:retrieve_documents(self, query_text: str, k: int = None) -> List[Dict[str, Any]]: 基于向量相似度从当前集合召回 Top-K 个文档片段。
retriever_generator.py:QwenRetrieverGenerator:_rerank_all_documents(self, query: str, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]: 调用重排序 API 对所有候选文档打分并排序，失败时降级为按初始距离排序。
retriever_generator.py:QwenRetrieverGenerator:rerank_documents(self, query: str, documents: List[Dict[str, Any]], top_n: int = None) -> List[Dict[str, Any]]: 重排序并返回前 top_n 个文档，同时添加 rerank_rank 字段。
retriever_generator.py:QwenRetrieverGenerator:generate_answer(self, query: str, contexts: List[Dict[str, Any]]) -> str: 基于上下文构建 Prompt，调用 LLM 生成最终回答。
retriever_generator.py:QwenRetrieverGenerator:_execute_single_round(self, user_input: str, initial_k: int, final_top_k: int) -> Tuple[str, List[Dict], List[Dict]]: 执行单轮“检索-重排序-生成”流程，返回答案、最终文档及候选文档。
retriever_generator.py:QwenRetrieverGenerator:query(self, user_input: str, evaluator_func: Optional[Callable[[str], bool]] = None) -> Tuple[str, List[Dict], List[Dict]]: 主查询入口，支持标准模式或自适应重试模式，返回答案及文档。

rag_engine.py:RAGEngine:__init__(self, collection_name: Optional[str] = None, log_file_path: Optional[str] = None) -> None: 初始化 RAG 引擎，内部创建 QwenRetrieverGenerator 实例。
rag_engine.py:RAGEngine:list_collections(self) -> List[str]: 列出所有可用集合名称。
rag_engine.py:RAGEngine:get_collection_info(self, collection_name: str) -> Optional[Dict[str, Any]]: 获取指定集合的详细信息。
rag_engine.py:RAGEngine:set_collection(self, collection_name: str) -> bool: 切换当前使用的集合。
rag_engine.py:RAGEngine:query(self, question: str) -> Tuple[str, Dict[str, Any]]: 根据问题生成 Markdown 格式的回答及元数据。
rag_engine.py:RAGEngine:_format_answer_markdown(self, question: str, answer: str, contexts: List[Dict]) -> str: 将问题和答案格式化为 Markdown 字符串，包含参考来源。
rag_engine.py:RAGEngine:set_retrieval_params(self, initial_k: Optional[int] = None, final_top_k: Optional[int] = None) -> None: 动态调整检索参数（初始召回数和最终保留数）。
rag_engine.py:calculate_dcg_from_scores(scores: List[float]) -> float: 根据增益列表计算折损累计增益（DCG）。
rag_engine.py:calc_mrr(scores: List[float]) -> float: 计算平均倒数排名（MRR），最高分文档视为唯一相关文档。
rag_engine.py:calc_ndcg(scores: List[float]) -> float: 计算归一化折损累计增益（NDCG）。
rag_engine.py:calculate_bleu_score(candidate: str, reference: str, max_n: int = 4) -> float: 使用 jieba 分词和 NLTK 计算生成答案与参考答案的 BLEU 分数。
rag_engine.py:check_answer_correctness(question: str, generated_answer: str, reference_answer: str) -> bool: 调用 LLM 判断生成答案是否与参考答案语义一致。