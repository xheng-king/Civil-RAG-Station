import os
import json
import math
import jieba
from typing import List, Dict, Any, Optional, Tuple
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
from openai import OpenAI
import warnings
warnings.filterwarnings('ignore')

from backend.core.retriever_generator import QwenRetrieverGenerator
from backend.core.settings import (
    LLM_API_KEY, LLM_BASE_URL, LLM_MODEL,
    ENABLE_ADAPTIVE_RETRIEVAL,
    BASE_INITIAL_RETRIEVE_K, BASE_FINAL_TOP_K
)

# 用于评估的 LLM 客户端（仅在评估函数中使用）
_eval_client = OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY) if LLM_API_KEY else None


class RAGEngine:
    """
    线上 RAG 引擎，提供集合管理和问答能力。
    返回的回答为 LLM 直接生成的原始文本（含自然语言中的 Markdown 格式），
    前端直接渲染，不再额外拼接参考来源。
    """

    def __init__(self, collection_name: Optional[str] = None, log_file_path: Optional[str] = None):
        """
        初始化 RAG 引擎
        :param collection_name: 初始绑定的集合名称（可选）
        :param log_file_path: 日志文件路径（可选）
        """
        self.retriever = QwenRetrieverGenerator(collection_name=collection_name, log_file_path=log_file_path)

    # ---------- 集合管理 ----------
    def list_collections(self) -> List[str]:
        """列出所有可用的集合名称"""
        return self.retriever.list_collections()

    def get_collection_info(self, collection_name: str) -> Optional[Dict[str, Any]]:
        """获取指定集合的详细信息（如文档数量）"""
        return self.retriever.get_collection_info(collection_name)

    def set_collection(self, collection_name: str) -> bool:
        """切换当前使用的集合"""
        return self.retriever.set_collection(collection_name)

    # ---------- 核心问答 ----------
    def query(self, question: str, adaptive_enabled: bool = False) -> Tuple[str, Dict[str, Any]]:
        """
        根据问题生成回答
        :param question: 用户问题
        :param adaptive_enabled: 是否启用自适应检索（若后端配置允许则生效）
        :return: (answer, metadata)   answer 为 LLM 直接生成的原始回答（可能含 Markdown）
        """
        if self.retriever.collection is None:
            raise ValueError("未设置集合，请先调用 set_collection() 或初始化时指定 collection_name")

        # 根据 adaptive_enabled 决定是否传入评估函数（仅当后端配置了自适应检索时才有意义）
        evaluator = None
        if adaptive_enabled:
            # 简单评估器：判断答案中是否包含暗示失败的关键词
            def simple_evaluator(answer: str) -> bool:
                negative_keywords = ["抱歉", "没有找到", "无法回答", "未找到相关", "暂无", "未检索到"]
                return not any(kw in answer for kw in negative_keywords)
            evaluator = simple_evaluator

        # 调用检索生成器，获得 LLM 答案
        answer, final_docs, _ = self.retriever.query(question, evaluator_func=evaluator)

        # 元数据（可用于日志或调试）
        metadata = {
            "question": question,
            "answer": answer,
            "num_contexts": len(final_docs),
            "collection": self.retriever.collection.name if self.retriever.collection else None,
            "adaptive_used": adaptive_enabled,
        }
        # 直接返回 answer，不再进行额外包装
        return answer, metadata

    # ---------- 高级参数调整 ----------
    def set_retrieval_params(self, initial_k: Optional[int] = None, final_top_k: Optional[int] = None):
        """动态调整检索参数"""
        if initial_k is not None:
            self.retriever.initial_retrieve_k = initial_k
        if final_top_k is not None:
            self.retriever.final_top_k = final_top_k


# ========== 以下为评估相关工具函数（复用原逻辑，供线上监控使用） ==========
def calculate_dcg_from_scores(scores: List[float]) -> float:
    """计算 DCG"""
    dcg = 0.0
    for i, score in enumerate(scores):
        gain = 2 ** score - 1
        dcg += gain / math.log2(i + 2)
    return dcg


def calc_mrr(scores: List[float]) -> float:
    """计算 MRR（最高分文档视为唯一相关文档）"""
    if not scores:
        return 0.1
    max_idx = max(range(len(scores)), key=lambda i: scores[i])
    rank = max_idx + 1
    return 1.0 / rank if rank <= 5 else 0.1


def calc_ndcg(scores: List[float]) -> float:
    """计算 NDCG"""
    if not scores:
        return 0.0
    dcg = calculate_dcg_from_scores(scores)
    ideal_scores = sorted(scores, reverse=True)
    idcg = calculate_dcg_from_scores(ideal_scores)
    return dcg / idcg if idcg > 0 else 0.0


def calculate_bleu_score(candidate: str, reference: str, max_n: int = 4) -> float:
    """计算 BLEU 分数"""
    if not candidate or not reference:
        return 0.0
    try:
        candidate_tokens = jieba.lcut(candidate.strip())
        reference_tokens = jieba.lcut(reference.strip())
        if not candidate_tokens:
            return 0.0
        weights = tuple(1.0 / max_n for _ in range(max_n))
        smoothing = SmoothingFunction().method1
        bleu = sentence_bleu([reference_tokens], candidate_tokens, weights=weights, smoothing_function=smoothing)
        return bleu
    except Exception as e:
        print(f"BLEU 计算失败: {e}")
        return 0.0


def check_answer_correctness(question: str, generated_answer: str, reference_answer: str) -> bool:
    """调用 LLM 判断生成答案是否正确"""
    if _eval_client is None:
        raise ValueError("LLM API 未配置，无法进行正确性评估")
    prompt = f"""
你是一个专业的评判员。我会给你一个问题、一个参考答案和一个待评价的答案。
你的任务是判断待评价答案是否与参考答案一致。你可以容忍一些措辞上的差异。
但对于参考答案表示信息不足等情况一律判断为"INCORRECT"
请严格只回复 "CORRECT" 或 "INCORRECT"。

问题: {question}

参考标准答案: {reference_answer}

模型生成答案: {generated_answer}
"""
    try:
        response = _eval_client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=10,
        )
        result = response.choices[0].message.content.strip().upper()
        return result == "CORRECT"
    except Exception as e:
        print(f"评估正确性时出错: {e}")
        return False