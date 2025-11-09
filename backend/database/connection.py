# -*- coding: utf-8 -*-

"""
消息平台数据库连接管理
独立于PersonalAgent项目的数据库连接
"""

import os
import sys
import logging
from typing import Generator, Optional
from contextlib import contextmanager
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base

# 消息平台完全独立，不再依赖PersonalAgent配置
_config_available = False

logger = logging.getLogger(__name__)

# 全局变量
_engine: Optional = None
_session_factory: Optional = None


def get_database_config() -> dict:
    """获取数据库配置"""
    if _config_available:
        global_config = GlobalConfig.get_instance()

        # 优先使用消息平台专用配置，否则使用原项目配置
        platform_config = global_config.get_config("database.mysql", {})

        # 如果没有指定数据库，默认使用message_platform
        if not platform_config.get("database"):
            platform_config["database"] = "message_platform"

        return platform_config
    else:
        # 使用默认配置
        return {
            "host": "localhost",
            "port": 3306,
            "user": "root",
            "password": "123456",
            "database": "message_platform",
            "charset": "utf8mb4",
            "echo": False,
            "pool_size": 20,
            "max_overflow": 30,
            "pool_timeout": 30,
            "pool_recycle": 3600
        }


def init_database() -> bool:
    """
    初始化数据库连接

    Returns:
        初始化是否成功
    """
    global _engine, _session_factory

    try:
        config = get_database_config()

        # 构建数据库URL
        database_url = (
            f"mysql+pymysql://{config['user']}:{config['password']}"
            f"@{config['host']}:{config['port']}/{config['database']}"
            f"?charset={config.get('charset', 'utf8mb4')}"
        )

        # 创建引擎
        engine_kwargs = {
            "echo": config.get("echo", False),
            "pool_size": config.get("pool_size", 20),
            "max_overflow": config.get("max_overflow", 30),
            "pool_timeout": config.get("pool_timeout", 30),
            "pool_recycle": config.get("pool_recycle", 3600),
            "pool_pre_ping": True,
        }

        _engine = create_engine(database_url, **engine_kwargs)

        # 创建会话工厂
        _session_factory = sessionmaker(
            bind=_engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False
        )

        # 测试连接
        with _engine.connect() as conn:
            from sqlalchemy import text
            conn.execute(text("SELECT 1"))

        # 创建数据库表结构
        from .entities import Base, init_database as create_tables
        create_tables(_engine)

        logger.info(f"消息平台数据库连接初始化成功: {config['database']}")
        return True

    except Exception as e:
        logger.error(f"消息平台数据库连接初始化失败: {e}")
        return False


def get_engine():
    """获取数据库引擎"""
    global _engine
    if _engine is None:
        if not init_database():
            raise Exception("数据库引擎初始化失败")
    return _engine


def get_session_factory():
    """获取会话工厂"""
    global _session_factory
    if _session_factory is None:
        init_database()
    return _session_factory


@contextmanager
def create_session() -> Generator[Session, None, None]:
    """
    创建数据库会话的上下文管理器

    Yields:
        Session: 数据库会话对象
    """
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"数据库会话异常: {e}")
        raise
    finally:
        session.close()


def get_db_session() -> Generator[Session, None, None]:
    """
    获取数据库会话（FastAPI兼容）

    Yields:
        Session: 数据库会话对象
    """
    with create_session() as session:
        yield session


def close_database():
    """关闭数据库连接"""
    global _engine, _session_factory

    try:
        if _engine:
            _engine.dispose()
            _engine = None
        _session_factory = None
        logger.info("消息平台数据库连接已关闭")
    except Exception as e:
        logger.error(f"关闭数据库连接失败: {e}")


def check_database_connection() -> bool:
    """
    检查数据库连接是否正常

    Returns:
        连接是否正常
    """
    try:
        engine = get_engine()
        with engine.connect() as conn:
            from sqlalchemy import text
            result = conn.execute(text("SELECT 1 as test"))
            return result.fetchone()[0] == 1
    except Exception as e:
        logger.error(f"数据库连接检查失败: {e}")
        return False


def get_database_info() -> dict:
    """
    获取数据库信息

    Returns:
        数据库信息字典
    """
    try:
        config = get_database_config()
        engine = get_engine()

        with engine.connect() as conn:
            from sqlalchemy import text

            # 获取数据库版本
            version_result = conn.execute(text("SELECT VERSION() as version"))
            version = version_result.fetchone()[0]

            # 获取表信息
            tables_result = conn.execute(text("""
                SELECT table_name, table_rows, data_length, index_length
                FROM information_schema.tables
                WHERE table_schema = :database AND table_name LIKE 'mp_%'
                ORDER BY data_length DESC
            """), {"database": config["database"]})

            tables = []
            total_size = 0
            total_rows = 0

            for row in tables_result:
                table_info = {
                    "name": row[0],
                    "rows": row[1] or 0,
                    "data_size": row[2] or 0,
                    "index_size": row[3] or 0,
                    "total_size": (row[2] or 0) + (row[3] or 0)
                }
                tables.append(table_info)
                total_size += table_info["total_size"]
                total_rows += table_info["rows"]

            return {
                "database": config["database"],
                "host": config["host"],
                "port": config["port"],
                "version": version,
                "tables": tables,
                "total_tables": len(tables),
                "total_rows": total_rows,
                "total_size": total_size,
                "connection_status": "connected"
            }

    except Exception as e:
        logger.error(f"获取数据库信息失败: {e}")
        return {
            "connection_status": "disconnected",
            "error": str(e)
        }


# 向后兼容的别名
MessageSource = None
ExternalMessage = None
TongHuaShunMessage = None
Kr36Message = None
ArxivMessage = None


def import_entities():
    """导入实体类（延迟导入避免循环依赖）"""
    global MessageSource, ExternalMessage, TongHuaShunMessage, Kr36Message, ArxivMessage

    try:
        from .entities import (
            MessageSource as _MessageSource,
            ExternalMessage as _ExternalMessage,
            TongHuaShunMessage as _TongHuaShunMessage,
            Kr36Message as _Kr36Message,
            ArxivMessage as _ArxivMessage
        )

        MessageSource = _MessageSource
        ExternalMessage = _ExternalMessage
        TongHuaShunMessage = _TongHuaShunMessage
        Kr36Message = _Kr36Message
        ArxivMessage = _ArxivMessage

    except ImportError as e:
        logger.error(f"导入实体类失败: {e}")


# 在模块加载时导入实体类
import_entities()


# 数据库健康检查
async def health_check() -> dict:
    """
    数据库健康检查

    Returns:
        健康检查结果
    """
    try:
        # 检查连接
        is_connected = check_database_connection()

        if not is_connected:
            return {
                "status": "unhealthy",
                "database": "disconnected",
                "timestamp": None,
                "response_time": None
            }

        # 测试查询性能
        import time
        start_time = time.time()

        with create_session() as session:
            # 简单查询测试
            result = session.execute("SELECT COUNT(*) FROM mp_message_sources")
            source_count = result.fetchone()[0]

        response_time = (time.time() - start_time) * 1000  # 转换为毫秒

        return {
            "status": "healthy",
            "database": "connected",
            "sources_count": source_count,
            "timestamp": time.time(),
            "response_time_ms": round(response_time, 2)
        }

    except Exception as e:
        logger.error(f"数据库健康检查失败: {e}")
        return {
            "status": "unhealthy",
            "database": "error",
            "error": str(e),
            "timestamp": time.time(),
            "response_time": None
        }


if __name__ == "__main__":
    # 测试数据库连接
    print("测试消息平台数据库连接...")

    if init_database():
        print("✅ 数据库连接成功")

        # 显示数据库信息
        info = get_database_info()
        print(f"数据库: {info.get('database')}")
        print(f"版本: {info.get('version')}")
        print(f"表数量: {info.get('total_tables', 0)}")
        print(f"总记录数: {info.get('total_rows', 0)}")

        # 健康检查
        import asyncio
        health = asyncio.run(health_check())
        print(f"健康状态: {health.get('status')}")
        print(f"响应时间: {health.get('response_time_ms')}ms")

    else:
        print("❌ 数据库连接失败")