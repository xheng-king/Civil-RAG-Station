# backend/core/settings.py
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件（如果存在）
load_dotenv()

# 项目根目录（backend 的上两级目录，即 rag_ce_online/）
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ========== 向量数据库路径 ==========
VECTORSTORE_PATH = os.getenv("VECTORSTORE_PATH", str(BASE_DIR / "data" / "vectorstore"))

# ========== Embedding 模型配置 ==========
EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY", "")
EMBEDDING_BASE_URL = os.getenv("EMBEDDING_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-v3")

# ========== 重排序模型配置 ==========
RERANK_API_KEY = os.getenv("RERANK_API_KEY", "")
RERANK_BASE_URL = os.getenv("RERANK_BASE_URL", "https://dashscope.aliyuncs.com/api/v1/rerank")
RERANK_MODEL = os.getenv("RERANK_MODEL", "gte-rerank")

# ========== LLM 模型配置（问答生成） ==========
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen-plus")

# ========== 分块参数 ==========
DEFAULT_MIN_CHUNK_SIZE = int(os.getenv("DEFAULT_MIN_CHUNK_SIZE", "512"))
DEFAULT_MAX_CHUNK_SIZE = int(os.getenv("DEFAULT_MAX_CHUNK_SIZE", "2048"))

# ========== 检索参数 ==========
# 基础初始召回数量
BASE_INITIAL_RETRIEVE_K = int(os.getenv("BASE_INITIAL_RETRIEVE_K", "20"))
# 基础重排序后最终使用的文档数
BASE_FINAL_TOP_K = int(os.getenv("BASE_FINAL_TOP_K", "5"))

# ========== 自适应检索配置 ==========
ENABLE_ADAPTIVE_RETRIEVAL = os.getenv("ENABLE_ADAPTIVE_RETRIEVAL", "false").lower() == "true"
MAX_RETRIEVAL_ROUNDS = int(os.getenv("MAX_RETRIEVAL_ROUNDS", "3"))
RETRIEVAL_STEP_SIZE = int(os.getenv("RETRIEVAL_STEP_SIZE", "10"))           # 每轮增加的初始召回数
RERANK_OUTPUT_STEP_SIZE = int(os.getenv("RERANK_OUTPUT_STEP_SIZE", "2"))    # 每轮增加的重排序后数量

# ========== 日志文件路径 ==========
QUERY_LOG_PATH = os.getenv("QUERY_LOG_PATH", str(BASE_DIR / "query_log.md"))

BASIC_DOCS_DIR = "./data/basicdocs"  # 存放系统自带规范文档的目录