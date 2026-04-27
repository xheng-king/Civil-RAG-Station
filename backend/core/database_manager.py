# backend/core/database_manager.py
import chromadb
from typing import List, Dict, Any
from backend.core.settings import VECTORSTORE_PATH

class DatabaseManager:
    """
    ChromaDB 集合管理封装
    提供列出集合、清空集合、创建空集合等功能
    """

    def __init__(self, persist_directory: str = None):
        """
        初始化数据库管理器
        :param persist_directory: 向量数据库持久化目录，若未指定则使用 settings.VECTORSTORE_PATH
        """
        self.persist_directory = persist_directory or VECTORSTORE_PATH
        self.client = chromadb.PersistentClient(path=self.persist_directory)

    def list_collections(self) -> List[str]:
        """
        列出当前数据库中所有集合及文档数量（打印信息并返回集合名称列表）
        :return: 集合名称列表
        """
        try:
            collections = self.client.list_collections()
            print("当前存在的集合:")
            collection_names = []
            for i, coll in enumerate(collections, 1):
                try:
                    cnt = self.client.get_collection(coll.name).count()
                    print(f"  {i}. {coll.name} (文档数: {cnt})")
                except Exception as e:
                    print(f"  {i}. {coll.name} (无法获取文档数: {e})")
                collection_names.append(coll.name)
            return collection_names
        except Exception as e:
            print(f"无法访问数据库: {e}")
            return []

    def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """
        获取指定集合的详细信息（文档数等）
        :param collection_name: 集合名称
        :return: 包含 name, count 的字典，若失败返回 None 或抛出异常
        """
        try:
            coll = self.client.get_collection(name=collection_name)
            return {"name": collection_name, "count": coll.count()}
        except Exception as e:
            print(f"获取集合 '{collection_name}' 信息失败: {e}")
            return None

    def clear_collection(self, collection_name: str) -> bool:
        """
        清空指定集合中的所有文档
        :param collection_name: 集合名称
        :return: 操作是否成功
        """
        try:
            collection = self.client.get_collection(name=collection_name)
            all_result = collection.get()
            all_ids = all_result['ids']
            if all_ids:
                collection.delete(ids=all_ids)
                print(f"集合 '{collection_name}' 已清空 ({len(all_ids)} 条文档)")
            else:
                print(f"集合 '{collection_name}' 本身已为空")
            return True
        except Exception as e:
            print(f"清空集合时出错: {e}")
            return False

    def create_empty_collection(self, collection_name: str) -> bool:
        """
        创建一个新的空集合（如果已存在则直接返回成功）
        :param collection_name: 集合名称
        :return: 操作是否成功
        """
        try:
            self.client.get_or_create_collection(name=collection_name)
            print(f"集合 '{collection_name}' 已创建或已存在")
            return True
        except Exception as e:
            print(f"创建集合时出错: {e}")
            return False

    def delete_collection(self, collection_name: str) -> bool:
        """
        完全删除一个集合
        :param collection_name: 集合名称
        :return: 是否删除成功
        """
        try:
            self.client.delete_collection(name=collection_name)
            print(f"集合 '{collection_name}' 已删除")
            return True
        except Exception as e:
            print(f"删除集合时出错: {e}")
            return False

    def get_collection(self, collection_name: str):
        """
        获取 ChromaDB 集合对象（供高级操作使用）
        :param collection_name: 集合名称
        :return: Collection 对象，若不存在则返回 None
        """
        try:
            return self.client.get_collection(name=collection_name)
        except Exception as e:
            print(f"获取集合对象失败: {e}")
            return None