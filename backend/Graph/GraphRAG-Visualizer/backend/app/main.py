"""
FastAPI 主应用
GraphRAG 可视化应用后端服务
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.routers import upload, extract, graph, config
from app.services.graphrag_service import GraphRAGService


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化 GraphRAG 服务
    graphrag_service = GraphRAGService()
    try:
        await graphrag_service.initialize(settings.GRAPHRAG_CONFIG_PATH)
        print("[INFO] GraphRAG 服务已初始化")
    except Exception as e:
        print(f"[WARNING] GraphRAG 服务初始化失败: {e}")
        print("[WARNING] 服务将继续运行，但 GraphRAG 功能可能不可用")
        print("[WARNING] 请检查 Neo4j 配置和 .env 文件")

    yield

    # 关闭时清理资源
    try:
        await graphrag_service.close()
        print("[INFO] GraphRAG 服务已关闭")
    except Exception as e:
        print(f"[WARNING] GraphRAG 服务关闭时出错: {e}")


# 创建 FastAPI 应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(upload.router, prefix=settings.API_PREFIX)
app.include_router(extract.router, prefix=settings.API_PREFIX)
app.include_router(graph.router, prefix=settings.API_PREFIX)
app.include_router(config.router, prefix=settings.API_PREFIX)


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "GraphRAG Visualizer API",
        "version": settings.APP_VERSION,
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
