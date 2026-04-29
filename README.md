# RAG 工程规范问答系统

基于 **RAG**（检索增强生成）的本地知识库问答系统，支持上传规范文档（.md/.txt），自动分块、向量化并存入 ChromaDB，通过大模型（Qwen）提供智能问答。前端提供友好的 Web 界面，支持 **Markdown** 与 **LaTeX** 渲染。

界面展示：  
<img width="75%" alt="钢结构问题1" src="https://github.com/user-attachments/assets/98cffc92-5b25-42ab-8781-5d05cb56f6f8" />

## 快速开始

### 1. 克隆代码并创建虚拟环境

```bash
git clone <your-repo-url>
cd rag_ce_online
python -m venv venv
source venv/bin/activate        # Linux/Mac
# .\venv\Scripts\activate       # Windows
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量（重要）

项目依赖 `.env` 文件中的 API 密钥等配置，需手动创建。

在项目根目录下创建 `.env` 文件，内容如下（请替换为您自己的 API Key）：

```
# 服务器配置
PORT=8080

# Embedding 模型
EMBEDDING_API_KEY=sk-xxxx
EMBEDDING_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
EMBEDDING_MODEL=text-embedding-v3

# Rerank 模型（可选，若无 Rerank 服务可留空，会自动降级）
RERANK_API_KEY=sk-xxxx
RERANK_BASE_URL=https://dashscope.aliyuncs.com/compatible-api/v1/reranks
RERANK_MODEL=qwen3-rerank

# LLM 模型
LLM_API_KEY=sk-xxxx
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen-max

# 其他配置（默认值通常无需修改）
VECTORSTORE_PATH=data/vectorstore
DEFAULT_MIN_CHUNK_SIZE=512
DEFAULT_MAX_CHUNK_SIZE=2048
BASE_INITIAL_RETRIEVE_K=20
BASE_FINAL_TOP_K=5
ENABLE_ADAPTIVE_RETRIEVAL=false
```

> **注意**：请确保 API Key 有效，且对应服务已开通。

如果您希望使用自己部署的模型（如通过 Ollama、vLLM、LocalAI 等），只需修改对应的 `*_BASE_URL` 和 `*_MODEL`，并视情况填写 API Key（若无鉴权则可留空或填任意值）。

**示例：使用 Ollama 部署的 Qwen2.5 模型**

```ini
# 假设 Ollama 服务运行在本地 11434 端口，且兼容 OpenAI API 格式
LLM_API_KEY=ollama
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=qwen2.5:7b

# 同理，Embedding 模型也可使用本地服务（如Qwen3-Embedding-0.6B）
EMBEDDING_API_KEY=ollama
EMBEDDING_BASE_URL=http://localhost:11434/v1
EMBEDDING_MODEL=Qwen3-Embedding-0.6B
```

**注意事项：**
- 私有模型需提供与 OpenAI API 兼容的 `/v1/embeddings` 和 `/v1/chat/completions` 端点。
- Rerank 模型若无本地可用服务，可留空 `RERANK_API_KEY`，系统会自动降级为向量距离排序。
- 确保模型名称与部署时的名称完全一致。

### 4.（可选）构建初始数据库

本系统提供初始数据库，包含GB50010混凝土结构设计规范、GB50011建筑抗震设计规范、GB50017钢结构设计标准三本规范的数据库集合

如需此初始集合，请在项目根目录运行以下命令：

```
python -m scripts.build_initial_set
```

### 5. 启动后端服务

在项目根目录执行：

```bash
python -m backend.main
```

后端将运行在 `.env` 中 `PORT` 指定的端口（默认 8080）。  
访问 `http://localhost:8080` (或你的服务器的公网IP+端口号）即可看到前端界面。

## 技术原理

1. **文档索引流程**  
   - 上传文件 → 按条款结构（正则匹配章节号）切分 → 合并/切割到指定长度（512~2048字符） → 调用 Embedding API 生成向量 → 存入 ChromaDB 集合。

2. **问答流程（RAG）**  
   - 用户问题 → 向量化 → 相似度检索 Top-K 文档 → **重排序**（Rerank，可选） → 将最相关片段拼接成上下文 → 调用 LLM 生成最终答案。

3. **自适应检索**  
   - 若开启，系统会评估答案是否包含失败关键词（如“抱歉”“没有找到”）。若判断失败，则自动增加检索数量并重试。

4. **前端渲染**  
   - 使用 `marked` 解析 Markdown，`highlight.js` 高亮代码，`KaTeX` 渲染 LaTeX 公式。

## 常见问题

- **Q：为什么集合名称不能包含中文？**  
  A：ChromaDB 限制集合名称只能使用字母、数字、下划线、点、连字符。

- **Q：上传大文件报超时？**  
  A：可适当增加后端超时时间，或分批上传较小的文件。

- **Q：没有 Rerank API Key 怎么办？**  
  A：在 `.env` 中留空 `RERANK_API_KEY`，系统会自动降级为按初始距离排序。

- **Q：为什么没有删除数据库集合的功能？**  
  A：为数据安全考虑，删除数据库集合需要手动到后台删除。进入到python虚拟环境后（`source venv/bin/activate`）可以在项目根目录下运行下述指令(将your_collection_name替换为你想要删除的集合的名字)，该集合的物理文件和对应元数据都将被永久删除！
  ```bash
  python -m scripts.delete_collection your_collection_name
  ```

## 许可证

本项目遵循MIT LICENSE。
