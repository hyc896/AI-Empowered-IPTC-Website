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
    govai_messages = relationship("GovAIMessage", back_populates="source", cascade="all, delete-orphan")
    oecd_ai_messages = relationship("OECDAIMessage", back_populates="source", cascade="all, delete-orphan")
    csis_messages = relationship("CSISMessage", back_populates="source", cascade="all, delete-orphan")
    wef_publication_messages = relationship("WEFPublicationMessage", back_populates="source", cascade="all, delete-orphan")
    cigi_messages = relationship("CIGIMessage", back_populates="source", cascade="all, delete-orphan")
    cnas_messages = relationship("CNASMessage", back_populates="source", cascade="all, delete-orphan")
    cset_messages = relationship("CSETMessage", back_populates="source", cascade="all, delete-orphan")
    rand_messages = relationship("RANDMessage", back_populates="source", cascade="all, delete-orphan")
    takshashila_messages = relationship("TakshashilaMessage", back_populates="source", cascade="all, delete-orphan")
    icrier_messages = relationship("ICRIERMessage", back_populates="source", cascade="all, delete-orphan")
    stellenbosch_messages = relationship("StellenboschMessage", back_populates="source", cascade="all, delete-orphan")
    hse_ai_messages = relationship("HSEAIMessage", back_populates="source", cascade="all, delete-orphan")
    obia_messages = relationship("OBIAMessage", back_populates="source", cascade="all, delete-orphan")
    gcg_ai_messages = relationship("GCGAIMessage", back_populates="source", cascade="all, delete-orphan")
    ada_lovelace_messages = relationship("AdaLovelaceMessage", back_populates="source", cascade="all, delete-orphan")
    ieai_messages = relationship("IEAIMessage", back_populates="source", cascade="all, delete-orphan")
    fari_messages = relationship("FARIMessage", back_populates="source", cascade="all, delete-orphan")
    kira_messages = relationship("KIRAMessage", back_populates="source", cascade="all, delete-orphan")
    aisi_messages = relationship("AISIMessage", back_populates="source", cascade="all, delete-orphan")
    future_society_messages = relationship("FutureSocietyMessage", back_populates="source", cascade="all, delete-orphan")
    saif_messages = relationship("SAIFMessage", back_populates="source", cascade="all, delete-orphan")
    venturebeat_messages = relationship("VentureBeatMessage", back_populates="source", cascade="all, delete-orphan")
    nikkei_asia_ai_messages = relationship("NikkeiAsiaAIMessage", back_populates="source", cascade="all, delete-orphan")

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
    region = Column(String(200), comment="地区（国家/省份/城市，斜杠分隔）")
    industry_tags = Column(Text, comment="行业标签（逗号分隔，最多3个）")
    ai_tag = Column(String(50), comment="AI分类标签（AI科研信息/AI产业信息/AI治理信息）")

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
    region = Column(String(200), comment="地区（国家/省份/城市，斜杠分隔）")
    industry_tags = Column(Text, comment="行业标签（逗号分隔，最多3个）")
    ai_tag = Column(String(50), comment="AI分类标签（AI科研信息/AI产业信息/AI治理信息）")

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


class GovAIMessage(Base):
    """Centre for the Governance of AI（人工智能治理中心）研究论文表"""
    __tablename__ = "mp_govai_messages"

    # 核心必备字段
    id = Column(String(36), primary_key=True, comment="消息ID（UUID）")
    source_id = Column(String(36), ForeignKey("mp_message_sources.id", ondelete="CASCADE"), nullable=False, comment="来源ID")
    external_id = Column(String(100), comment="外部唯一标识（从URL路径提取）")
    title = Column(String(500), nullable=False, comment="论文标题")
    content = Column(Text, nullable=False, comment="论文摘要/正文内容")
    summary = Column(Text, comment="中文摘要（翻译后）")
    provider = Column(String(500), comment="作者列表（逗号分隔）")
    published_at = Column(DateTime, comment="发布时间")
    crawled_at = Column(DateTime, default=datetime.now, nullable=False, comment="抓取时间")
    url = Column(String(500), unique=True, nullable=False, comment="论文链接（用于去重）")

    # 扩展字段
    region = Column(String(50), default="GLOBAL", comment="地区（GLOBAL）")
    category = Column(String(100), comment="研究分类（Survey Research/Technical AI Governance等）")
    language = Column(String(10), default="en", comment="语言（en）")
    extra_metadata = Column("metadata", JSON, comment="其他元数据（JSON对象）")

    # 关系
    source = relationship("MessageSource", back_populates="govai_messages")

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


class OECDAIMessage(Base):
    """OECD Artificial Intelligence Policy Observatory（经合组织人工智能政策观察站）博客表"""
    __tablename__ = "mp_oecd_ai_messages"

    # 核心必备字段
    id = Column(String(36), primary_key=True, comment="消息ID（UUID）")
    source_id = Column(String(36), ForeignKey("mp_message_sources.id", ondelete="CASCADE"), nullable=False, comment="来源ID")
    external_id = Column(String(100), comment="外部唯一标识（从URL路径提取）")
    title = Column(String(500), nullable=False, comment="文章标题")
    content = Column(Text, nullable=False, comment="文章正文内容")
    summary = Column(Text, comment="中文摘要（翻译后）")
    provider = Column(String(500), comment="作者列表（逗号分隔）")
    published_at = Column(DateTime, comment="发布时间")
    crawled_at = Column(DateTime, default=datetime.now, nullable=False, comment="抓取时间")
    url = Column(String(500), unique=True, nullable=False, comment="文章链接（用于去重）")

    # 扩展字段
    region = Column(String(50), default="GLOBAL", comment="地区（GLOBAL）")
    category = Column(String(100), comment="文章分类（Academia/Civil society/Intergovernmental等）")
    language = Column(String(10), default="en", comment="语言（en）")
    extra_metadata = Column("metadata", JSON, comment="其他元数据（JSON对象）")

    # 关系
    source = relationship("MessageSource", back_populates="oecd_ai_messages")

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


class CSISMessage(Base):
    """CSIS AI Topic（战略与国际研究中心-AI主题）文章表"""
    __tablename__ = "mp_csis_messages"

    # 核心必备字段
    id = Column(String(36), primary_key=True, comment="消息ID（UUID）")
    source_id = Column(String(36), ForeignKey("mp_message_sources.id", ondelete="CASCADE"), nullable=False, comment="来源ID")
    external_id = Column(String(100), comment="外部唯一标识（从URL路径提取）")
    title = Column(String(500), nullable=False, comment="文章标题")
    content = Column(Text, nullable=False, comment="文章正文内容")
    summary = Column(Text, comment="中文摘要（翻译后）")
    provider = Column(String(500), comment="作者列表（逗号分隔）")
    published_at = Column(DateTime, comment="发布时间")
    crawled_at = Column(DateTime, default=datetime.now, nullable=False, comment="抓取时间")
    url = Column(String(500), unique=True, nullable=False, comment="文章链接（用于去重）")

    # 扩展字段
    region = Column(String(50), default="US", comment="地区（US）")
    category = Column(String(100), comment="内容类型（Event/Commentary/Report/Podcast Episode等）")
    language = Column(String(10), default="en", comment="语言（en）")
    extra_metadata = Column("metadata", JSON, comment="其他元数据（JSON对象）")

    # 关系
    source = relationship("MessageSource", back_populates="csis_messages")

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


class WEFPublicationMessage(Base):
    """World Economic Forum (WEF) AI Publications（世界经济论坛AI出版物）表"""
    __tablename__ = "mp_wef_publication_messages"

    # 核心必备字段
    id = Column(String(36), primary_key=True, comment="消息ID（UUID）")
    source_id = Column(String(36), ForeignKey("mp_message_sources.id", ondelete="CASCADE"), nullable=False, comment="来源ID")
    external_id = Column(String(100), comment="外部唯一标识（从URL路径提取slug）")
    title = Column(String(500), nullable=False, comment="出版物标题")
    content = Column(Text, nullable=False, comment="出版物正文内容")
    summary = Column(Text, comment="中文摘要（翻译后）")
    provider = Column(String(500), comment="合作方（如Ministry of Economy of UAE等）")
    published_at = Column(DateTime, comment="发布时间")
    crawled_at = Column(DateTime, default=datetime.now, nullable=False, comment="抓取时间")
    url = Column(String(500), unique=True, nullable=False, comment="出版物链接（用于去重）")

    # 扩展字段
    region = Column(String(50), default="GLOBAL", comment="地区（GLOBAL）")
    category = Column(String(100), comment="出版物分类（如EMERGING TECHNOLOGIES等）")
    language = Column(String(10), default="en", comment="语言（en）")
    extra_metadata = Column("metadata", JSON, comment="其他元数据（JSON对象）")

    # 关系
    source = relationship("MessageSource", back_populates="wef_publication_messages")

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


class CNASMessage(Base):
    """Center for a New American Security (CNAS)（新美国安全中心）文章表"""
    __tablename__ = "mp_cnas_messages"

    # 核心必备字段
    id = Column(String(36), primary_key=True, comment="消息ID（UUID）")
    source_id = Column(String(36), ForeignKey("mp_message_sources.id", ondelete="CASCADE"), nullable=False, comment="来源ID")
    external_id = Column(String(100), comment="外部唯一标识（从URL路径提取slug）")
    title = Column(String(500), nullable=False, comment="文章标题")
    content = Column(Text, nullable=False, comment="文章正文内容")
    summary = Column(Text, comment="中文摘要（翻译后）")
    provider = Column(String(500), comment="作者列表（逗号分隔）")
    published_at = Column(DateTime, comment="发布时间")
    crawled_at = Column(DateTime, default=datetime.now, nullable=False, comment="抓取时间")
    url = Column(String(500), unique=True, nullable=False, comment="文章链接（用于去重）")

    # 扩展字段
    region = Column(String(50), default="US", comment="地区（US）")
    category = Column(String(100), comment="内容分类（Defense/Technology & National Security等）")
    language = Column(String(10), default="en", comment="语言（en）")

    # 关系
    source = relationship("MessageSource", back_populates="cnas_messages")

    # 索引
    __table_args__ = (
        Index("idx_source_id", "source_id"),
        Index("idx_published_at", "published_at"),
        Index("idx_crawled_at", "crawled_at"),
        Index("idx_source_published", "source_id", "published_at"),
        Index("idx_url", "url"),
        Index("idx_external_id", "external_id"),
        Index("idx_category", "category"),
    )


class CSETMessage(Base):
    """Center for Security and Emerging Technology (CSET)（安全与新兴技术中心-乔治城大学）研究论文表"""
    __tablename__ = "mp_cset_messages"

    # 核心必备字段
    id = Column(String(36), primary_key=True, comment="消息ID（UUID）")
    source_id = Column(String(36), ForeignKey("mp_message_sources.id", ondelete="CASCADE"), nullable=False, comment="来源ID")
    external_id = Column(String(100), comment="外部唯一标识（从URL路径提取slug）")
    title = Column(String(500), nullable=False, comment="文章标题")
    content = Column(Text, nullable=False, comment="文章正文内容（从详情页提取）")
    summary = Column(Text, comment="中文摘要（翻译后）")
    provider = Column(String(500), comment="作者列表（逗号分隔）")
    published_at = Column(DateTime, comment="发布时间")
    crawled_at = Column(DateTime, default=datetime.now, nullable=False, comment="抓取时间")
    url = Column(String(500), unique=True, nullable=False, comment="文章链接（用于去重）")

    # 扩展字段
    region = Column(String(50), default="US", comment="地区（US-乔治城大学位于华盛顿）")
    category = Column(String(100), comment="内容类型（Analysis/Report/Blog/Research等）")
    language = Column(String(10), default="en", comment="语言（en）")

    # 关系
    source = relationship("MessageSource", back_populates="cset_messages")

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


class CIGIMessage(Base):
    """Centre for International Governance Innovation（国际治理创新中心）研究出版物表"""
    __tablename__ = "mp_cigi_messages"

    # 核心必备字段（遵循2025统一标准）
    id = Column(String(36), primary_key=True, comment="消息ID（UUID）")
    source_id = Column(String(36), ForeignKey("mp_message_sources.id", ondelete="CASCADE"), nullable=False, comment="来源ID")
    external_id = Column(String(200), comment="外部唯一标识（从URL路径提取slug）")
    title = Column(String(500), nullable=False, comment="标题")
    content = Column(Text, nullable=False, comment="正文内容")
    summary = Column(Text, comment="中文摘要（优先从网页提取，无则翻译content前1000字）")
    provider = Column(String(500), comment="作者列表（多个用逗号分隔）")
    published_at = Column(DateTime, comment="发布时间")
    crawled_at = Column(DateTime, default=datetime.now, nullable=False, comment="抓取时间")
    url = Column(String(500), unique=True, nullable=False, comment="原文链接（用于去重）")

    # 扩展字段
    region = Column(String(50), default="CA", comment="地区（CA=Canada）")
    content_type = Column(String(50), comment="内容类型（Publication/Opinion/News Releases/Multimedia/Event/Op-Eds）")
    language = Column(String(10), default="en", comment="语言（en）")
    pdf_url = Column(String(500), comment="PDF下载链接（如果有）")
    extra_metadata = Column("metadata", JSON, comment="其他元数据（JSON对象）")

    # 关系
    source = relationship("MessageSource", back_populates="cigi_messages")

    # 索引（强制要求）
    __table_args__ = (
        Index("idx_source_id", "source_id"),
        Index("idx_published_at", "published_at"),
        Index("idx_crawled_at", "crawled_at"),
        Index("idx_source_published", "source_id", "published_at"),
        Index("idx_url", "url"),
        Index("idx_external_id", "external_id"),
        Index("idx_content_type", "content_type"),
    )


class RANDMessage(Base):
    """RAND Corporation - Artificial Intelligence（兰德公司-人工智能）研究文章表"""
    __tablename__ = "mp_rand_messages"

    # 核心必备字段
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


class TakshashilaMessage(Base):
    """Takshashila Institution（印度塔克沙希拉研究所）出版物表"""
    __tablename__ = "mp_takshashila_messages"

    # 核心必备字段（遵循2025统一标准）
    id = Column(String(36), primary_key=True, comment="消息ID（UUID）")
    source_id = Column(String(36), ForeignKey("mp_message_sources.id", ondelete="CASCADE"), nullable=False, comment="来源ID")
    external_id = Column(String(200), comment="外部唯一标识（从URL文件名提取，如20251103-LEPF-Policy-Brief）")
    title = Column(String(500), nullable=False, comment="标题")
    content = Column(Text, nullable=False, comment="正文内容（从详情页提取）")
    summary = Column(Text, comment="中文摘要（翻译后）")
    provider = Column(String(500), comment="作者列表（多个用逗号分隔）")
    published_at = Column(DateTime, comment="发布时间")
    crawled_at = Column(DateTime, default=datetime.now, nullable=False, comment="抓取时间")
    url = Column(String(500), unique=True, nullable=False, comment="原文链接（用于去重）")

    # 扩展字段
    region = Column(String(50), default="IN", comment="地区（IN=India）")
    language = Column(String(10), default="en", comment="语言（en）")
    publication_type = Column(String(100), comment="出版物类型（Policy Brief/Discussion Document/Working Paper/Journal Article等）")
    categories = Column(JSON, comment="分类标签列表（如Geopolitics, Public Policy, Governance）")
    extra_metadata = Column("metadata", JSON, comment="其他元数据（JSON对象）")

    # 关系
    source = relationship("MessageSource", back_populates="takshashila_messages")

    # 索引（强制要求）
    __table_args__ = (
        Index("idx_source_id", "source_id"),
        Index("idx_published_at", "published_at"),
        Index("idx_crawled_at", "crawled_at"),
        Index("idx_source_published", "source_id", "published_at"),
        Index("idx_url", "url"),
        Index("idx_external_id", "external_id"),
        Index("idx_publication_type", "publication_type"),
    )


class ICRIERMessage(Base):
    """ICRIER (Indian Council for Research on International Economic Relations) 出版物表"""
    __tablename__ = "mp_icrier_messages"

    # 核心必备字段（遵循2025统一标准）
    id = Column(String(36), primary_key=True, comment="消息ID（UUID）")
    source_id = Column(String(36), ForeignKey("mp_message_sources.id", ondelete="CASCADE"), nullable=False, comment="来源ID")
    external_id = Column(String(200), comment="外部唯一标识（URL slug）")
    title = Column(String(500), nullable=False, comment="标题")
    content = Column(Text, nullable=False, comment="正文内容（英文摘要）")
    summary = Column(Text, comment="摘要（中文翻译）")
    provider = Column(String(500), comment="作者（多个用逗号分隔）")
    published_at = Column(DateTime, comment="发布时间")
    crawled_at = Column(DateTime, default=datetime.now, nullable=False, comment="抓取时间")
    url = Column(String(500), unique=True, nullable=False, comment="原文链接（用于去重）")

    # 扩展字段
    region = Column(String(50), default="IN", comment="地区（IN=India）")
    category = Column(String(100), comment="分类（Policy Briefs/Reports/Bulletins等）")
    language = Column(String(10), default="en", comment="语言（en）")
    pdf_url = Column(String(500), comment="PDF下载链接")
    extra_metadata = Column("metadata", JSON, comment="其他元数据（JSON对象）")

    # 关系
    source = relationship("MessageSource", back_populates="icrier_messages")

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
        },
        {
            "name": "mp_stellenbosch_messages",
            "description": "斯坦陵布什大学政策创新实验室新闻表",
            "primary_key": "id",
            "unique_key": "url",
            "foreign_key": "source_id → mp_message_sources.id"
        }
    ]

    return tables


class HSEAIMessage(Base):
    """HSE University AI Research Centre 新闻消息表"""
    __tablename__ = "mp_hse_ai_messages"

    # 核心必备字段（遵循2025统一标准）
    id = Column(String(36), primary_key=True, comment="消息ID（UUID）")
    source_id = Column(String(36), ForeignKey("mp_message_sources.id", ondelete="CASCADE"), nullable=False, comment="来源ID")
    external_id = Column(String(200), comment="外部唯一标识（从URL提取的数字ID）")
    title = Column(String(500), nullable=False, comment="标题")
    content = Column(Text, nullable=False, comment="正文内容（英文）")
    summary = Column(Text, comment="摘要（中文翻译）")
    provider = Column(String(500), comment="作者或主要人物（多个用逗号分隔）")
    published_at = Column(DateTime, comment="发布时间")
    crawled_at = Column(DateTime, default=datetime.now, nullable=False, comment="抓取时间")
    url = Column(String(500), unique=True, nullable=False, comment="原文链接（用于去重）")

    # 扩展字段
    region = Column(String(50), default="RU", comment="地区（RU=Russia）")
    category = Column(String(100), comment="分类（Research & Expertise等）")
    language = Column(String(10), default="en", comment="语言（en）")
    tags = Column(JSON, comment="关键词标签（JSON数组）")
    extra_metadata = Column("metadata", JSON, comment="其他元数据（JSON对象）")

    # 关系
    source = relationship("MessageSource", back_populates="hse_ai_messages")

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


class StellenboschMessage(Base):
    """Policy Innovation Lab, Stellenbosch University（斯坦陵布什大学政策创新实验室）新闻文章表"""
    __tablename__ = "mp_stellenbosch_messages"

    # 核心必备字段（遵循2025统一标准）
    id = Column(String(36), primary_key=True, comment="消息ID（UUID）")
    source_id = Column(String(36), ForeignKey("mp_message_sources.id", ondelete="CASCADE"), nullable=False, comment="来源ID")
    external_id = Column(String(200), comment="外部唯一标识（从URL路径提取slug）")
    title = Column(String(500), nullable=False, comment="标题")
    content = Column(Text, nullable=False, comment="正文内容（从详情页提取）")
    summary = Column(Text, comment="中文摘要（翻译后）")
    provider = Column(String(500), comment="作者（From JSON-LD schema）")
    published_at = Column(DateTime, comment="发布时间")
    crawled_at = Column(DateTime, default=datetime.now, nullable=False, comment="抓取时间")
    url = Column(String(500), unique=True, nullable=False, comment="原文链接（用于去重）")

    # 扩展字段
    region = Column(String(50), default="ZA", comment="地区（ZA=South Africa 南非）")
    category = Column(String(100), comment="分类（从articleSection提取，如Data Science & Public Policy/Goalkeepers stories/News等）")
    language = Column(String(10), default="en", comment="语言（en）")
    word_count = Column(Integer, comment="字数统计（从JSON-LD schema提取）")
    extra_metadata = Column("metadata", JSON, comment="其他元数据（JSON对象）")

    # 关系
    source = relationship("MessageSource", back_populates="stellenbosch_messages")

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

class OBIAMessage(Base):
    """OBIA (Observatório Brasileiro de Inteligência Artificial) 巴西AI观测站研究出版物表"""
    __tablename__ = "mp_obia_messages"

    # 核心必备字段（遵循2025统一标准）
    id = Column(String(36), primary_key=True, comment="消息ID（UUID）")
    source_id = Column(String(36), ForeignKey("mp_message_sources.id", ondelete="CASCADE"), nullable=False, comment="来源ID")
    external_id = Column(String(200), comment="外部唯一标识（从PDF URL提取data-guid）")
    title = Column(String(500), nullable=False, comment="标题")
    content = Column(Text, nullable=False, comment="正文内容（描述信息）")
    summary = Column(Text, comment="摘要（中文翻译）")
    provider = Column(String(500), comment="作者列表（多个用逗号分隔）")
    published_at = Column(DateTime, comment="发布时间（从PDF URL中的时间戳提取，格式：YYYYMMDDhhmmss）")
    crawled_at = Column(DateTime, default=datetime.now, nullable=False, comment="抓取时间")
    url = Column(String(500), unique=True, nullable=False, comment="原文链接（PDF直链，用于去重）")

    # 扩展字段
    region = Column(String(50), default="BR", comment="地区（BR=Brazil 巴西）")
    category = Column(String(100), comment="分类（PANORAMA SETORIAL DA INTERNET/PESQUISAS TIC等）")
    language = Column(String(10), default="pt", comment="语言（pt=葡萄牙语）")
    pdf_url = Column(String(500), comment="PDF下载链接（与url相同）")
    series = Column(String(100), comment="系列名称（Panorama Setorial/TIC Empresas/TIC Governo等）")
    extra_metadata = Column("metadata", JSON, comment="其他元数据（JSON对象）")

    # 关系
    source = relationship("MessageSource", back_populates="obia_messages")

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


class GCGAIMessage(Base):
    """Global Center on AI Governance (GCG)（南非/非洲AI治理研究中心）研究报告表"""
    __tablename__ = "mp_gcg_ai_messages"

    # 核心必备字段（遵循2025统一标准）
    id = Column(String(36), primary_key=True, comment="消息ID（UUID）")
    source_id = Column(String(36), ForeignKey("mp_message_sources.id", ondelete="CASCADE"), nullable=False, comment="来源ID")
    external_id = Column(String(200), comment="外部唯一标识（从URL路径提取slug）")
    title = Column(String(500), nullable=False, comment="标题")
    content = Column(Text, nullable=False, comment="正文内容（从详情页提取的简介）")
    summary = Column(Text, comment="中文摘要（翻译后）")
    provider = Column(String(500), comment="作者（多个用逗号分隔）")
    published_at = Column(DateTime, comment="发布时间")
    crawled_at = Column(DateTime, default=datetime.now, nullable=False, comment="抓取时间")
    url = Column(String(500), unique=True, nullable=False, comment="原文链接（用于去重）")

    # 扩展字段
    region = Column(String(50), default="ZA", comment="地区（ZA=South Africa/Africa 南非/非洲）")
    category = Column(String(100), comment="出版物类型（Policy Brief/Report/Article/Analysis/Toolkit等）")
    language = Column(String(10), default="en", comment="语言（en）")
    tags = Column(JSON, comment="标签列表（如Technology、Public Policy等）")
    pdf_url = Column(String(500), comment="PDF下载链接（如果有）")
    extra_metadata = Column("metadata", JSON, comment="其他元数据（JSON对象）")

    # 关系
    source = relationship("MessageSource", back_populates="gcg_ai_messages")

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


class AdaLovelaceMessage(Base):
    """Ada Lovelace Institute（英国AI治理与伦理智库）博客文章表"""
    __tablename__ = "mp_ada_lovelace_messages"

    # 核心必备字段（遵循2025统一标准）
    id = Column(String(36), primary_key=True, comment="消息ID（UUID）")
    source_id = Column(String(36), ForeignKey("mp_message_sources.id", ondelete="CASCADE"), nullable=False, comment="来源ID")
    external_id = Column(String(200), comment="外部唯一标识（从URL路径提取slug）")
    title = Column(String(500), nullable=False, comment="标题")
    content = Column(Text, nullable=False, comment="正文内容（从详情页提取完整文章）")
    summary = Column(Text, comment="中文摘要（翻译后）")
    provider = Column(String(500), comment="作者（多个用逗号分隔）")
    published_at = Column(DateTime, comment="发布时间")
    crawled_at = Column(DateTime, default=datetime.now, nullable=False, comment="抓取时间")
    url = Column(String(500), unique=True, nullable=False, comment="原文链接（用于去重）")

    # 扩展字段
    region = Column(String(50), default="UK", comment="地区（UK=United Kingdom 英国）")
    category = Column(String(100), comment="内容类型（Commentary/Report/Blog Post等）")
    language = Column(String(10), default="en", comment="语言（en）")
    tags = Column(JSON, comment="标签列表（如AI policy、Data governance等）")
    reading_time = Column(Integer, comment="预计阅读时间（分钟）")
    extra_metadata = Column("metadata", JSON, comment="其他元数据（JSON对象）")

    # 关系
    source = relationship("MessageSource", back_populates="ada_lovelace_messages")

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


class IEAIMessage(Base):
    """Institute for Ethics in AI (IEAI) - TUM（德国慕尼黑技术大学AI伦理研究所）文章表"""
    __tablename__ = "mp_ieai_messages"

    # 核心必备字段（遵循2025统一标准）
    id = Column(String(36), primary_key=True, comment="消息ID（UUID）")
    source_id = Column(String(36), ForeignKey("mp_message_sources.id", ondelete="CASCADE"), nullable=False, comment="来源ID")
    external_id = Column(String(200), comment="外部唯一标识（从URL路径提取slug）")
    title = Column(String(500), nullable=False, comment="标题")
    content = Column(Text, nullable=False, comment="正文内容（完整文章内容）")
    summary = Column(Text, comment="中文摘要（翻译后）")
    provider = Column(String(500), comment="作者（多个用逗号分隔）")
    published_at = Column(DateTime, comment="发布时间")
    crawled_at = Column(DateTime, default=datetime.now, nullable=False, comment="抓取时间")
    url = Column(String(500), unique=True, nullable=False, comment="原文链接（用于去重）")

    # 扩展字段
    region = Column(String(50), default="DE", comment="地区（DE=Germany 德国）")
    category = Column(String(100), comment="文章类型（News/Blog/Research等）")
    language = Column(String(10), default="en", comment="语言（en）")
    tags = Column(JSON, comment="标签列表（如AI Ethics、Cognitive Science等）")
    extra_metadata = Column("metadata", JSON, comment="其他元数据（JSON对象）")

    # 关系
    source = relationship("MessageSource", back_populates="ieai_messages")

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


class FARIMessage(Base):
    """FARI - AI for the Common Good Institute（比利时AI公益研究所）新闻与出版物表"""
    __tablename__ = "mp_fari_messages"

    # 核心必备字段（遵循2025统一标准）
    id = Column(String(36), primary_key=True, comment="消息ID（UUID）")
    source_id = Column(String(36), ForeignKey("mp_message_sources.id", ondelete="CASCADE"), nullable=False, comment="来源ID")
    external_id = Column(String(200), comment="外部唯一标识（从URL路径提取slug）")
    title = Column(String(500), nullable=False, comment="标题")
    content = Column(Text, nullable=False, comment="正文内容（从详情页提取完整内容）")
    summary = Column(Text, comment="中文摘要（翻译后）")
    provider = Column(String(500), comment="作者（多个用逗号分隔）")
    published_at = Column(DateTime, comment="发布时间")
    crawled_at = Column(DateTime, default=datetime.now, nullable=False, comment="抓取时间")
    url = Column(String(500), unique=True, nullable=False, comment="原文链接（用于去重）")

    # 扩展字段
    region = Column(String(50), default="BE", comment="地区（BE=Belgium 比利时）")
    content_type = Column(String(100), comment="内容类型（News/Report/Journal Article/Conference Proceeding/Thesis）")
    language = Column(String(10), default="en", comment="语言（en）")
    tags = Column(JSON, comment="主题标签（如Sustainable AI、Data & Robotics等）")
    pdf_url = Column(String(500), comment="PDF下载链接（出版物）")
    extra_metadata = Column("metadata", JSON, comment="其他元数据（JSON对象）")

    # 关系
    source = relationship("MessageSource", back_populates="fari_messages")

    # 索引（强制要求）
    __table_args__ = (
        Index("idx_source_id", "source_id"),
        Index("idx_published_at", "published_at"),
        Index("idx_crawled_at", "crawled_at"),
        Index("idx_source_published", "source_id", "published_at"),
        Index("idx_url", "url"),
        Index("idx_external_id", "external_id"),
        Index("idx_content_type", "content_type"),
    )


class KIRAMessage(Base):
    """KIRA Center（德国AI风险与影响研究中心）博客与报告表"""
    __tablename__ = "mp_kira_messages"

    # 核心必备字段（遵循2025统一标准）
    id = Column(String(36), primary_key=True, comment="消息ID（UUID）")
    source_id = Column(String(36), ForeignKey("mp_message_sources.id", ondelete="CASCADE"), nullable=False, comment="来源ID")
    external_id = Column(String(200), comment="外部唯一标识（从URL路径提取slug）")
    title = Column(String(500), nullable=False, comment="标题")
    content = Column(Text, nullable=False, comment="正文内容（从详情页提取完整内容）")
    summary = Column(Text, comment="中文摘要（翻译后）")
    provider = Column(String(500), comment="作者（多个用逗号分隔）")
    published_at = Column(DateTime, comment="发布时间")
    crawled_at = Column(DateTime, default=datetime.now, nullable=False, comment="抓取时间")
    url = Column(String(500), unique=True, nullable=False, comment="原文链接（用于去重）")

    # 扩展字段
    region = Column(String(50), default="DE", comment="地区（DE=Germany 德国）")
    content_type = Column(String(100), comment="内容类型（Blog/Report/Policy Analysis）")
    language = Column(String(10), default="en", comment="语言（en/de）")
    pdf_url = Column(String(500), comment="PDF报告下载链接")
    extra_metadata = Column("metadata", JSON, comment="其他元数据（JSON对象）")

    # 关系
    source = relationship("MessageSource", back_populates="kira_messages")

    # 索引（强制要求）
    __table_args__ = (
        Index("idx_source_id", "source_id"),
        Index("idx_published_at", "published_at"),
        Index("idx_crawled_at", "crawled_at"),
        Index("idx_source_published", "source_id", "published_at"),
        Index("idx_url", "url"),
        Index("idx_external_id", "external_id"),
        Index("idx_content_type", "content_type"),
    )


class AISIMessage(Base):
    """AI Security Institute（英国政府AI安全研究机构）研究与博客表"""
    __tablename__ = "mp_aisi_messages"

    # 核心必备字段（遵循2025统一标准）
    id = Column(String(36), primary_key=True, comment="消息ID（UUID）")
    source_id = Column(String(36), ForeignKey("mp_message_sources.id", ondelete="CASCADE"), nullable=False, comment="来源ID")
    external_id = Column(String(200), comment="外部唯一标识（从URL路径提取slug）")
    title = Column(String(500), nullable=False, comment="标题")
    content = Column(Text, nullable=False, comment="正文内容（从详情页提取完整内容）")
    summary = Column(Text, comment="中文摘要（翻译后）")
    provider = Column(String(500), comment="作者（多个用逗号分隔）")
    published_at = Column(DateTime, comment="发布时间")
    crawled_at = Column(DateTime, default=datetime.now, nullable=False, comment="抓取时间")
    url = Column(String(500), unique=True, nullable=False, comment="原文链接（用于去重）")

    # 扩展字段
    region = Column(String(50), default="UK", comment="地区（UK=United Kingdom 英国）")
    content_type = Column(String(100), comment="内容类型（Research/Blog/Technical Report）")
    language = Column(String(10), default="en", comment="语言（en）")
    categories = Column(JSON, comment="分类标签（JSON数组，如Safeguards, Control, Alignment等）")
    extra_metadata = Column("metadata", JSON, comment="其他元数据（JSON对象）")

    # 关系
    source = relationship("MessageSource", back_populates="aisi_messages")

    # 索引（强制要求）
    __table_args__ = (
        Index("idx_source_id", "source_id"),
        Index("idx_published_at", "published_at"),
        Index("idx_crawled_at", "crawled_at"),
        Index("idx_source_published", "source_id", "published_at"),
        Index("idx_url", "url"),
        Index("idx_external_id", "external_id"),
        Index("idx_content_type", "content_type"),
    )


class FutureSocietyMessage(Base):
    """The Future Society（跨大西洋AI治理智库）研究报告与政策简报表"""
    __tablename__ = "mp_future_society_messages"

    # 核心必备字段（遵循2025统一标准）
    id = Column(String(36), primary_key=True, comment="消息ID（UUID）")
    source_id = Column(String(36), ForeignKey("mp_message_sources.id", ondelete="CASCADE"), nullable=False, comment="来源ID")
    external_id = Column(String(200), comment="外部唯一标识（从URL路径提取slug）")
    title = Column(String(500), nullable=False, comment="标题")
    content = Column(Text, nullable=False, comment="正文内容（从详情页提取完整内容）")
    summary = Column(Text, comment="中文摘要（翻译后）")
    provider = Column(String(500), comment="作者（多个用逗号分隔）")
    published_at = Column(DateTime, comment="发布时间")
    crawled_at = Column(DateTime, default=datetime.now, nullable=False, comment="抓取时间")
    url = Column(String(500), unique=True, nullable=False, comment="原文链接（用于去重）")

    # 扩展字段
    region = Column(String(50), default="GLOBAL", comment="地区（US+BE，设为GLOBAL）")
    content_type = Column(String(100), comment="内容类型（Report/Policy Brief/Article等）")
    language = Column(String(10), default="en", comment="语言（en）")
    categories = Column(JSON, comment="分类标签（JSON数组，如AI Governance, EU AI Act等）")
    extra_metadata = Column("metadata", JSON, comment="其他元数据（JSON对象，包括pdf_url等）")

    # 关系
    source = relationship("MessageSource", back_populates="future_society_messages")

    # 索引（强制要求）
    __table_args__ = (
        Index("idx_source_id", "source_id"),
        Index("idx_published_at", "published_at"),
        Index("idx_crawled_at", "crawled_at"),
        Index("idx_source_published", "source_id", "published_at"),
        Index("idx_url", "url"),
        Index("idx_external_id", "external_id"),
        Index("idx_content_type", "content_type"),
    )


class SAIFMessage(Base):
    """Safe AI Forum (SAIF)（英国AI安全论坛）研究报告与政策指南表"""
    __tablename__ = "mp_saif_messages"

    # 核心必备字段（遵循2025统一标准）
    id = Column(String(36), primary_key=True, comment="消息ID（UUID）")
    source_id = Column(String(36), ForeignKey("mp_message_sources.id", ondelete="CASCADE"), nullable=False, comment="来源ID")
    external_id = Column(String(200), comment="外部唯一标识（从URL路径提取slug）")
    title = Column(String(500), nullable=False, comment="标题")
    content = Column(Text, nullable=False, comment="正文内容（摘要或完整内容）")
    summary = Column(Text, comment="中文摘要（翻译后）")
    provider = Column(String(500), comment="作者（多个用逗号分隔）")
    published_at = Column(DateTime, comment="发布时间")
    crawled_at = Column(DateTime, default=datetime.now, nullable=False, comment="抓取时间")
    url = Column(String(500), unique=True, nullable=False, comment="原文链接（用于去重）")

    # 扩展字段
    region = Column(String(50), default="UK", comment="地区（UK=United Kingdom 英国）")
    content_type = Column(String(100), comment="内容类型（Research/Policy Guide/Primer/Report等）")
    language = Column(String(10), default="en", comment="语言（en/zh=中英双语出版物）")
    pdf_url = Column(String(500), comment="PDF下载链接")
    updated_at = Column(DateTime, comment="文章更新时间")
    extra_metadata = Column("metadata", JSON, comment="其他元数据（JSON对象）")

    # 关系
    source = relationship("MessageSource", back_populates="saif_messages")

    # 索引（强制要求）
    __table_args__ = (
        Index("idx_source_id", "source_id"),
        Index("idx_published_at", "published_at"),
        Index("idx_crawled_at", "crawled_at"),
        Index("idx_source_published", "source_id", "published_at"),
        Index("idx_url", "url"),
        Index("idx_external_id", "external_id"),
        Index("idx_content_type", "content_type"),
    )


class VentureBeatMessage(Base):
    """VentureBeat科技媒体（美国AI、数据基础设施、安全领域新闻）消息表"""
    __tablename__ = "mp_venturebeat_messages"

    # 核心必备字段（遵循2025统一标准）
    id = Column(String(36), primary_key=True, comment="消息ID（UUID）")
    source_id = Column(String(36), ForeignKey("mp_message_sources.id", ondelete="CASCADE"), nullable=False, comment="来源ID")
    external_id = Column(String(200), comment="外部唯一标识（从URL路径提取slug）")
    title = Column(String(500), nullable=False, comment="标题")
    content = Column(Text, nullable=False, comment="正文内容（从详情页提取的完整文章）")
    summary = Column(Text, comment="中文摘要（翻译后）")
    provider = Column(String(500), comment="作者（多个用逗号分隔）")
    published_at = Column(DateTime, comment="发布时间")
    crawled_at = Column(DateTime, default=datetime.now, nullable=False, comment="抓取时间")
    url = Column(String(500), unique=True, nullable=False, comment="原文链接（用于去重）")

    # 新增必备字段（2025年强制要求）
    region = Column(String(200), comment="地区（中文格式，如'美国'、'美国/加利福尼亚州'、'全球'等）")
    industry_tags = Column(Text, comment="行业标签（逗号分隔，最多3个，涉及AI必须包含'人工智能'标签）")

    # 扩展字段
    category = Column(String(100), comment="文章分类（AI/Data Infrastructure/Security）")
    language = Column(String(10), default="en", comment="语言（en）")
    excerpt = Column(Text, comment="摘要（从列表页提取的excerpt）")
    featured_image = Column(String(500), comment="特色图片URL")
    tags = Column(JSON, comment="标签列表（JSON数组）")
    extra_metadata = Column("metadata", JSON, comment="其他元数据（JSON对象）")

    # 关系
    source = relationship("MessageSource", back_populates="venturebeat_messages")

    # 索引（强制要求）
    __table_args__ = (
        Index("idx_source_id", "source_id"),
        Index("idx_published_at", "published_at"),
        Index("idx_crawled_at", "crawled_at"),
        Index("idx_source_published", "source_id", "published_at"),
        Index("idx_url", "url"),
        Index("idx_external_id", "external_id"),
        Index("idx_category", "category"),
        Index("idx_region", "region"),
    )


class NikkeiAsiaAIMessage(Base):
    """Nikkei Asia AI板块（日经亚洲人工智能新闻）消息表"""
    __tablename__ = "mp_nikkei_asia_ai_messages"

    # 核心必备字段（遵循2025统一标准）
    id = Column(String(36), primary_key=True, comment="消息ID（UUID）")
    source_id = Column(String(36), ForeignKey("mp_message_sources.id", ondelete="CASCADE"), nullable=False, comment="来源ID")
    external_id = Column(String(200), comment="外部唯一标识（文章ID或slug）")
    title = Column(String(500), nullable=False, comment="标题")
    content = Column(Text, nullable=False, comment="正文内容（subhead描述）")
    summary = Column(Text, comment="中文摘要（翻译后）")
    provider = Column(String(500), comment="作者")
    published_at = Column(DateTime, comment="发布时间")
    crawled_at = Column(DateTime, default=datetime.now, nullable=False, comment="抓取时间")
    url = Column(String(500), unique=True, nullable=False, comment="原文链接（用于去重）")

    # 扩展字段
    region = Column(String(200), comment="地区")
    category = Column(String(100), comment="分类")
    language = Column(String(10), default="en", comment="语言")
    industry_tags = Column(String(200), comment="行业标签")
    ai_tag = Column(String(50), comment="AI分类标签")
    extra_metadata = Column("metadata", JSON, comment="其他元数据")

    # 关系
    source = relationship("MessageSource", back_populates="nikkei_asia_ai_messages")

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
