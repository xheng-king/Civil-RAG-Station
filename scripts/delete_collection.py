#!/usr/bin/env python3
"""
彻底删除 ChromaDB 集合（正确映射物理文件夹）
用法：python delete_collection_correct.py <集合名称>
"""

import os
import sys
import shutil
import sqlite3
from backend.core.database_manager import DatabaseManager
from backend.core.settings import VECTORSTORE_PATH

def get_physical_folder_name(collection_name: str) -> str | None:
    """通过元数据库查询真正的物理文件夹名（segments.id）"""
    chroma_db = os.path.join(VECTORSTORE_PATH, "chroma.sqlite3")
    if not os.path.exists(chroma_db):
        print(f"错误：元数据库不存在 {chroma_db}")
        return None
    conn = sqlite3.connect(chroma_db)
    cur = conn.cursor()
    # 关键：从 segments 表获取 id，而不是 collections.id
    cur.execute("""
        SELECT s.id 
        FROM segments s 
        JOIN collections c ON s.collection = c.id 
        WHERE c.name = ? AND s.scope = 'VECTOR'
    """, (collection_name,))
    row = cur.fetchone()
    conn.close()
    if row:
        return row[0]
    else:
        return None

def fully_delete_collection(collection_name: str):
    # 1. 获取真正的物理文件夹名
    folder_name = get_physical_folder_name(collection_name)
    if not folder_name:
        print(f"错误：找不到集合 '{collection_name}' 对应的物理文件夹（segments.id）")
        print("可能原因：集合不存在，或元数据已损坏。")
        return False

    # 2. 删除物理文件夹
    folder_path = os.path.join(VECTORSTORE_PATH, folder_name)
    if os.path.exists(folder_path):
        print(f"删除物理文件夹: {folder_path}")
        shutil.rmtree(folder_path)
        print("  ✓ 文件夹已删除")
    else:
        print(f"警告：物理文件夹不存在: {folder_path}")

    # 3. 调用 ChromaDB API 删除元数据（会自动清理 collections 和 segments 记录）
    db_manager = DatabaseManager()
    try:
        db_manager.delete_collection(collection_name)
        print("  ✓ 元数据已删除")
    except Exception as e:
        print(f"  ✗ API删除元数据失败: {e}")
        # 降级：直接 SQL 删除（慎用）
        chroma_db = os.path.join(VECTORSTORE_PATH, "chroma.sqlite3")
        conn = sqlite3.connect(chroma_db)
        cur = conn.cursor()
        cur.execute("DELETE FROM collections WHERE name = ?", (collection_name,))
        conn.commit()
        conn.close()
        print("  已通过 SQL 强制删除元数据记录")

    print(f"✅ 集合 '{collection_name}' 已彻底清理")
    return True

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法: python delete_collection_correct.py <集合名称>")
        sys.exit(1)
    fully_delete_collection(sys.argv[1])