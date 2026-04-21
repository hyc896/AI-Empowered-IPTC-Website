# -*- coding: utf-8 -*-

"""
逐光智慧思政平台 - 后端主入口
"""

import logging
import traceback
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
logger = logging.getLogger(__name__)

# 导入路由
from api import auth_routes, knowledge_routes, practice_routes, submission_routes, review_routes, venue_routes, annotation_routes

# 导入数据库初始化
from database.connection import init_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    init_database()
    yield


# 创建FastAPI应用
app = FastAPI(
    title="逐光智慧思政平台API",
    description="思政课理论与实践一体化平台",
    version="1.0.0",
    lifespan=lifespan
)


# 全局异常处理 - 打印完整堆栈到终端
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"未捕获异常 {request.method} {request.url.path}:")
    logger.error(traceback.format_exc())
    return JSONResponse(status_code=500, content={"detail": str(exc)})

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth_routes.router, prefix="/api/v1/auth", tags=["认证"])
app.include_router(knowledge_routes.router, prefix="/api/v1/knowledge-points", tags=["知识点"])
app.include_router(practice_routes.router, prefix="/api/v1/practice", tags=["实践方案"])
app.include_router(submission_routes.router, prefix="/api/v1/submissions", tags=["实践提交"])
app.include_router(review_routes.router, prefix="/api/v1/reviews", tags=["审核管理"])
app.include_router(venue_routes.router, prefix="/api/v1/venues", tags=["场馆"])
app.include_router(annotation_routes.router, prefix="/api/v1/annotations", tags=["批注"])


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "逐光智慧思政平台API",
        "version": "1.0.0",
        "docs_url": "/docs"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}


# 挂载静态文件服务（上传的图片、视频、音频等）
upload_dir = os.path.join(os.path.dirname(__file__), "data", "uploads")
os.makedirs(upload_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=upload_dir), name="uploads")


if __name__ == "__main__":
    import uvicorn
    import logging
    logging.basicConfig(level=logging.INFO)
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True, reload_delay=2)
