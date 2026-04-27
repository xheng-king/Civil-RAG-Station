import os
from backend.core.indexer import QwenIndexer
from backend.core.settings import SOURCE_DOCS_DIR  # 假设你定义了集合名

indexer = QwenIndexer()
for filename in os.listdir(SOURCE_DOCS_DIR):
    if filename.endswith(".md"):
        file_path = os.path.join(SOURCE_DOCS_DIR, filename)
        print(f"Indexing {filename}...")
        indexer.index_single_file_to_collection(
            file_path=file_path,
            collection_name="gb50010_gb50011_gb50017",
            min_chunk_size=512,
            max_chunk_size=2048
        )