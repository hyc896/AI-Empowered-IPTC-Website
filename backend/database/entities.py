# -*- coding: utf-8 -*-

"""
消息平台数据库实体定义
定义所有数据库表结构和ORM映射
"""

from datetime import datetime
import uuid
from sqlalchemy import Column, String, Text, DateTime, Date, Integer, BigInteger, Float, Boolean, ForeignKey, Index, JSON, Enum
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
    gcg_ai_messages = relationship("GCGAIMessage", back_populates="source", cascade="all, delete-orphan")
    venturebeat_messages = relationship("VentureBeatMessage", back_populates="source", cascade="all, delete-orphan")
    nikkei_asia_ai_messages = relationship("NikkeiAsiaAIMessage", back_populates="source", cascade="all, delete-orphan")
    investing_com_messages = relationship("InvestingComMessage", back_populates="source", cascade="all, delete-orphan")
    techcrunch_messages = relationship("TechCrunchMessage", back_populates="source", cascade="all, delete-orphan")
    korea_herald_messages = relationship("KoreaHeraldMessage", back_populates="source", cascade="all, delete-orphan")
    techinasia_messages = relationship("TechInAsiaMessage", back_populates="source", cascade="all, delete-orphan")
    guardian_messages = relationship("GuardianMessage", back_populates="source", cascade="all, delete-orphan")
    betakit_messages = relationship("BetaKitMessage", back_populates="source", cascade="all, delete-orphan")
    securities_times_messages = relationship("SecuritiesTimesMessage", back_populates="source", cascade="all, delete-orphan")
    bloomberg_messages = relationship("BloombergMessage", back_populates="source", cascade="all, delete-orphan")
    wsj_messages = relationship("WSJMessage", back_populates="source", cascade="all, delete-orphan")
    axios_messages = relationship("AxiosMessage", back_populates="source", cascade="all, delete-orphan")
    wired_messages = relationship("WiredMessage", back_populates="source", cascade="all, delete-orphan")
    cnbc_messages = relationship("CNBCMessage", back_populates="source", cascade="all, delete-orphan")
    financial_times_messages = relationship("FinancialTimesMessage", back_populates="source", cascade="all, delete-orphan")
    ars_technica_messages = relationship("ArsTechnicaMessage", back_populates="source", cascade="all, delete-orphan")
    der_spiegel_messages = relationship("DerSpiegelMessage", back_populates="source", cascade="all, delete-orphan")
    le_monde_messages = relationship("LeMondeMessage", back_populates="source", cascade="all, delete-orphan")
    times_of_india_messages = relationship("TimesOfIndiaMessage", back_populates="source", cascade="all, delete-orphan")
    the_hindu_messages = relationship("TheHinduMessage", back_populates="source", cascade="all, delete-orphan")

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

    # AI标签字段（arXiv论文全部归类为AI科研信息）
    industry_tags = Column(Text, default="人工智能", comment="行业标签（固定为'人工智能'）")
    ai_tag = Column(String(50), default="AI科研信息", comment="AI分类标签（固定为'AI科研信息'）")

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
        Index("idx_ai_tag", "ai_tag"),
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
    region = Column(String(200), comment="地区（中文格式，如'美国'、'全球'等）")
    industry_tags = Column(Text, comment="行业标签（逗号分隔，最多3个）")
    ai_tag = Column(String(50), comment="AI分类标签（AI科研信息/AI产业信息/AI治理信息）")
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
        Index("idx_ai_tag", "ai_tag"),
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
    industry_tags = Column(Text, comment="行业标签（逗号分隔，最多3个）")
    ai_tag = Column(String(50), comment="AI分类标签（AI科研信息/AI产业信息/AI治理信息）")
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
        Index("idx_ai_tag", "ai_tag"),
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
    industry_tags = Column(Text, comment="行业标签（逗号分隔，最多3个）")
    ai_tag = Column(String(50), comment="AI分类标签（AI科研信息/AI产业信息/AI治理信息）")

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
        Index("idx_ai_tag", "ai_tag"),
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


class InvestingComMessage(Base):
    """Investing.com General News（全球金融市场综合新闻）消息表"""
    __tablename__ = "mp_investing_com_messages"

    # 核心必备字段（遵循2025统一标准）
    id = Column(String(36), primary_key=True, comment="消息ID（UUID）")
    source_id = Column(String(36), ForeignKey("mp_message_sources.id", ondelete="CASCADE"), nullable=False, comment="来源ID")
    external_id = Column(String(200), comment="外部唯一标识（RSS guid）")
    title = Column(String(500), nullable=False, comment="标题")
    content = Column(Text, nullable=False, comment="正文内容（description）")
    summary = Column(Text, comment="摘要（同content）")
    provider = Column(String(500), comment="信息提供方（固定为Investing.com）")
    published_at = Column(DateTime, comment="发布时间（pubDate）")
    crawled_at = Column(DateTime, default=datetime.now, nullable=False, comment="抓取时间")
    url = Column(String(500), unique=True, nullable=False, comment="原文链接（用于去重）")

    # 新增必备字段（2025年强制要求）
    region = Column(String(200), comment="地区（中文格式，如'美国'、'全球'等）")
    industry_tags = Column(Text, comment="行业标签（逗号分隔，最多3个）")
    ai_tag = Column(String(50), comment="AI分类标签（AI科研信息/AI产业信息/AI治理信息）")

    # 扩展字段
    category = Column(String(100), comment="分类（General News）")
    language = Column(String(10), default="en", comment="语言（en）")
    extra_metadata = Column("metadata", JSON, comment="其他元数据（JSON对象）")

    # 关系
    source = relationship("MessageSource", back_populates="investing_com_messages")

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


class TechCrunchMessage(Base):
    """TechCrunch Tech News（全球科技新闻与深度报道）消息表"""
    __tablename__ = "mp_techcrunch_messages"

    # 核心必备字段（遵循2025统一标准）
    id = Column(String(36), primary_key=True, comment="消息ID（UUID）")
    source_id = Column(String(36), ForeignKey("mp_message_sources.id", ondelete="CASCADE"), nullable=False, comment="来源ID")
    external_id = Column(String(200), comment="外部唯一标识（从URL提取的post ID或slug）")
    title = Column(String(500), nullable=False, comment="标题")
    content = Column(Text, nullable=False, comment="正文内容（完整文章内容）")
    summary = Column(Text, comment="摘要（中文翻译）")
    provider = Column(String(500), comment="作者（多个用逗号分隔）")
    published_at = Column(DateTime, comment="发布时间")
    crawled_at = Column(DateTime, default=datetime.now, nullable=False, comment="抓取时间")
    url = Column(String(500), unique=True, nullable=False, comment="原文链接（用于去重）")

    # 新增必备字段（2025年强制要求）
    region = Column(String(200), comment="地区（中文格式，多为'全球'、'美国'等）")
    industry_tags = Column(Text, comment="行业标签（逗号分隔，最多3个）")
    ai_tag = Column(String(50), comment="AI分类标签（AI科研信息/AI产业信息/AI治理信息）")

    # 扩展字段
    category = Column(String(100), comment="分类（AI/Security/Robotics/Cloud Computing/Hardware等）")
    language = Column(String(10), default="en", comment="语言（en）")
    extra_metadata = Column("metadata", JSON, comment="其他元数据（JSON对象）")

    # 关系
    source = relationship("MessageSource", back_populates="techcrunch_messages")

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


class KoreaHeraldMessage(Base):
    """Korea Herald科技新闻（韩国科技、半导体、AI领域新闻）消息表"""
    __tablename__ = "mp_korea_herald_messages"

    # 核心必备字段（遵循2025统一标准）
    id = Column(String(36), primary_key=True, comment="消息ID（UUID）")
    source_id = Column(String(36), ForeignKey("mp_message_sources.id", ondelete="CASCADE"), nullable=False, comment="来源ID")
    external_id = Column(String(200), comment="外部唯一标识（从URL路径提取article ID）")
    title = Column(String(500), nullable=False, comment="标题")
    content = Column(Text, nullable=False, comment="正文内容（从详情页提取）")
    summary = Column(Text, comment="中文摘要（翻译后）")
    provider = Column(String(500), comment="作者或信息提供方（The Korea Herald / Yonhap等）")
    published_at = Column(DateTime, comment="发布时间")
    crawled_at = Column(DateTime, default=datetime.now, nullable=False, comment="抓取时间")
    url = Column(String(500), unique=True, nullable=False, comment="原文链接（用于去重）")

    # 新增必备字段（2025年强制要求）
    region = Column(String(200), comment="地区（中文格式，多为'韩国'、'全球'等）")
    industry_tags = Column(Text, comment="行业标签（逗号分隔，最多3个）")
    ai_tag = Column(String(50), comment="AI分类标签（AI科研信息/AI产业信息/AI治理信息）")

    # 扩展字段
    category = Column(String(100), comment="分类（Business/Technology/AI等）")
    language = Column(String(10), default="en", comment="语言（en）")
    extra_metadata = Column("metadata", JSON, comment="其他元数据（JSON对象）")

    # 关系
    source = relationship("MessageSource", back_populates="korea_herald_messages")

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


class TechInAsiaMessage(Base):
    """Tech in Asia科技新闻（东南亚科技创投新闻）消息表"""
    __tablename__ = "mp_techinasia_messages"

    # 核心必备字段（遵循2025统一标准）
    id = Column(String(36), primary_key=True, comment="消息ID（UUID）")
    source_id = Column(String(36), ForeignKey("mp_message_sources.id", ondelete="CASCADE"), nullable=False, comment="来源ID")
    external_id = Column(String(200), comment="外部唯一标识（从URL slug提取）")
    title = Column(String(500), nullable=False, comment="标题")
    content = Column(Text, nullable=False, comment="正文内容（从详情页提取完整文章）")
    summary = Column(Text, comment="摘要（RSS description翻译为中文）")
    provider = Column(String(500), comment="作者（多个用逗号分隔）")
    published_at = Column(DateTime, comment="发布时间")
    crawled_at = Column(DateTime, default=datetime.now, nullable=False, comment="抓取时间")
    url = Column(String(500), unique=True, nullable=False, comment="原文链接（用于去重）")

    # 新增必备字段（2025年强制要求）
    region = Column(String(200), comment="地区（中文格式，如'新加坡'、'印度尼西亚'、'全球'等）")
    industry_tags = Column(Text, comment="行业标签（逗号分隔，最多3个）")
    ai_tag = Column(String(50), comment="AI分类标签（AI科研信息/AI产业信息/AI治理信息）")

    # 扩展字段
    category = Column(String(100), comment="分类（AI/Investments/Startups/Fintech等）")
    language = Column(String(10), default='en', comment="语言（en）")
    extra_metadata = Column("metadata", JSON, comment="其他元数据（JSON对象）")

    # 关系
    source = relationship("MessageSource", back_populates="techinasia_messages")

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


class GuardianMessage(Base):
    """The Guardian AI与科技新闻消息表"""
    __tablename__ = "mp_guardian_messages"

    # 核心必备字段（遵循2025统一标准）
    id = Column(String(36), primary_key=True, comment="消息ID（UUID）")
    source_id = Column(String(36), ForeignKey("mp_message_sources.id", ondelete="CASCADE"), nullable=False, comment="来源ID")
    external_id = Column(String(200), comment="外部唯一标识（RSS guid）")
    title = Column(String(500), nullable=False, comment="标题")
    content = Column(Text, nullable=False, comment="正文内容（RSS description或summary）")
    summary = Column(Text, comment="摘要（中文翻译）")
    provider = Column(String(500), comment="作者（多个用逗号分隔）")
    published_at = Column(DateTime, comment="发布时间")
    crawled_at = Column(DateTime, default=datetime.now, nullable=False, comment="抓取时间")
    url = Column(String(500), unique=True, nullable=False, comment="原文链接（用于去重）")

    # 新增必备字段（2025年强制要求）
    region = Column(String(200), comment="地区（中文格式，如'英国'、'全球'等）")
    industry_tags = Column(Text, comment="行业标签（逗号分隔，最多3个）")
    ai_tag = Column(String(50), comment="AI分类标签（AI科研信息/AI产业信息/AI治理信息）")

    # 扩展字段
    category = Column(String(100), comment="分类（AI/Technology/Security等）")
    language = Column(String(10), default='en', comment="语言（en）")

    # 关系
    source = relationship("MessageSource", back_populates="guardian_messages")

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


class BetaKitMessage(Base):
    """BetaKit Canadian Tech News（加拿大科技新闻与创业生态）消息表"""
    __tablename__ = "mp_betakit_messages"

    # 核心必备字段（遵循2025统一标准）
    id = Column(String(36), primary_key=True, comment="消息ID（UUID）")
    source_id = Column(String(36), ForeignKey("mp_message_sources.id", ondelete="CASCADE"), nullable=False, comment="来源ID")
    external_id = Column(String(200), comment="外部唯一标识（从RSS guid提取的post ID或URL slug）")
    title = Column(String(500), nullable=False, comment="标题")
    content = Column(Text, nullable=False, comment="正文内容（从RSS content:encoded清理HTML后提取）")
    summary = Column(Text, comment="摘要（中文翻译，来自RSS description）")
    provider = Column(String(500), comment="作者（RSS dc:creator字段）")
    published_at = Column(DateTime, comment="发布时间（RSS pubDate字段）")
    crawled_at = Column(DateTime, default=datetime.now, nullable=False, comment="抓取时间")
    url = Column(String(500), unique=True, nullable=False, comment="原文链接（用于去重）")

    # 新增必备字段（2025年强制要求）
    region = Column(String(200), comment="地区（中文格式，主要为'加拿大'或'加拿大/省份'）")
    industry_tags = Column(Text, comment="行业标签（逗号分隔，最多3个）")
    ai_tag = Column(String(50), comment="AI分类标签（AI科研信息/AI产业信息/AI治理信息）")

    # 扩展字段
    category = Column(String(100), comment="分类（ai/machine-learning/funding/startups等）")
    language = Column(String(10), default="en", comment="语言（en，可能包含法语）")
    tags = Column(JSON, comment="RSS category标签列表（JSON数组）")

    # 关系
    source = relationship("MessageSource", back_populates="betakit_messages")

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
        Index("idx_ai_tag", "ai_tag"),
    )


class AIDailyReport(Base):
    """AI日报表"""
    __tablename__ = "mp_ai_daily_reports"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), comment="UUID主键")
    report_date = Column(Date, nullable=False, index=True, comment="报告日期（YYYY-MM-DD）")
    report_type = Column(String(20), nullable=False, default='comprehensive', comment="报告类型（comprehensive/governance/research/industry）")
    content = Column(Text, nullable=False, comment="日报Markdown内容")
    statistics = Column(JSON, nullable=False, comment="统计数据（消息数量、地区分布等）")
    governance_count = Column(Integer, nullable=False, default=0, comment="AI治理信息数量")
    research_count = Column(Integer, nullable=False, default=0, comment="AI科研信息数量")
    industry_count = Column(Integer, nullable=False, default=0, comment="AI产业信息数量")
    total_messages = Column(Integer, nullable=False, default=0, comment="总消息数量")
    generation_status = Column(String(20), nullable=False, default='pending', comment="生成状态（pending/completed/failed）")
    error_message = Column(Text, nullable=True, comment="错误信息（生成失败时记录）")
    generated_at = Column(DateTime, nullable=False, default=datetime.now, comment="生成时间")
    model_version = Column(String(50), nullable=False, comment="LLM模型版本")

    __table_args__ = (
        Index("idx_report_date_type", "report_date", "report_type", unique=True),
        Index("idx_generated_at", "generated_at"),
        Index("idx_status", "generation_status"),
    )


class SecuritiesTimesMessage(Base):
    """证券时报（Securities Times）财经新闻消息表"""
    __tablename__ = "mp_securities_times_messages"

    # 核心必备字段（遵循2025统一标准）
    id = Column(String(36), primary_key=True, comment="消息ID（UUID）")
    source_id = Column(String(36), ForeignKey("mp_message_sources.id", ondelete="CASCADE"), nullable=False, comment="来源ID")
    external_id = Column(String(200), comment="外部唯一标识（从URL提取的文章ID，如3500937）")
    title = Column(String(500), nullable=False, comment="标题")
    content = Column(Text, nullable=False, comment="正文内容（从详情页提取）")
    summary = Column(Text, comment="摘要（优先提取excerpt，否则用content前1000字）")
    provider = Column(String(500), comment="作者（多个用逗号分隔，从byline提取）")
    published_at = Column(DateTime, comment="发布时间（格式：YYYY-MM-DD HH:MM）")
    crawled_at = Column(DateTime, default=datetime.now, nullable=False, comment="抓取时间")
    url = Column(String(500), unique=True, nullable=False, comment="原文链接（用于去重）")

    # 新增必备字段（2025年强制要求）
    region = Column(String(200), comment="地区（中文格式，从文章内容提取，如'中国'、'中国/广东省/深圳市'、'全球'等）")
    industry_tags = Column(Text, comment="行业标签（逗号分隔，最多3个，如'金融,科技金融,人工智能'）")
    ai_tag = Column(String(50), comment="AI分类标签（AI科研信息/AI产业信息/AI治理信息）")

    # 扩展字段
    category = Column(String(500), comment="文章分类（要闻/快讯/股市/公司等）")
    language = Column(String(10), default="zh", comment="语言（zh=中文）")
    tags = Column(JSON, comment="标签列表（JSON数组，从页面提取）")
    extra_metadata = Column("metadata", JSON, comment="其他元数据（JSON对象）")

    # 关系
    source = relationship("MessageSource", back_populates="securities_times_messages")

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
        Index("idx_ai_tag", "ai_tag"),
    )


class BloombergMessage(Base):
    """Bloomberg Technology科技新闻消息表（基于RSS Feed采集）"""
    __tablename__ = "mp_bloomberg_messages"

    # 核心必备字段（遵循2025统一标准）
    id = Column(String(36), primary_key=True, comment="消息ID（UUID）")
    source_id = Column(String(36), ForeignKey("mp_message_sources.id", ondelete="CASCADE"), nullable=False, comment="来源ID")
    external_id = Column(String(200), comment="外部唯一标识（RSS的guid字段）")
    title = Column(String(500), nullable=False, comment="标题（RSS的title字段）")
    content = Column(Text, nullable=False, comment="正文内容（RSS的description字段）")
    summary = Column(Text, comment="中文摘要（翻译后）")
    provider = Column(String(500), comment="作者（RSS的dc:creator字段）")
    published_at = Column(DateTime, comment="发布时间（RSS的pubDate字段）")
    crawled_at = Column(DateTime, default=datetime.now, nullable=False, comment="抓取时间")
    url = Column(String(500), unique=True, nullable=False, comment="原文链接（RSS的link字段，用于去重）")

    # 新增必备字段（2025年强制要求）
    region = Column(String(200), comment="地区（中文格式，从文章内容提取，如'美国'、'全球'等）")
    industry_tags = Column(Text, comment="行业标签（逗号分隔，最多3个，涉及AI必须包含'人工智能'标签）")
    ai_tag = Column(String(50), comment="AI分类标签（AI科研信息/AI产业信息/AI治理信息）")

    # 扩展字段
    category = Column(String(500), comment="文章分类（RSS的category字段）")
    language = Column(String(10), default="en", comment="语言（en=英文）")
    media_content = Column(String(500), comment="媒体内容URL（RSS的media:content字段）")
    tags = Column(JSON, comment="标签列表（JSON数组）")
    extra_metadata = Column("metadata", JSON, comment="其他元数据（JSON对象）")

    # 关系
    source = relationship("MessageSource", back_populates="bloomberg_messages")

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
        Index("idx_ai_tag", "ai_tag"),
    )


class WSJMessage(Base):
    """Wall Street Journal Technology科技新闻消息表（基于RSS Feed采集）"""
    __tablename__ = "mp_wsj_messages"

    # 核心必备字段（遵循2025统一标准）
    id = Column(String(36), primary_key=True, comment="消息ID（UUID）")
    source_id = Column(String(36), ForeignKey("mp_message_sources.id", ondelete="CASCADE"), nullable=False, comment="来源ID")
    external_id = Column(String(200), comment="外部唯一标识（RSS的guid字段）")
    title = Column(String(500), nullable=False, comment="标题（RSS的title字段）")
    content = Column(Text, nullable=False, comment="正文内容（RSS的description字段）")
    summary = Column(Text, comment="中文摘要（翻译后）")
    provider = Column(String(500), comment="作者（RSS的author字段）")
    published_at = Column(DateTime, comment="发布时间（RSS的pubDate字段）")
    crawled_at = Column(DateTime, default=datetime.now, nullable=False, comment="抓取时间")
    url = Column(String(500), unique=True, nullable=False, comment="原文链接（RSS的link字段，用于去重）")

    # 新增必备字段（2025年强制要求）
    region = Column(String(200), comment="地区（中文格式，从文章内容提取，如'美国'、'全球'等）")
    industry_tags = Column(Text, comment="行业标签（逗号分隔，最多3个，涉及AI必须包含'人工智能'标签）")
    ai_tag = Column(String(50), comment="AI分类标签（AI科研信息/AI产业信息/AI治理信息）")

    # 扩展字段
    category = Column(String(500), comment="文章分类（RSS的category字段）")
    language = Column(String(10), default="en", comment="语言（en=英文）")
    media_content = Column(String(500), comment="媒体内容URL（RSS的media:content字段）")
    tags = Column(JSON, comment="标签列表（JSON数组）")
    extra_metadata = Column("metadata", JSON, comment="其他元数据（JSON对象）")

    # 关系
    source = relationship("MessageSource", back_populates="wsj_messages")

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
        Index("idx_ai_tag", "ai_tag"),
    )


class AxiosMessage(Base):
    """Axios新闻消息表（基于RSS Feed采集）"""
    __tablename__ = "mp_axios_messages"

    # 核心必备字段（遵循2025统一标准）
    id = Column(String(36), primary_key=True, comment="消息ID（UUID）")
    source_id = Column(String(36), ForeignKey("mp_message_sources.id", ondelete="CASCADE"), nullable=False, comment="来源ID")
    external_id = Column(String(200), comment="外部唯一标识（RSS的guid字段）")
    title = Column(String(500), nullable=False, comment="标题（RSS的title字段）")
    content = Column(Text, nullable=False, comment="正文内容（RSS的description字段）")
    summary = Column(Text, comment="中文摘要（翻译后）")
    provider = Column(String(500), comment="作者（RSS的author字段）")
    published_at = Column(DateTime, comment="发布时间（RSS的pubDate字段）")
    crawled_at = Column(DateTime, default=datetime.now, nullable=False, comment="抓取时间")
    url = Column(String(500), unique=True, nullable=False, comment="原文链接（RSS的link字段，用于去重）")

    # 新增必备字段（2025年强制要求）
    region = Column(String(200), comment="地区（中文格式，从文章内容提取，如'美国'、'全球'等）")
    industry_tags = Column(Text, comment="行业标签（逗号分隔，最多3个，涉及AI必须包含'人工智能'标签）")
    ai_tag = Column(String(50), comment="AI分类标签（AI科研信息/AI产业信息/AI治理信息）")

    # 扩展字段
    category = Column(String(500), comment="文章分类（RSS的category字段）")
    language = Column(String(10), default="en", comment="语言（en=英文）")
    media_content = Column(String(500), comment="媒体内容URL（RSS的media:content字段）")
    tags = Column(JSON, comment="标签列表（JSON数组）")
    extra_metadata = Column("metadata", JSON, comment="其他元数据（JSON对象）")

    # 关系
    source = relationship("MessageSource", back_populates="axios_messages")

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
        Index("idx_ai_tag", "ai_tag"),
    )

class WiredMessage(Base):
    """Wired科技新闻消息表（基于RSS Feed采集）"""
    __tablename__ = "mp_wired_messages"

    # 核心必备字段（遵循2025统一标准）
    id = Column(String(36), primary_key=True, comment="消息ID（UUID）")
    source_id = Column(String(36), ForeignKey("mp_message_sources.id", ondelete="CASCADE"), nullable=False, comment="来源ID")
    external_id = Column(String(200), comment="外部唯一标识（RSS的guid字段）")
    title = Column(String(500), nullable=False, comment="标题（RSS的title字段）")
    content = Column(Text, nullable=False, comment="正文内容（RSS的description字段）")
    summary = Column(Text, comment="中文摘要（翻译后）")
    provider = Column(String(500), comment="作者（RSS的author字段）")
    published_at = Column(DateTime, comment="发布时间（RSS的pubDate字段）")
    crawled_at = Column(DateTime, default=datetime.now, nullable=False, comment="抓取时间")
    url = Column(String(500), unique=True, nullable=False, comment="原文链接（RSS的link字段，用于去重）")

    # 新增必备字段（2025年强制要求）
    region = Column(String(200), comment="地区（中文格式，从文章内容提取，默认'美国'）")
    industry_tags = Column(Text, comment="行业标签（逗号分隔，最多3个，涉及AI必须包含'人工智能'标签）")
    ai_tag = Column(String(50), comment="AI分类标签（AI科研信息/AI产业信息/AI治理信息）")

    # 扩展字段
    category = Column(String(500), comment="文章分类（RSS的category字段）")
    language = Column(String(10), default="en", comment="语言（en=英文）")
    media_content = Column(String(500), comment="媒体内容URL（RSS的media:content字段）")
    tags = Column(JSON, comment="标签列表（JSON数组）")
    extra_metadata = Column("metadata", JSON, comment="其他元数据（JSON对象）")

    # 关系
    source = relationship("MessageSource", back_populates="wired_messages")

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
        Index("idx_ai_tag", "ai_tag"),
    )


class CNBCMessage(Base):
    """CNBC Technology消息表（基于RSS Feed采集）"""
    __tablename__ = "mp_cnbc_messages"

    # 核心必备字段（遵循2025统一标准）
    id = Column(String(36), primary_key=True, comment="消息ID（UUID）")
    source_id = Column(String(36), ForeignKey("mp_message_sources.id", ondelete="CASCADE"), nullable=False, comment="来源ID")
    external_id = Column(String(200), comment="外部唯一标识（RSS的guid字段）")
    title = Column(String(500), nullable=False, comment="标题（RSS的title字段）")
    content = Column(Text, nullable=False, comment="正文内容（RSS的description字段）")
    summary = Column(Text, comment="中文摘要（翻译后）")
    provider = Column(String(500), comment="作者（RSS的author字段）")
    published_at = Column(DateTime, comment="发布时间（RSS的pubDate字段）")
    crawled_at = Column(DateTime, default=datetime.now, nullable=False, comment="抓取时间")
    url = Column(String(500), unique=True, nullable=False, comment="原文链接（RSS的link字段，用于去重）")

    # 新增必备字段（2025年强制要求）
    region = Column(String(200), comment="地区（中文格式，从文章内容提取，默认'美国'）")
    industry_tags = Column(Text, comment="行业标签（逗号分隔，最多3个，涉及AI必须包含'人工智能'标签）")
    ai_tag = Column(String(50), comment="AI分类标签（AI科研信息/AI产业信息/AI治理信息）")

    # 扩展字段
    category = Column(String(500), comment="文章分类（RSS的category字段）")
    language = Column(String(10), default="en", comment="语言")
    media_content = Column(String(500), comment="媒体内容URL（RSS的media:content字段）")
    tags = Column(JSON, comment="标签列表（JSON数组）")
    extra_metadata = Column("metadata", JSON, comment="其他元数据（JSON对象）")

    # 关系
    source = relationship("MessageSource", back_populates="cnbc_messages")

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
        Index("idx_ai_tag", "ai_tag"),
    )


class FinancialTimesMessage(Base):
    """Financial Times Technology消息表（基于RSS Feed采集）"""
    __tablename__ = "mp_financial_times_messages"

    # 核心必备字段（遵循2025统一标准）
    id = Column(String(36), primary_key=True, comment="消息ID（UUID）")
    source_id = Column(String(36), ForeignKey("mp_message_sources.id", ondelete="CASCADE"), nullable=False, comment="来源ID")
    external_id = Column(String(200), comment="外部唯一标识（RSS的guid字段）")
    title = Column(String(500), nullable=False, comment="标题（RSS的title字段）")
    content = Column(Text, nullable=False, comment="正文内容（RSS的description字段）")
    summary = Column(Text, comment="中文摘要（翻译后）")
    provider = Column(String(500), comment="作者（RSS的author字段）")
    published_at = Column(DateTime, comment="发布时间（RSS的pubDate字段）")
    crawled_at = Column(DateTime, default=datetime.now, nullable=False, comment="抓取时间")
    url = Column(String(500), unique=True, nullable=False, comment="原文链接（RSS的link字段，用于去重）")

    # 新增必备字段（2025年强制要求）
    region = Column(String(200), comment="地区（中文格式，从文章内容提取，默认'英国'）")
    industry_tags = Column(Text, comment="行业标签（逗号分隔，最多3个，涉及AI必须包含'人工智能'标签）")
    ai_tag = Column(String(50), comment="AI分类标签（AI科研信息/AI产业信息/AI治理信息）")

    # 扩展字段
    category = Column(String(500), comment="文章分类（RSS的category字段）")
    language = Column(String(10), default="en", comment="语言")
    media_content = Column(String(500), comment="媒体内容URL（RSS的media:content字段）")
    tags = Column(JSON, comment="标签列表（JSON数组）")
    extra_metadata = Column("metadata", JSON, comment="其他元数据（JSON对象）")

    # 关系
    source = relationship("MessageSource", back_populates="financial_times_messages")

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
        Index("idx_ai_tag", "ai_tag"),
    )


class ArsTechnicaMessage(Base):
    """Ars Technica消息表（基于RSS Feed采集）"""
    __tablename__ = "mp_ars_technica_messages"

    # 核心必备字段（遵循2025统一标准）
    id = Column(String(36), primary_key=True, comment="消息ID（UUID）")
    source_id = Column(String(36), ForeignKey("mp_message_sources.id", ondelete="CASCADE"), nullable=False, comment="来源ID")
    external_id = Column(String(200), comment="外部唯一标识（RSS的guid字段）")
    title = Column(String(500), nullable=False, comment="标题（RSS的title字段）")
    content = Column(Text, nullable=False, comment="正文内容（RSS的description字段）")
    summary = Column(Text, comment="中文摘要（翻译后）")
    provider = Column(String(500), comment="作者（RSS的author字段）")
    published_at = Column(DateTime, comment="发布时间（RSS的pubDate字段）")
    crawled_at = Column(DateTime, default=datetime.now, nullable=False, comment="抓取时间")
    url = Column(String(500), unique=True, nullable=False, comment="原文链接（RSS的link字段，用于去重）")

    # 新增必备字段（2025年强制要求）
    region = Column(String(200), comment="地区（中文格式，从文章内容提取，默认'美国'）")
    industry_tags = Column(Text, comment="行业标签（逗号分隔，最多3个，涉及AI必须包含'人工智能'标签）")
    ai_tag = Column(String(50), comment="AI分类标签（AI科研信息/AI产业信息/AI治理信息）")

    # 扩展字段
    category = Column(String(500), comment="文章分类（RSS的category字段）")
    language = Column(String(10), default="en", comment="语言")
    media_content = Column(String(500), comment="媒体内容URL（RSS的media:content字段）")
    tags = Column(JSON, comment="标签列表（JSON数组）")
    extra_metadata = Column("metadata", JSON, comment="其他元数据（JSON对象）")

    # 关系
    source = relationship("MessageSource", back_populates="ars_technica_messages")

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
        Index("idx_ai_tag", "ai_tag"),
    )


class DerSpiegelMessage(Base):
    """Der Spiegel Netzwelt消息表（基于RSS Feed采集）"""
    __tablename__ = "mp_der_spiegel_messages"

    # 核心必备字段（遵循2025统一标准）
    id = Column(String(36), primary_key=True, comment="消息ID（UUID）")
    source_id = Column(String(36), ForeignKey("mp_message_sources.id", ondelete="CASCADE"), nullable=False, comment="来源ID")
    external_id = Column(String(200), comment="外部唯一标识（RSS的guid字段）")
    title = Column(String(500), nullable=False, comment="标题（RSS的title字段）")
    content = Column(Text, nullable=False, comment="正文内容（RSS的description字段）")
    summary = Column(Text, comment="中文摘要（翻译后）")
    provider = Column(String(500), comment="作者（RSS的author字段）")
    published_at = Column(DateTime, comment="发布时间（RSS的pubDate字段）")
    crawled_at = Column(DateTime, default=datetime.now, nullable=False, comment="抓取时间")
    url = Column(String(500), unique=True, nullable=False, comment="原文链接（RSS的link字段，用于去重）")

    # 新增必备字段（2025年强制要求）
    region = Column(String(200), comment="地区（中文格式，从文章内容提取，默认'德国'）")
    industry_tags = Column(Text, comment="行业标签（逗号分隔，最多3个，涉及AI必须包含'人工智能'标签）")
    ai_tag = Column(String(50), comment="AI分类标签（AI科研信息/AI产业信息/AI治理信息）")

    # 扩展字段
    category = Column(String(500), comment="文章分类（RSS的category字段）")
    language = Column(String(10), default="de", comment="语言")
    media_content = Column(String(500), comment="媒体内容URL（RSS的media:content字段）")
    tags = Column(JSON, comment="标签列表（JSON数组）")
    extra_metadata = Column("metadata", JSON, comment="其他元数据（JSON对象）")

    # 关系
    source = relationship("MessageSource", back_populates="der_spiegel_messages")

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
        Index("idx_ai_tag", "ai_tag"),
    )


class LeMondeMessage(Base):
    """Le Monde Pixels消息表（基于RSS Feed采集）"""
    __tablename__ = "mp_le_monde_messages"

    # 核心必备字段（遵循2025统一标准）
    id = Column(String(36), primary_key=True, comment="消息ID（UUID）")
    source_id = Column(String(36), ForeignKey("mp_message_sources.id", ondelete="CASCADE"), nullable=False, comment="来源ID")
    external_id = Column(String(200), comment="外部唯一标识（RSS的guid字段）")
    title = Column(String(500), nullable=False, comment="标题（RSS的title字段）")
    content = Column(Text, nullable=False, comment="正文内容（RSS的description字段）")
    summary = Column(Text, comment="中文摘要（翻译后）")
    provider = Column(String(500), comment="作者（RSS的author字段）")
    published_at = Column(DateTime, comment="发布时间（RSS的pubDate字段）")
    crawled_at = Column(DateTime, default=datetime.now, nullable=False, comment="抓取时间")
    url = Column(String(500), unique=True, nullable=False, comment="原文链接（RSS的link字段，用于去重）")

    # 新增必备字段（2025年强制要求）
    region = Column(String(200), comment="地区（中文格式，从文章内容提取，默认'法国'）")
    industry_tags = Column(Text, comment="行业标签（逗号分隔，最多3个，涉及AI必须包含'人工智能'标签）")
    ai_tag = Column(String(50), comment="AI分类标签（AI科研信息/AI产业信息/AI治理信息）")

    # 扩展字段
    category = Column(String(500), comment="文章分类（RSS的category字段）")
    language = Column(String(10), default="fr", comment="语言")
    media_content = Column(String(500), comment="媒体内容URL（RSS的media:content字段）")
    tags = Column(JSON, comment="标签列表（JSON数组）")
    extra_metadata = Column("metadata", JSON, comment="其他元数据（JSON对象）")

    # 关系
    source = relationship("MessageSource", back_populates="le_monde_messages")

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
        Index("idx_ai_tag", "ai_tag"),
    )


class TimesOfIndiaMessage(Base):
    """Times of India Tech消息表（基于RSS Feed采集）"""
    __tablename__ = "mp_times_of_india_messages"

    # 核心必备字段（遵循2025统一标准）
    id = Column(String(36), primary_key=True, comment="消息ID（UUID）")
    source_id = Column(String(36), ForeignKey("mp_message_sources.id", ondelete="CASCADE"), nullable=False, comment="来源ID")
    external_id = Column(String(200), comment="外部唯一标识（RSS的guid字段）")
    title = Column(String(500), nullable=False, comment="标题（RSS的title字段）")
    content = Column(Text, nullable=False, comment="正文内容（RSS的description字段）")
    summary = Column(Text, comment="中文摘要（翻译后）")
    provider = Column(String(500), comment="作者（RSS的author字段）")
    published_at = Column(DateTime, comment="发布时间（RSS的pubDate字段）")
    crawled_at = Column(DateTime, default=datetime.now, nullable=False, comment="抓取时间")
    url = Column(String(500), unique=True, nullable=False, comment="原文链接（RSS的link字段，用于去重）")

    # 新增必备字段（2025年强制要求）
    region = Column(String(200), comment="地区（中文格式，从文章内容提取，默认'印度'）")
    industry_tags = Column(Text, comment="行业标签（逗号分隔，最多3个，涉及AI必须包含'人工智能'标签）")
    ai_tag = Column(String(50), comment="AI分类标签（AI科研信息/AI产业信息/AI治理信息）")

    # 扩展字段
    category = Column(String(500), comment="文章分类（RSS的category字段）")
    language = Column(String(10), default="en", comment="语言")
    media_content = Column(String(500), comment="媒体内容URL（RSS的media:content字段）")
    tags = Column(JSON, comment="标签列表（JSON数组）")
    extra_metadata = Column("metadata", JSON, comment="其他元数据（JSON对象）")

    # 关系
    source = relationship("MessageSource", back_populates="times_of_india_messages")

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
        Index("idx_ai_tag", "ai_tag"),
    )


class TheHinduMessage(Base):
    """The Hindu Business消息表（基于RSS Feed采集）"""
    __tablename__ = "mp_the_hindu_messages"

    # 核心必备字段（遵循2025统一标准）
    id = Column(String(36), primary_key=True, comment="消息ID（UUID）")
    source_id = Column(String(36), ForeignKey("mp_message_sources.id", ondelete="CASCADE"), nullable=False, comment="来源ID")
    external_id = Column(String(200), comment="外部唯一标识（RSS的guid字段）")
    title = Column(String(500), nullable=False, comment="标题（RSS的title字段）")
    content = Column(Text, nullable=False, comment="正文内容（RSS的description字段）")
    summary = Column(Text, comment="中文摘要（翻译后）")
    provider = Column(String(500), comment="作者（RSS的author字段）")
    published_at = Column(DateTime, comment="发布时间（RSS的pubDate字段）")
    crawled_at = Column(DateTime, default=datetime.now, nullable=False, comment="抓取时间")
    url = Column(String(500), unique=True, nullable=False, comment="原文链接（RSS的link字段，用于去重）")

    # 新增必备字段（2025年强制要求）
    region = Column(String(200), comment="地区（中文格式，从文章内容提取，默认'印度'）")
    industry_tags = Column(Text, comment="行业标签（逗号分隔，最多3个，涉及AI必须包含'人工智能'标签）")
    ai_tag = Column(String(50), comment="AI分类标签（AI科研信息/AI产业信息/AI治理信息）")

    # 扩展字段
    category = Column(String(500), comment="文章分类（RSS的category字段）")
    language = Column(String(10), default="en", comment="语言")
    media_content = Column(String(500), comment="媒体内容URL（RSS的media:content字段）")
    tags = Column(JSON, comment="标签列表（JSON数组）")
    extra_metadata = Column("metadata", JSON, comment="其他元数据（JSON对象）")

    # 关系
    source = relationship("MessageSource", back_populates="the_hindu_messages")

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
        Index("idx_ai_tag", "ai_tag"),
    )
