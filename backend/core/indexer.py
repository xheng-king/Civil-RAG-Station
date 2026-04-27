# backend/core/indexer.py
import os
import re
import csv
import chromadb
from openai import OpenAI
from typing import List, Optional, Dict, Any
from backend.core.settings import (
    EMBEDDING_API_KEY,
    EMBEDDING_BASE_URL,
    EMBEDDING_MODEL,
    VECTORSTORE_PATH,
    DEFAULT_MIN_CHUNK_SIZE,
    DEFAULT_MAX_CHUNK_SIZE,
)

class QwenIndexer:
    """文档索引器：负责文本分块、向量化并存入 ChromaDB"""

    def __init__(self):
        if not EMBEDDING_API_KEY:
            raise ValueError("settings.py 中的 EMBEDDING_API_KEY 未设置")
        
        self.client = OpenAI(
            api_key=EMBEDDING_API_KEY,
            base_url=EMBEDDING_BASE_URL
        )
        
        # 确保向量存储目录存在
        os.makedirs(VECTORSTORE_PATH, exist_ok=True)
        self.chroma_client = chromadb.PersistentClient(path=VECTORSTORE_PATH)
        # 原 DatabaseManager 在此并不需要，直接使用 chroma_client

    # ---------- 以下为原始保留的静态/辅助方法 ----------
    def blocks(self, text: str) -> List[str]:
        """基于条款号正则切分文本块"""
        clause_pattern = r'\n\s*(?:\d+(?:\.\d+)+~)?\d+(?:\.\d+)+\s+'
        clauses_found = list(re.finditer(clause_pattern, text))
        
        if not clauses_found:
            return [text.strip()] if text.strip() else []

        chunks = []
        start = 0
        for match in clauses_found:
            clause_end = match.end()
            chunk_content = text[start:clause_end].strip()
            if chunk_content:
                chunks.append(chunk_content)
            start = clause_end
        
        if start < len(text):
            remaining_content = text[start:].strip()
            if remaining_content:
                chunks.append(remaining_content)
        return chunks

    def connect(self, str1: str, str2: str) -> str:
        if not str1:
            return str2
        if not str2:
            return str1
        return str1 + "\n" + str2

    def cut_string(self, s: str, start: int, end: int) -> str:
        return s[start:end]

    def structural_chunk(self, text: str, min_chunk_size: int = 512, max_chunk_size: int = 2048) -> List[str]:
        """结构分块：合并短块、切割长块，确保每个块长度在 [min_chunk_size, max_chunk_size] 范围内"""
        initial_chunks = self.blocks(text)
        final_chunks = []
        current_chunk = ""

        for block_i in initial_chunks:
            # 如果当前块超过最大长度，强行切割
            while len(current_chunk) > max_chunk_size:
                part = self.cut_string(current_chunk, 0, max_chunk_size)
                final_chunks.append(part)
                current_chunk = self.cut_string(current_chunk, max_chunk_size, len(current_chunk))

            if len(current_chunk) == max_chunk_size:
                final_chunks.append(current_chunk)
                current_chunk = ""

            potential_chunk = self.connect(current_chunk, block_i)

            if len(potential_chunk) <= max_chunk_size:
                current_chunk = potential_chunk
                if len(current_chunk) >= min_chunk_size:
                    final_chunks.append(current_chunk)
                    current_chunk = ""
            else:
                if current_chunk != "":
                    final_chunks.append(current_chunk)
                    current_chunk = block_i
                else:
                    long_part = self.cut_string(block_i, 0, max_chunk_size)
                    remaining_part = self.cut_string(block_i, max_chunk_size, len(block_i))
                    final_chunks.append(long_part)
                    current_chunk = remaining_part

        while len(current_chunk) > max_chunk_size:
            part = self.cut_string(current_chunk, 0, max_chunk_size)
            final_chunks.append(part)
            current_chunk = self.cut_string(current_chunk, max_chunk_size, len(current_chunk))
        
        if current_chunk.strip():
            final_chunks.append(current_chunk)
        return final_chunks

    def read_and_chunk_file(self, file_path: str, min_chunk_size: int = 512, max_chunk_size: int = 2048) -> List[str]:
        """从文件读取并分块（保留原接口）"""
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        return self.structural_chunk(content, min_chunk_size, max_chunk_size)

    def create_embeddings(self, texts: List[str]) -> List[List[float]]:
        """调用 Embedding API 生成向量"""
        embeddings = []
        for i, text in enumerate(texts):
            # 生产环境可改用 logger 替换 print
            print(f"为第 {i+1}/{len(texts)} 块生成嵌入...")
            try:
                response = self.client.embeddings.create(
                    model=EMBEDDING_MODEL,
                    input=text
                )
                embeddings.append(response.data[0].embedding)
            except Exception as e:
                print(f"生成嵌入失败: {e}")
                raise e
        return embeddings

    # ---------- 核心索引方法 ----------
    def index_text_to_collection(
        self,
        text: str,
        filename: str,
        collection_name: str,
        min_chunk_size: int = DEFAULT_MIN_CHUNK_SIZE,
        max_chunk_size: int = DEFAULT_MAX_CHUNK_SIZE,
        record_stats: bool = True
    ) -> Dict[str, Any]:
        """
        将文本内容分块、向量化后存入指定集合（Web 上传后推荐使用）
        返回索引信息统计
        """
        # 1. 分块
        segments = self.structural_chunk(text, min_chunk_size, max_chunk_size)
        if not segments:
            return {"success": False, "error": "文本为空或分块后无内容", "total_chunks": 0}
        
        # 2. 生成向量
        embeddings = self.create_embeddings(segments)
        
        # 3. 获取或创建集合
        collection = self.chroma_client.get_or_create_collection(name=collection_name)
        
        # 4. 生成 ids 和 metadatas
        base_name = os.path.splitext(filename)[0]
        ids = [f"{base_name}_seg_{i}" for i in range(len(segments))]
        metadatas = [{
            "source": filename,
            "segment_number": i+1,
            "file": base_name,
            "min_chunk_size": min_chunk_size,
            "max_chunk_size": max_chunk_size,
            "length": len(segments[i])
        } for i in range(len(segments))]
        
        # 5. 入库
        collection.add(
            documents=segments,
            metadatas=metadatas,
            ids=ids,
            embeddings=embeddings
        )
        
        # 6. 可选：记录统计信息到 CSV（与原项目保持一致）
        # if record_stats:
        #     self._record_chunk_stats(filename, segments)
        
        return {
            "success": True,
            "total_chunks": len(segments),
            "collection": collection_name,
            "filename": filename,
            "avg_chunk_length": round(sum(len(s) for s in segments) / len(segments), 2) if segments else 0
        }

    def index_single_file_to_collection(
        self,
        file_path: str,
        collection_name: str,
        min_chunk_size: int = DEFAULT_MIN_CHUNK_SIZE,
        max_chunk_size: int = DEFAULT_MAX_CHUNK_SIZE,
        record_stats: bool = True
    ) -> Dict[str, Any]:
        """从本地文件路径索引（保留原接口，内部调用 text 版本）"""
        filename = os.path.basename(file_path)
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
        return self.index_text_to_collection(
            text=text,
            filename=filename,
            collection_name=collection_name,
            min_chunk_size=min_chunk_size,
            max_chunk_size=max_chunk_size,
            record_stats=record_stats
        )

    def _record_chunk_stats(self, filename: str, segments: List[str]) -> None:
        """将分块细节追加写入项目根目录下的 chunk_details.csv（与原项目逻辑一致）"""
        # 这里假设 chunk_details.csv 位于项目根目录，可根据实际调整
        csv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "chunk_details.csv")
        file_exists = os.path.isfile(csv_path)
        with open(csv_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['file_name', 'chunk_index', 'length'])
            if not file_exists:
                writer.writeheader()
            for i, seg in enumerate(segments):
                writer.writerow({
                    'file_name': filename,
                    'chunk_index': i,
                    'length': len(seg),
                })