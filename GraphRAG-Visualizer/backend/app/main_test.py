"""
简化版主应用 - 用于测试基本功能
不需要 Neo4j 连接
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html

from app.config import settings
from app.routers import upload

# 创建 FastAPI 应用（禁用默认文档）
app = FastAPI(
    title=settings.APP_NAME + " (测试模式)",
    version=settings.APP_VERSION,
    description="测试模式 - 仅包含 PDF 上传功能",
    docs_url=None,  # 禁用默认文档
    redoc_url=None  # 禁用默认 ReDoc
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 仅注册上传路由
app.include_router(upload.router, prefix=settings.API_PREFIX)


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "GraphRAG Visualizer API (测试模式)",
        "version": settings.APP_VERSION,
        "mode": "test",
        "docs": "/docs",
        "note": "此版本仅包含 PDF 上传功能，不需要 Neo4j"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "mode": "test"}


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui():
    """自定义 Swagger UI - 使用国内 CDN"""
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " - API 文档",
        swagger_js_url="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css",
    )


@app.get("/redoc", include_in_schema=False)
async def redoc_html():
    """ReDoc 文档"""
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=app.title + " - ReDoc",
        redoc_js_url="https://unpkg.com/redoc@next/bundles/redoc.standalone.js",
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
