# -*- coding: utf-8 -*-

"""
消息平台数据库实体定义
定义所有数据库表结构和ORM映射
"""

from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Integer, BigInteger, Float, Boolean, ForeignKey, Index, JSON, Enum
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.ext.hybrid import hybrid_property
import enum

Base = declarative_base()


"""
===================================================================================
消息源表统一字段标准（所有新建消息表必须遵循此结构）
===================================================================================

核心必备字段（不准增删改）：

class StandardMessageTable(Base):
    __tablename__ = "mp_{source_name}_messages"

    # 核心必备字段
    id = Column(String(36), primary_key=True, comment="消息ID（UUID）")
    source_id = Column(String(36), ForeignKey("mp_message_sources.id", ondelete="CASCADE"), nullable=False, comment="来源ID")
    external_id = Column(String(100), comment="外部唯一标识（post_id/article_id/event_id等）")
    title = Column(String(500), nullable=False, comment="标题")
    content = Column(Text, nullable=False, comment="正文内容")
    summary = Column(Text, comment="摘要（优先从网页提取，无则用content，content>1000字时取前1000字）")
    provider = Column(String(500), comment="作者或信息提供方（多个用逗号分隔）")
    published_at = Column(DateTime, comment="发布时间")
    crawled_at = Column(DateTime, default=datetime.now, nullable=False, comment="抓取时间")
    url = Column(String(500), unique=True, nullable=False, comment="原文链接（用于去重）")

    # 扩展字段（可选，根据业务需求添加）
    region = Column(String(50), comment="地区（US/EU/UK/GLOBAL等）")
    category = Column(String(100), comment="分类")
    language = Column(String(10), comment="语言（en/zh/fr等）")
    tags = Column(JSON, comment="标签列表（JSON数组）")
    extra_metadata = Column("metadata", JSON, comment="其他元数据（JSON对象，注意：属性名为extra_metadata）")

    # 关系
    source = relationship("MessageSource", back_populates="{source_name}_messages")

    # 索引（强制要求）
    __table_args__ = (
        Index("idx_source_id", "source_id"),
        Index("idx_published_at", "published_at"),
        Index("idx_crawled_at", "crawled_at"),
        Index("idx_source_published", "source_id", "published_at"),
        Index("idx_url", "url"),
        Index("idx_external_id", "external_id"),
    )

字段映射规则：
- 网页的post_id/article_id/event_id → 数据库的external_id
- 网页的authors/author/by → 数据库的provider（逗号分隔）
- 网页的permalink/link/href → 数据库的url
- 网页的excerpt/abstract/description → 数据库的summary或content

禁止字段：
- 不准添加image_url字段
- 不准使用source_url命名（统一用url）
- 不准使用author命名（统一用provider）
- 不准使用seq/item_id/arxiv_id等（统一用external_id）

旧表（同花顺、Kr36、arXiv）保持现状不动，仅供参考。
===================================================================================
"""


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
    tonghuashun_messages = relationship("TongHuaShunMessage", back_populates="source", cascade="all, delete-orphan")
    kr36_messages = relationship("Kr36Message", back_populates="source", cascade="all, delete-orphan")
    arxiv_messages = relationship("ArxivMessage", back_populates="source", cascade="all, delete-orphan")
    partnership_ai_messages = relationship("PartnershipAIMessage", back_populates="source", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_is_active", "is_active"),
        Index("idx_created_at", "created_at"),
        Index("idx_category", "category"),
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

    # 统一的外部ID访问接口（映射到seq字段，用于代码层面统一）
    @hybrid_property
    def external_id(self):
        """外部唯一标识（映射到seq字段）"""
        return self.seq

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

    # 统一的外部ID访问接口（映射到item_id字段，用于代码层面统一）
    @hybrid_property
    def external_id(self):
        """外部唯一标识（映射到item_id字段）"""
        return self.item_id

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

    # 统一的外部ID访问接口（映射到arxiv_id字段，用于代码层面统一）
    @hybrid_property
    def external_id(self):
        """外部唯一标识（映射到arxiv_id字段）"""
        return self.arxiv_id

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


class PartnershipAIMessage(Base):
    """Partnership on AI消息表（2025统一字段标准）"""
    __tablename__ = "mp_partnership_ai_messages"

    # 核心必备字段（遵循2025统一标准）
    id = Column(String(36), primary_key=True, comment="消息ID（UUID）")
    source_id = Column(String(36), ForeignKey("mp_message_sources.id", ondelete="CASCADE"), nullable=False, comment="来源ID")
    external_id = Column(String(200), comment="外部唯一标识（文章slug）")
    title = Column(String(500), nullable=False, comment="标题")
    content = Column(Text, nullable=False, comment="正文内容")
    summary = Column(Text, comment="摘要（优先从网页提取，无则用content，content>1000字时取前1000字）")
    provider = Column(String(500), comment="作者或信息提供方（多个用逗号分隔）")
    published_at = Column(DateTime, comment="发布时间")
    crawled_at = Column(DateTime, default=datetime.now, nullable=False, comment="抓取时间")
    url = Column(String(500), unique=True, nullable=False, comment="原文链接（用于去重）")

    # 扩展字段
    region = Column(String(50), comment="地区（US/EU/UK/GLOBAL等）")
    category = Column(String(100), comment="分类（AI Governance/Policy/Research等）")
    language = Column(String(10), comment="语言（en/zh/fr等）")
    tags = Column(JSON, comment="标签列表（JSON数组）")
    extra_metadata = Column("metadata", JSON, comment="其他元数据（JSON对象）")

    # 关系
    source = relationship("MessageSource", back_populates="partnership_ai_messages")

    __table_args__ = (
        Index("idx_source_id", "source_id"),
        Index("idx_published_at", "published_at"),
        Index("idx_crawled_at", "crawled_at"),
        Index("idx_source_published", "source_id", "published_at"),
        Index("idx_url", "url"),
        Index("idx_external_id", "external_id"),
        Index("idx_region", "region"),
        Index("idx_category", "category"),
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