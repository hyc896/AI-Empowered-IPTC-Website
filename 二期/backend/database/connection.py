# -*- coding: utf-8 -*-

"""
数据库连接配置
"""

import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool
from dotenv import load_dotenv

# 加载环境变量（从项目根目录的config/.env）
project_root = Path(__file__).parent.parent.parent
env_path = project_root / "config" / ".env"
load_dotenv(env_path)

# 数据库URL
DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://root:password@localhost:3306/iptc_practice")

# 创建数据库引擎
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=False
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基类
Base = declarative_base()


def init_database():
    """初始化数据库（创建所有表）"""
    from database.entities import User, KnowledgePoint, PracticePlan, Venue, PracticeSubmission, PracticeReview
    Base.metadata.create_all(bind=engine)
    print("✓ 数据库表创建成功")


def get_db():
    """获取数据库会话（依赖注入）"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
