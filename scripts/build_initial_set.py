import os
from backend.core.indexer import QwenIndexer

# 目标目录（相对于项目根目录）
DOCS_DIR = "data/basicdoc"
COLLECTION_NAME = "gb50010_gb50011_gb50017"  # 可根据需要修改
MIN_CHUNK_SIZE = 512
MAX_CHUNK_SIZE = 2048

def is_text_file(file_path: str) -> bool:
    """简单判断是否为文本文件（尝试读取前1KB）"""
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(1024)
            # 如果包含 null 字节，大概率是二进制
            if b'\0' in chunk:
                return False
        return True
    except Exception:
        return False

def is_supported_extension(file_name: str) -> bool:
    """可选：只处理常见文本扩展名，若不使用则注释掉"""
    ext = os.path.splitext(file_name)[1].lower()
    supported = {'.txt', '.md', '.text', '.markdown'}
    return ext in supported

def collect_files(root_dir: str, recursive: bool = True):
    """收集目录下的所有文件（可选递归）"""
    files = []
    if recursive:
        for dirpath, _, filenames in os.walk(root_dir):
            for f in filenames:
                files.append(os.path.join(dirpath, f))
    else:
        for f in os.listdir(root_dir):
            full = os.path.join(root_dir, f)
            if os.path.isfile(full):
                files.append(full)
    return files

def main():
    # 检查目录是否存在
    if not os.path.isdir(DOCS_DIR):
        print(f"错误：目录不存在 - {DOCS_DIR}")
        return

    # 初始化索引器
    indexer = QwenIndexer()

    # 收集所有文件（递归子目录）
    all_files = collect_files(DOCS_DIR, recursive=True)
    print(f"在 {DOCS_DIR} 中找到 {len(all_files)} 个文件")

    for file_path in all_files:
        # 可选：根据扩展名过滤
        # if not is_supported_extension(file_path):
        #     print(f"跳过不支持的文件类型: {file_path}")
        #     continue

        # 检查是否为文本文件（避免二进制文件导致错误）
        if not is_text_file(file_path):
            print(f"警告：跳过二进制文件 {file_path}")
            continue

        # 获取相对路径用作显示名称
        rel_path = os.path.relpath(file_path, DOCS_DIR)
        print(f"正在索引: {rel_path} ...")

        try:
            result = indexer.index_single_file_to_collection(
                file_path=file_path,
                collection_name=COLLECTION_NAME,
                min_chunk_size=MIN_CHUNK_SIZE,
                max_chunk_size=MAX_CHUNK_SIZE
            )
            if result.get("success"):
                print(f"  完成，分块数: {result.get('chunks', 0)}")
            else:
                print(f"  失败: {result.get('error', '未知错误')}")
        except Exception as e:
            print(f"  处理出错: {e}")

if __name__ == "__main__":
    main()