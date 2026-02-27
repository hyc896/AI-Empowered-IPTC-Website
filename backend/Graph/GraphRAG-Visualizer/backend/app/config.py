"""
配置管理模块
负责加载和管理应用配置
"""
import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# 加载 .env 文件
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


class Settings(BaseSettings):
    """应用配置类"""

    # 应用基础配置
    APP_NAME: str = "GraphRAG Visualizer"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # API 配置
    API_PREFIX: str = "/api"
    CORS_ORIGINS: list = ["http://localhost:5173", "http://localhost:3000"]

    # 文件上传配置
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS: set = {".pdf", ".docx", ".doc", ".epub", ".txt"}

    # 分页配置
    DEFAULT_PAGE_RANGE: int = 20  # 默认每次处理 20 页

    # GraphRAG 配置文件路径
    GRAPHRAG_CONFIG_PATH: str = str(Path(__file__).parent.parent.parent.parent / "GraphRAG" / "config" / "default_config.yaml")

    # 历史记录存储路径
    HISTORY_STORAGE_PATH: str = "storage/history.json"

    # Neo4j 配置（从环境变量读取）
    NEO4J_URI: Optional[str] = None
    NEO4J_USER: Optional[str] = None
    NEO4J_PASSWORD: Optional[str] = None
    NEO4J_DATABASE: Optional[str] = None

    # LLM 配置（从环境变量读取）
    LLM_API_KEY: Optional[str] = None
    LLM_BASE_URL: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"  # 允许额外的字段


# 创建全局配置实例
settings = Settings()

# 确保必要的目录存在
Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
Path(settings.HISTORY_STORAGE_PATH).parent.mkdir(parents=True, exist_ok=True)
