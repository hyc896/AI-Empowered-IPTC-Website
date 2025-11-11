# -*- coding: utf-8 -*-

"""
RAND Corporation Message ORM Entity
兰德公司AI研究消息表
"""

from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Index, JSON, ForeignKey
from sqlalchemy.orm import relationship

from backend.database.entities import Base


class RANDMessage(Base):
    """RAND Corporation - Artificial Intelligence 消息表（2025统一字段标准）"""
    __tablename__ = "mp_rand_messages"

    # 核心必备字段（遵循2025统一标准）
    id = Column(String(36), primary_key=True, comment="消息ID（UUID）")
    source_id = Column(String(36), ForeignKey("mp_message_sources.id", ondelete="CASCADE"), nullable=False, comment="来源ID")
    external_id = Column(String(100), comment="外部唯一标识（RAND content-id，如RRA4180-1）")
    title = Column(String(500), nullable=False, comment="文章标题")
    content = Column(Text, nullable=False, comment="文章正文内容")
    summary = Column(Text, comment="中文摘要（翻译后）")
    provider = Column(String(500), comment="作者列表（逗号分隔）")
    published_at = Column(DateTime, comment="发布时间")
    crawled_at = Column(DateTime, default=datetime.now, nullable=False, comment="抓取时间")
    url = Column(String(500), unique=True, nullable=False, comment="文章链接（用于去重）")

    # 扩展字段
    region = Column(String(50), default="US", comment="地区（US）")
    category = Column(String(100), comment="出版类型（RESEARCH/COMMENTARY/DATA VIZ等）")
    language = Column(String(10), default="en", comment="语言（en）")
    extra_metadata = Column("metadata", JSON, comment="其他元数据（JSON对象）")

    # 关系
    source = relationship("MessageSource", back_populates="rand_messages")

    # 索引（强制要求）
    __table_args__ = (
        Index("idx_source_id", "source_id"),
        Index("idx_published_at", "published_at"),
        Index("idx_crawled_at", "crawled_at"),
        Index("idx_source_published", "source_id", "published_at"),
        Index("idx_url", "url"),
        Index("idx_external_id", "external_id"),
        Index("idx_category", "category"),
    )
