# -*- coding: utf-8 -*-

"""
消息平台主入口文件
提供独立的消息采集、存储、检索服务
"""

import asyncio
import logging
import sys
import os
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

# 导入搜索请求模型
try:
    from backend.api.schemas import SearchRequest
except ImportError:
    # 如果导入失败，创建一个简化版本
    class SearchRequest(BaseModel):
        query: str
        source_type: str = "news"
        limit: int = 20

# 添加项目路径 - 只使用消息平台自己的路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))  # 消息平台根目录

# 配置日志（支持环境变量和配置文件）
log_file = os.getenv('LOG_FILE', 'logs/platform.log')  # 可通过环境变量自定义
os.makedirs(os.path.dirname(log_file), exist_ok=True)  # 确保日志目录存在

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_file, encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# 降低第三方库日志级别，减少噪音
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('chromadb').setLevel(logging.WARNING)
logging.getLogger('chromadb.telemetry.product.posthog').setLevel(logging.ERROR)
logging.getLogger('arxiv').setLevel(logging.WARNING)

class SearchRequest(BaseModel):
    """搜索请求模型"""
    query: str
    source_type: str = "news"
    limit: int = 20


# 全局变量
app_state: Dict[str, Any] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    await startup()
    yield
    # 关闭时清理
    await shutdown()


async def startup():
    """应用启动初始化"""
    logger.info("=== 消息平台启动中 ===")

    try:
        # 1. 初始化配置
        logger.info("【1/7】加载配置...")
        await init_config()

        # 2. 初始化数据库
        logger.info("【2/7】初始化数据库...")
        await init_database()

        # 2.5. 启动配置验证（新增）
        logger.info("【3/7】验证配置完整性...")
        import os
        skip_validation = os.getenv('SKIP_VALIDATION', '0') == '1'

        if not skip_validation:
            from backend.database.startup_validator import startup_validation
            startup_validation(fail_on_error=True)
        else:
            logger.warning("⚠️  跳过启动验证（SKIP_VALIDATION=1）")

        # 3. 初始化存储
        logger.info("【4/7】初始化向量存储...")
        await init_storage()

        # 4. 初始化LLM和Embedding客户端
        logger.info("【5/7】初始化LLM客户端...")
        await init_llm()

        # 5. 启动采集器服务
        logger.info("【6/7】启动采集器服务...")
        await start_collector_service()

        # 5.5. 启动向量同步检查（后台任务）
        try:
            from backend.services.message.vector_sync import startup_vector_sync

            config = app_state.get("config", {})
            vector_sync_config = config.get("vector_sync", {})

            if vector_sync_config.get("enabled", True):
                full_sync = (vector_sync_config.get("mode", "full") == "full")
                logger.info(f"【向量同步】后台任务启动 ({'全量' if full_sync else '增量'}模式)")
                asyncio.create_task(startup_vector_sync(full_sync=full_sync))
            else:
                logger.info("【向量同步】已禁用")

        except Exception as e:
            logger.warning(f"【向量同步】启动失败: {e}，将继续运行但无法自动同步向量")

        # 6. 加载完整的API路由
        logger.info("【7/7】加载API路由...")
        load_api_routes()
        setup_basic_routes()

        # 7. 显示数据库数据统计
        await display_database_stats()

        logger.info("=== 消息平台启动完成 ===")
        app_state["status"] = "running"
        app_state["startup_time"] = asyncio.get_event_loop().time()

    except Exception as e:
        logger.error(f"【启动失败】消息平台启动失败: {e}")
        app_state["status"] = "failed"
        app_state["error"] = str(e)
        raise


async def shutdown():
    """应用关闭清理"""
    logger.info("=== 消息平台正在关闭 ===")

    try:
        # 停止采集器服务
        if "collector_service" in app_state:
            logger.info("【关闭】正在停止采集器服务...")
            await app_state["collector_service"].stop()

        # 关闭数据库连接
        if "db_config" in app_state:
            logger.info("【关闭】数据库配置已清理")

        # 关闭存储连接
        if "storage" in app_state:
            logger.info("【关闭】正在关闭存储连接...")
            # ChromaDB会自动关闭

        logger.info("=== 消息平台已停止 ===")

    except Exception as e:
        logger.error(f"【关闭失败】清理过程失败: {e}")


async def init_config():
    """初始化配置"""
    try:
        # 使用ConfigManager加载配置，确保环境变量正确替换
        from backend.config.config_manager import ConfigManager
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.yaml')

        config_manager = ConfigManager()
        success = config_manager.load_config(config_path)

        if not success:
            raise Exception("Failed to load configuration")

        config_data = config_manager.get_config()
        app_state["config"] = config_data
        logger.info("✓ 配置加载成功")

    except Exception as e:
        logger.error(f"✗ 配置加载失败: {e}")
        raise


async def init_database():
    """初始化数据库"""
    try:
        # 使用SQLAlchemy测试数据库连接
        from backend.database.connection import init_database, get_database_config

        # 初始化数据库连接
        success = init_database()
        if not success:
            raise Exception("数据库连接初始化失败")

        config = get_database_config()
        app_state["db_config"] = config
        logger.info(f"✓ 数据库连接成功: {config['database']}")

    except Exception as e:
        logger.error(f"✗ 数据库初始化失败: {e}")
        raise


async def init_storage():
    """初始化存储"""
    try:
        # 初始化ChromaDB向量存储
        logger.info("【存储初始化】正在初始化ChromaDB向量数据库...")
        from backend.storage import initialize_chromadb, get_chromadb_storage

        # 从配置中获取ChromaDB配置
        config = app_state.get("config", {})
        chromadb_config = config.get("database", {}).get("chromadb", {})

        if chromadb_config:
            logger.info(f"【存储初始化】ChromaDB配置: {chromadb_config}")
            result = initialize_chromadb(chromadb_config)

            if result:
                app_state["storage"] = get_chromadb_storage()
                logger.info("存储初始化成功")
            else:
                logger.error("ChromaDB初始化失败")
                raise Exception("ChromaDB initialization failed")
        else:
            logger.error("未找到ChromaDB配置")
            raise Exception("ChromaDB configuration not found")

    except Exception as e:
        logger.error(f"存储初始化失败: {e}")
        raise


async def init_llm():
    """初始化Embedding和Fast LLM客户端（消息平台不需要Chat主模型）"""
    try:
        from backend.llm.global_llm_manager import GlobalLLMManager

        # 从配置中获取LLM设置
        config = app_state["config"]
        llm_config = config.get("llm", {})

        if not llm_config:
            logger.info("LLM配置为空，跳过初始化")
            return

        # 消息平台只需要embedding和fast客户端，不需要chat主模型
        embedding_config = llm_config.get("embedding", {})
        fast_config = llm_config.get("fast", {})

        # 初始化GlobalLLMManager
        llm_manager = GlobalLLMManager.get_instance()
        llm_manager.initialize(
            chat_config=None,  # 消息平台不需要Chat主模型
            embedding_config=embedding_config,
            fast_config=fast_config
        )

        app_state["llm_manager"] = llm_manager

        # 记录初始化成功的客户端（显示完整配置信息）
        logger.info("LLM客户端初始化成功:")
        if embedding_config:
            logger.info(f"  Embedding: {embedding_config.get('model')} @ {embedding_config.get('base_url')}")
        if fast_config:
            logger.info(f"  Fast: {fast_config.get('model')} @ {fast_config.get('base_url')}")
            logger.info(f"  Fast模型用途: arXiv论文摘要翻译")

    except Exception as e:
        logger.error(f"LLM初始化失败: {e}")
        # 不抛出异常，允许平台在没有LLM的情况下运行
        logger.warning("消息平台将在没有LLM功能的情况下运行")


async def start_collector_service():
    """启动采集器服务"""
    try:
        from backend.services.collector_service import collector_service

        await collector_service.start()
        app_state["collector_service"] = collector_service

        logger.info("采集器服务启动成功")

    except Exception as e:
        logger.error(f"采集器服务启动失败: {e}")
        raise


def setup_basic_routes():
    """设置基础路由"""
    try:
        @app.get("/health")
        async def health():
            return {
                "status": "healthy",
                "service": "message_platform",
                "database": "connected" if "db_config" in app_state else "disconnected"
            }

        @app.get("/api/v1/test")
        async def test():
            return {"message": "消息平台运行正常"}

    
        logger.info("【启动】基础路由设置完成")

    except Exception as e:
        logger.error(f"基础路由设置失败: {e}")
        raise


def load_api_routes():
    """加载API路由"""
    try:
        from backend.api.search_routes import router as search_router

        try:
            from backend.api.source_routes import router as source_router
            app.include_router(source_router, prefix="/api/v1")
        except ImportError as e:
            logger.warning(f"源管理路由加载失败: {e}")

        try:
            from backend.api.collector_routes import router as collector_router
            app.include_router(collector_router, prefix="/api/v1")
        except ImportError as e:
            logger.warning(f"采集器路由加载失败: {e}")

        try:
            from backend.api.stats_routes import router as stats_router
            app.include_router(stats_router, prefix="/api/v1")
        except ImportError as e:
            logger.warning(f"统计路由加载失败: {e}")

        app.include_router(search_router, prefix="/api/v1")

        logger.info("API路由加载成功")

    except Exception as e:
        logger.error(f"API路由加载失败: {e}")
        raise


# 创建FastAPI应用
app = FastAPI(
    title="消息平台API",
    description="个人Agent消息采集与检索平台",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count"],  # 暴露自定义响应头给前端
)


# 健康检查端点
@app.get("/health")
async def health_check():
    """健康检查"""
    try:
        collector_status = None
        if "collector_service" in app_state:
            collector_status = await app_state["collector_service"].health_check()

        # 数据库健康检查
        db_health = await health_check_database()

        status = "healthy"
        if db_health.get("status") != "healthy":
            status = "degraded"
        if collector_status and collector_status.get("status") == "stopped":
            status = "partial"

        uptime = None
        if "startup_time" in app_state:
            uptime = asyncio.get_event_loop().time() - app_state["startup_time"]

        return {
            "status": status,
            "timestamp": asyncio.get_event_loop().time(),
            "uptime_seconds": uptime,
            "database": db_health,
            "collectors": collector_status
        }

    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": asyncio.get_event_loop().time()
        }


async def health_check_database() -> Dict[str, Any]:
    """数据库健康检查"""
    try:
        from backend.database.connection import check_database_connection, create_session
        from backend.database.entities import MessageSource

        is_connected = check_database_connection()
        if not is_connected:
            return {
                "status": "disconnected",
                "error": "数据库连接失败"
            }

        with create_session() as session:
            source_count = session.query(MessageSource).count()

        return {
            "status": "healthy",
            "sources_count": source_count
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


# 根路径
@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "消息平台API服务",
        "version": "1.0.0",
        "status": app_state.get("status", "unknown"),
        "docs_url": "/docs",
        "health_url": "/health"
    }


# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理器"""
    logger.error(f"未处理的异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "内部服务器错误",
            "message": str(exc),
            "type": type(exc).__name__
        }
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP异常处理器"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code
        }
    )


async def display_database_stats():
    """显示数据库数据统计信息"""
    logger.info("=== 数据库数据统计 ===")

    # 统计MySQL数据库（配置驱动，零硬编码）
    try:
        from backend.database.connection import create_session
        from backend.database.entities import MessageSource
        from backend.database.orm_registry import get_orm_registry
        from sqlalchemy.exc import OperationalError

        with create_session() as session:
            logger.info("【MySQL数据库】")

            # 统计消息源配置表
            try:
                sources_count = session.query(MessageSource).count()
                logger.info(f"  消息源配置 (mp_message_sources): {sources_count} 条")
            except OperationalError as e:
                if "doesn't exist" in str(e):
                    logger.warning(f"  消息源配置表 (mp_message_sources): 不存在")
                    sources_count = 0
                else:
                    raise

            # 动态统计所有消息表（使用ORM Registry，自动支持新增消息源）
            total_messages = 0
            registry = get_orm_registry()
            sources = session.query(MessageSource).filter(MessageSource.is_active == True).all()

            for source in sources:
                source_config = source.config or {}
                mysql_table = source_config.get('mysql_table')

                if not mysql_table:
                    continue

                model = registry.get_model(mysql_table)
                if model:
                    try:
                        count = session.query(model).count()
                        total_messages += count
                        logger.info(f"  {source.display_name} ({mysql_table}): {count} 条")
                    except OperationalError as e:
                        if "doesn't exist" in str(e):
                            logger.warning(f"  {source.display_name} ({mysql_table}): 表不存在")
                        else:
                            logger.error(f"  {source.display_name} ({mysql_table}): 统计失败 - {e}")
                else:
                    logger.warning(f"  {source.display_name} ({mysql_table}): 未找到ORM模型")

            logger.info(f"  MySQL总计: {total_messages} 条记录")

    except Exception as e:
        logger.error(f"【MySQL统计失败】{e}")

    # 统计ChromaDB向量数据库
    try:
        storage = app_state.get("storage")
        if storage and hasattr(storage, 'count'):
            logger.info("【ChromaDB向量数据库】")

            # 从数据库动态读取所有激活消息源的collection配置
            with create_session() as db:
                sources = db.query(MessageSource).filter(MessageSource.is_active == True).all()

                total_chromadb = 0
                for source in sources:
                    collection_name = source.config.get('chroma_collection') if source.config else None
                    if collection_name:
                        try:
                            count = storage.count(collection_name)
                            total_chromadb += count
                            logger.info(f"  {source.display_name} ({collection_name}): {count} 条")
                        except Exception as e:
                            logger.warning(f"  {source.display_name} ({collection_name}): 统计失败 - {e}")

                logger.info(f"  ChromaDB总计: {total_chromadb} 条向量")

            # 获取集合详情（调试用）
            if hasattr(storage, '_collections'):
                logger.info("  Collections详情:")
                for name, collection in storage._collections.items():
                    try:
                        count = collection.count()
                        logger.info(f"    {name}: {count} 条向量")
                    except Exception as e:
                        logger.warning(f"    {name}: 获取失败 - {e}")
        else:
            logger.warning("【ChromaDB统计】存储未初始化或不支持统计功能")

    except Exception as e:
        logger.error(f"【ChromaDB统计失败】{e}")

    logger.info("======================")


# 开发模式启动
if __name__ == "__main__":
    # 确保日志目录存在
    os.makedirs("logs", exist_ok=True)

    # 获取配置
    try:
        from backend.config.config_manager import ConfigManager
        config_manager = ConfigManager()
        config_manager.load_config("config.yaml")
        config = config_manager.get_config()

        web_config = config.get("web", {})

        host = web_config.get("host", "0.0.0.0")
        port = web_config.get("port", 11528)
        workers = web_config.get("workers", 1)
        reload = web_config.get("reload", False)
        log_level = "info"  # 固定日志级别

    except Exception as e:
        logger.warning(f"配置加载失败，使用默认配置: {e}")
        host = "0.0.0.0"
        port = 11528
        workers = 1
        reload = False
        log_level = "info"

    logger.info(f"启动消息平台服务: http://{host}:{port}")
    logger.info(f"API文档: http://{host}:{port}/docs")
    logger.info(f"健康检查: http://{host}:{port}/health")

    # 启动服务
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        workers=workers,
        reload=reload,
        log_level=log_level,
        access_log=True
    )