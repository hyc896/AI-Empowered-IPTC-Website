# -*- coding: utf-8 -*-

"""
消息平台数据库实体定义
基于原PersonalAgent的消息相关实体，适配消息平台独立运行
"""

from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Integer, BigInteger, Float, Boolean, ForeignKey, Index, JSON, Enum
from sqlalchemy.orm import declarative_base, relationship
import enum

Base = declarative_base()


class MessageSource(Base):
    """消息源配置表"""
    __tablename__ = "mp_message_sources"

    id = Column(String(36), primary_key=True, comment="消息源ID（UUID）")
    name = Column(String(100), nullable=False, unique=True, comment="源名称")
    adapter_name = Column(String(100), nullable=False, comment="适配器名称")
    category = Column(String(50), comment="业务类别：news/wechat/rss等")
    display_name = Column(String(100), comment="显示名称")
    config = Column(JSON, comment="适配器配置（JSON格式）")
    schedule = Column(String(50), comment="定时任务cron表达式")
    is_active = Column(Boolean, default=True, comment="是否启用")
    last_crawled_at = Column(DateTime, comment="最后抓取时间")
    created_at = Column(DateTime, default=datetime.now, nullable=False, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False, comment="更新时间")

    # 关系
    external_messages = relationship("ExternalMessage", back_populates="source", cascade="all, delete-orphan")
    tonghuashun_messages = relationship("TongHuaShunMessage", back_populates="source", cascade="all, delete-orphan")
    kr36_messages = relationship("Kr36Message", back_populates="source", cascade="all, delete-orphan")
    arxiv_messages = relationship("ArxivMessage", back_populates="source", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_is_active", "is_active"),
        Index("idx_created_at", "created_at"),
        Index("idx_category", "category"),
    )


class ExternalMessage(Base):
    """外部消息表（通用表，未来可能弃用）"""
    __tablename__ = "mp_external_messages"

    id = Column(String(36), primary_key=True, comment="消息ID（UUID）")
    source_id = Column(String(36), ForeignKey("mp_message_sources.id", ondelete="CASCADE"), nullable=False, comment="来源ID")
    title = Column(String(500), nullable=False, comment="标题")
    content = Column(Text, nullable=False, comment="正文内容")
    summary = Column(Text, comment="摘要（LLM生成）")
    url = Column(String(255), unique=True, comment="原文链接")
    author = Column(String(200), comment="作者")
    published_at = Column(DateTime, comment="发布时间")
    crawled_at = Column(DateTime, default=datetime.now, nullable=False, comment="抓取时间")

    # 关系
    source = relationship("MessageSource", back_populates="external_messages")

    __table_args__ = (
        Index("idx_source_id", "source_id"),
        Index("idx_published_at", "published_at"),
        Index("idx_source_published", "source_id", "published_at"),
        Index("idx_crawled_at", "crawled_at"),
    )


class TongHuaShunMessage(Base):
    """同花顺7x24小时财经快讯表"""
    __tablename__ = "mp_tonghuashun_messages"

    id = Column(String(36), primary_key=True, comment="消息ID（UUID）")
    source_id = Column(String(36), ForeignKey("mp_message_sources.id", ondelete="CASCADE"), nullable=False, comment="来源ID")
    title = Column(String(500), nullable=False, comment="标题")
    content = Column(Text, nullable=False, comment="正文内容")
    summary = Column(Text, comment="摘要（<1000字用content，≥1000字LLM生成）")
    provider = Column(String(200), comment="信息提供方（来源）")
    published_at = Column(DateTime, comment="发布时间")
    url = Column(String(500), unique=True, comment="原文链接（用于去重）")
    image_url = Column(Text, comment="图片链接")
    crawled_at = Column(DateTime, default=datetime.now, nullable=False, comment="抓取时间")
    seq = Column(String(50), comment="同花顺序列号")
    tags = Column(JSON, comment="标签列表（JSON数组）")

    # 关系
    source = relationship("MessageSource", back_populates="tonghuashun_messages")

    __table_args__ = (
        Index("idx_source_id", "source_id"),
        Index("idx_published_at", "published_at"),
        Index("idx_source_published", "source_id", "published_at"),
        Index("idx_crawled_at", "crawled_at"),
        Index("idx_seq", "seq"),
        Index("idx_provider", "provider"),
        Index("idx_url", "url"),
    )


class Kr36Message(Base):
    """36氪快讯表"""
    __tablename__ = "mp_kr36_messages"

    id = Column(String(36), primary_key=True, comment="消息ID（UUID）")
    source_id = Column(String(36), ForeignKey("mp_message_sources.id", ondelete="CASCADE"), nullable=False, comment="来源ID")
    item_id = Column(String(50), unique=True, nullable=False, comment="36氪item_id（用于去重）")
    title = Column(String(500), nullable=False, comment="标题")
    content = Column(Text, nullable=False, comment="正文内容")
    summary = Column(Text, comment="摘要（直接使用content）")
    published_at = Column(DateTime, comment="发布时间")
    kr_route = Column(String(500), comment="36氪页面路由")
    source_url = Column(String(500), comment="原文链接")
    image_url = Column(Text, comment="图片链接")
    crawled_at = Column(DateTime, default=datetime.now, nullable=False, comment="抓取时间")
    comment_count = Column(Integer, default=0, comment="评论数")
    has_relevant = Column(Boolean, default=False, comment="是否相关")

    # 关系
    source = relationship("MessageSource", back_populates="kr36_messages")

    __table_args__ = (
        Index("idx_source_id", "source_id"),
        Index("idx_published_at", "published_at"),
        Index("idx_source_published", "source_id", "published_at"),
        Index("idx_crawled_at", "crawled_at"),
        Index("idx_item_id", "item_id"),
        Index("idx_source_url", "source_url"),
    )


class ArxivMessage(Base):
    """arXiv学术论文表"""
    __tablename__ = "mp_arxiv_messages"

    id = Column(String(36), primary_key=True, comment="消息ID（UUID）")
    source_id = Column(String(36), ForeignKey("mp_message_sources.id", ondelete="CASCADE"), nullable=False, comment="来源ID")
    arxiv_id = Column(String(50), unique=True, nullable=False, comment="arXiv ID（用于去重）")
    title = Column(String(500), nullable=False, comment="标题")
    content = Column(Text, nullable=False, comment="摘要（Abstract）")
    summary = Column(Text, nullable=False, comment="展示摘要（<1000字=content，>=1000字LLM生成）")
    provider = Column(Text, comment="所有作者逗号分隔（无作者时=Anonymous）")
    published_at = Column(DateTime, comment="发布时间")
    url = Column(String(500), unique=True, comment="论文详情页（用于去重）")
    primary_category = Column(String(50), comment="主分类")
    categories = Column(JSON, comment="所有分类数组")
    doi = Column(String(255), comment="DOI")
    journal_ref = Column(Text, comment="期刊引用")
    comment = Column(Text, comment="评论")
    updated_at = Column(DateTime, comment="更新时间")
    crawled_at = Column(DateTime, default=datetime.now, nullable=False, comment="抓取时间")

    # 关系
    source = relationship("MessageSource", back_populates="arxiv_messages")

    __table_args__ = (
        Index("idx_source_id", "source_id"),
        Index("idx_published_at", "published_at"),
        Index("idx_source_published", "source_id", "published_at"),
        Index("idx_crawled_at", "crawled_at"),
        Index("idx_arxiv_id", "arxiv_id"),
        Index("idx_primary_category", "primary_category"),
        Index("idx_doi", "doi"),
        Index("idx_updated_at", "updated_at"),
    )


# 数据库初始化函数
def init_database(engine):
    """初始化数据库表结构"""
    Base.metadata.create_all(bind=engine)
    print("消息平台数据库表初始化完成")


# 数据库表信息导出
def get_table_info():
    """获取所有表的信息"""
    tables = [
        {
            "name": "mp_message_sources",
            "description": "消息源配置表",
            "primary_key": "id",
            "foreign_keys": ["被所有消息表引用"]
        },
        {
            "name": "mp_external_messages",
            "description": "通用外部消息表",
            "primary_key": "id",
            "foreign_key": "source_id → mp_message_sources.id"
        },
        {
            "name": "mp_tonghuashun_messages",
            "description": "同花顺财经快讯表",
            "primary_key": "id",
            "unique_key": "url",
            "foreign_key": "source_id → mp_message_sources.id"
        },
        {
            "name": "mp_kr36_messages",
            "description": "36氪快讯表",
            "primary_key": "id",
            "unique_key": "item_id",
            "foreign_key": "source_id → mp_message_sources.id"
        },
        {
            "name": "mp_arxiv_messages",
            "description": "arXiv学术论文表",
            "primary_key": "id",
            "unique_key": "arxiv_id",
            "foreign_key": "source_id → mp_message_sources.id"
        }
    ]

    return tables