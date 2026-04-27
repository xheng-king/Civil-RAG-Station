# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.api import api_router
import os

# 计算前端目录的绝对路径（项目根目录下的 frontend 文件夹）
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")

app = FastAPI(
    title="RAG Knowledge Base API",
    description="基于 ChromaDB 和 Qwen 的文档检索增强生成系统",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS 配置（允许前端跨域，此处虽同源但保留）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册 API 路由（所有 API 路径以 /api 开头）
app.include_router(api_router)

# 将前端静态文件挂载到根路径（html=True 会自动返回 index.html）
app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

# 健康检查端点（可选，因为根路径已被前端占用，改用 /health）
@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy"}

# 如果需要保留根路径的 API 信息，可以注释掉上面的挂载，
# 但根据方案一，前端应直接展示，因此不再提供根路径的 JSON 响应。

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)