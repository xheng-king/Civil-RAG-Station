import os
import chromadb
from openai import OpenAI
from typing import List, Dict, Any, Callable, Optional, Tuple
import json
import requests
from datetime import datetime

from backend.core.settings import (
    VECTORSTORE_PATH,
    EMBEDDING_API_KEY,
    EMBEDDING_BASE_URL,
    EMBEDDING_MODEL,
    RERANK_API_KEY,
    RERANK_BASE_URL,
    RERANK_MODEL,
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_MODEL,
    ENABLE_ADAPTIVE_RETRIEVAL,
    MAX_RETRIEVAL_ROUNDS,
    RETRIEVAL_STEP_SIZE,
    RERANK_OUTPUT_STEP_SIZE,
    BASE_INITIAL_RETRIEVE_K,
    BASE_FINAL_TOP_K,
)
from backend.core.database_manager import DatabaseManager

class QwenRetrieverGenerator:
    def __init__(self, collection_name: Optional[str] = None, log_file_path: Optional[str] = None):
        """
        初始化检索生成器
        :param collection_name: 可选，初始绑定的集合名称
        :param log_file_path: 日志文件路径（默认项目根目录下的 query_log.md）
        """
        if not EMBEDDING_API_KEY:
            raise ValueError("settings 中 EMBEDDING_API_KEY 未设置")
        self.embedding_client = OpenAI(
            api_key=EMBEDDING_API_KEY,
            base_url=EMBEDDING_BASE_URL
        )
        
        if not LLM_API_KEY:
            raise ValueError("settings 中 LLM_API_KEY 未设置")
        self.llm_client = OpenAI(
            api_key=LLM_API_KEY,
            base_url=LLM_BASE_URL
        )
        
        self.rerank_api_key = RERANK_API_KEY
        
        self.chroma_client = chromadb.PersistentClient(path=VECTORSTORE_PATH)
        self.db_manager = DatabaseManager(persist_directory=VECTORSTORE_PATH)
        
        self.initial_retrieve_k = BASE_INITIAL_RETRIEVE_K
        self.final_top_k = BASE_FINAL_TOP_K
        
        if log_file_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            self.log_file_path = os.path.join(base_dir, "query_log.md")
        else:
            self.log_file_path = log_file_path
        os.makedirs(os.path.dirname(self.log_file_path), exist_ok=True)
        
        self.collection = None
        if collection_name:
            self.set_collection(collection_name)
    
    def set_collection(self, collection_name: str) -> bool:
        try:
            self.collection = self.chroma_client.get_collection(name=collection_name)
            print(f"已选择集合: {collection_name}")
            return True
        except Exception as e:
            print(f"获取集合 '{collection_name}' 失败: {e}")
            self.collection = None
            return False
    
    def list_collections(self) -> List[str]:
        return self.db_manager.list_collections()
    
    def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        return self.db_manager.get_collection_info(collection_name)
    
    def _log_interaction(self, user_input: str, response: str, round_num: int = 1, status: str = "Final"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        markdown_content = f"## {timestamp} - Round {round_num} ({status})\n**Q:** {user_input}\n**A:** {response}\n\n"
        try:
            with open(self.log_file_path, 'a', encoding='utf-8') as f:
                f.write(markdown_content)
        except Exception as e:
            print(f"记录日志时出错: {e}")
    
    def embed_query(self, query_text: str) -> List[float]:
        response = self.embedding_client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=query_text
        )
        return response.data[0].embedding
    
    def retrieve_documents(self, query_text: str, k: int = None) -> List[Dict[str, Any]]:
        if self.collection is None:
            raise ValueError("未设置集合，请先调用 set_collection()")
        if k is None:
            k = self.initial_retrieve_k
        
        query_embedding = [self.embed_query(query_text)]
        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=k,
            include=['documents', 'metadatas', 'distances']
        )
        
        documents = results['documents'][0] if results['documents'] else []
        metadatas = results['metadatas'][0] if results['metadatas'] else []
        distances = results['distances'][0] if results['distances'] else []
        
        retrieved_docs = []
        for i, (doc, meta, dist) in enumerate(zip(documents, metadatas, distances)):
            retrieved_docs.append({
                'id': i,
                'content': doc,
                'metadata': meta,
                'initial_distance': dist,
                'score': 1.0 - dist,
                'rerank_score': None
            })
        return retrieved_docs
    
    def _rerank_all_documents(self, query: str, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not documents:
            return []
        if not self.rerank_api_key:
            print("重排序 API Key 未设置，跳过重排序")
            return documents
        try:
            headers = {
                "Authorization": f"Bearer {self.rerank_api_key}",
                "Content-Type": "application/json"
            }
            texts_to_rerank = [doc['content'] for doc in documents]
            payload = {
                "model": RERANK_MODEL,
                "documents": texts_to_rerank,
                "query": query,
                "top_n": len(documents),
            }
            response = requests.post(RERANK_BASE_URL, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()
            if 'results' in result:
                reranked_docs = []
                for rank_data in result['results']:
                    original_index = rank_data['index']
                    relevance_score = rank_data['relevance_score']
                    if original_index < len(documents):
                        updated_doc = documents[original_index].copy()
                        updated_doc['rerank_score'] = relevance_score
                        reranked_docs.append(updated_doc)
                return reranked_docs
            else:
                print(f"重排序 API 响应格式异常: {result}")
        except Exception as e:
            print(f"重排序失败: {e}")
        documents.sort(key=lambda x: x['initial_distance'])
        return documents
    
    def rerank_documents(self, query: str, documents: List[Dict[str, Any]], top_n: int = None) -> List[Dict[str, Any]]:
        if top_n is None:
            top_n = self.final_top_k
        if not documents:
            return []
        actual_top_n = min(top_n, len(documents))
        all_reranked = self._rerank_all_documents(query, documents)
        final = all_reranked[:actual_top_n]
        for idx, doc in enumerate(final):
            doc['rerank_rank'] = idx + 1
        return final
    
    def generate_answer(self, query: str, contexts: List[Dict[str, Any]]) -> str:
        if not contexts:
            return "抱歉，没有找到相关文档。"
        
        context_parts = []
        for doc in contexts:
            source = doc.get('metadata', {}).get('source', '未知')
            score = doc.get('rerank_score', doc.get('score', 0))
            rank = doc.get('rerank_rank', '?')
            context_parts.append(
                f"参考信息 #{rank} (相关性: {score:.4f}, 来源: {source}):\n{doc['content']}"
            )
        context_str = "\n\n".join(context_parts)
        
        prompt = f"""基于以下数据库内容，回答用户的问题。

数据库内容：
{context_str}

用户问题：
{query}

回答要求：
1. 若数据库内容中存在用户问题的相关回答，则直接简明扼要地回答问题。
2. 若数据库中不存在用户问题的相关解答，提示用户查询结果没有相关内容。
"""
        try:
            completion = self.llm_client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": "你是一个专业的知识助手，能够基于提供的多段上下文信息回答用户的问题。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=800
            )
            return completion.choices[0].message.content.strip()
        except Exception as e:
            print(f"生成答案出错: {e}")
            simple_context = "\n\n".join([doc['content'] for doc in contexts])
            simple_prompt = f"基于以下信息回答问题:\n\n{simple_context}\n\n问题: {query}"
            try:
                completion = self.llm_client.chat.completions.create(
                    model=LLM_MODEL,
                    messages=[{"role": "user", "content": simple_prompt}],
                    max_tokens=600
                )
                return completion.choices[0].message.content.strip()
            except:
                return "抱歉，生成答案时遇到问题。"
    
    def _execute_single_round(self, user_input: str, initial_k: int, final_top_k: int) -> Tuple[str, List[Dict], List[Dict]]:
        candidate_docs = self.retrieve_documents(user_input, k=initial_k)
        if not candidate_docs:
            return "抱歉，没有找到相关文档。", [], []
        all_reranked = self._rerank_all_documents(user_input, candidate_docs)
        final_docs = all_reranked[:final_top_k]
        for idx, doc in enumerate(final_docs):
            doc['rerank_rank'] = idx + 1
        answer = self.generate_answer(user_input, final_docs)
        return answer, final_docs, candidate_docs
    
    def query(self, user_input: str, evaluator_func: Optional[Callable[[str], bool]] = None) -> Tuple[str, List[Dict], List[Dict]]:
        if self.collection is None:
            raise ValueError("未设置集合，请先调用 set_collection()")
        
        if not ENABLE_ADAPTIVE_RETRIEVAL or evaluator_func is None:
            answer, final_docs, candidates = self._execute_single_round(
                user_input, self.initial_retrieve_k, self.final_top_k
            )
            return answer, final_docs, candidates
        
        current_initial_k = self.initial_retrieve_k
        current_final_top_k = self.final_top_k
        last_answer = ""
        last_final_docs = []
        last_candidates = []
        
        for round_num in range(1, MAX_RETRIEVAL_ROUNDS + 1):
            answer, final_docs, candidates = self._execute_single_round(
                user_input, current_initial_k, current_final_top_k
            )
            last_answer = answer
            last_final_docs = final_docs
            last_candidates = candidates
            
            if evaluator_func(answer):
                return answer, final_docs, candidates
            else:
                if round_num < MAX_RETRIEVAL_ROUNDS:
                    current_initial_k += RETRIEVAL_STEP_SIZE
                    current_final_top_k += RERANK_OUTPUT_STEP_SIZE
        
        return last_answer, last_final_docs, last_candidates