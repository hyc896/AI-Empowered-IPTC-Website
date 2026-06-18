# -*- coding: utf-8 -*-

"""
数据库ORM实体定义
"""

import enum
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Enum, Boolean, Integer, Float, Text, JSON, ForeignKey

def _enum(enum_cls):
    """创建使用枚举value存储的Enum列类型"""
    return Enum(enum_cls, values_callable=lambda x: [e.value for e in x])
from sqlalchemy.orm import relationship, backref
from database.connection import Base


# 枚举类型定义
class UserRole(enum.Enum):
    """用户角色"""
    STUDENT = "student"
    TEACHER = "teacher"
    ADMIN = "admin"


class PracticeType(enum.Enum):
    """实践类型"""
    WRITING = "writing"           # 写作设计类
    PRESENTATION = "presentation" # 宣传表达类
    VISIT = "visit"               # 参观研学类
    PERFORMANCE = "performance"   # 表演体验类
    INTERACTION = "interaction"   # 交往行动类
    PRODUCTION = "production"     # 生产改造类
    FREE = "free"                 # 自由申请类


class SubmissionStatus(enum.Enum):
    """提交状态"""
    DRAFT = "draft"           # 草稿
    SUBMITTED = "submitted"   # 已提交
    REVIEWING = "reviewing"   # 审核中
    APPROVED = "approved"     # 通过
    REJECTED = "rejected"     # 不通过


# 实体类定义
class User(Base):
    """用户表"""
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, comment="用户ID (UUID)")
    username = Column(String(50), unique=True, nullable=False, index=True, comment="用户名 (学号/工号)")
    password_hash = Column(String(255), nullable=False, comment="密码哈希")
    real_name = Column(String(50), nullable=False, comment="真实姓名")
    role = Column(_enum(UserRole), nullable=False, default=UserRole.STUDENT, comment="用户角色")
    email = Column(String(100), comment="邮箱")
    phone = Column(String(20), comment="手机号")
    department = Column(String(100), comment="院系/部门")
    class_name = Column(String(50), comment="班级 (学生)")
    teacher_id = Column(String(36), ForeignKey('users.id', ondelete='SET NULL'), comment="指导教师ID (学生)")
    major = Column(String(100), comment="专业")
    interests = Column(String(500), comment="兴趣爱好/特长")
    is_active = Column(Boolean, default=True, comment="是否激活")
    created_at = Column(DateTime, default=datetime.now, nullable=False, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False, comment="更新时间")
    last_login_at = Column(DateTime, comment="最后登录时间")

    # 关系
    practice_plans = relationship("PracticePlan", back_populates="user", cascade="all, delete-orphan")
    submissions = relationship("PracticeSubmission", back_populates="user", cascade="all, delete-orphan")
    reviews = relationship("PracticeReview", back_populates="reviewer")

    __table_args__ = (
        {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}
    )


class KnowledgePoint(Base):
    """知识点表"""
    __tablename__ = "knowledge_points"

    id = Column(String(36), primary_key=True, comment="知识点ID")
    code = Column(String(50), unique=True, nullable=False, index=True, comment="知识点编码")
    name = Column(String(200), nullable=False, comment="知识点名称")
    category = Column(String(50), nullable=False, comment="所属课程 (习概/思修/马原)")
    chapter = Column(String(100), comment="章节")
    description = Column(Text, comment="知识点描述")
    keywords = Column(String(500), comment="关键词 (逗号分隔)")
    is_active = Column(Boolean, default=True, comment="是否启用")
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    # 关系
    practice_plans = relationship("PracticePlan", back_populates="knowledge_point")

    __table_args__ = (
        {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}
    )


class PracticePlan(Base):
    """实践方案表"""
    __tablename__ = "practice_plans"

    id = Column(String(36), primary_key=True, comment="方案ID")
    user_id = Column(String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True, comment="学生ID")
    knowledge_point_id = Column(String(36), ForeignKey('knowledge_points.id', ondelete='SET NULL'), index=True, comment="知识点ID")
    practice_type = Column(_enum(PracticeType), nullable=False, comment="实践类型")
    title = Column(String(200), nullable=False, comment="方案标题")
    content = Column(Text, nullable=False, comment="方案详细内容 (Markdown)")
    tasks = Column(JSON, nullable=False, comment="任务清单")
    venues = Column(JSON, comment="推荐场馆（AI生成）")
    venue_id = Column(String(36), ForeignKey('venues.id', ondelete='SET NULL'), nullable=True, comment="用户预选场馆ID")
    estimated_hours = Column(Integer, comment="预计耗时 (小时)")
    difficulty = Column(String(20), comment="难度等级")
    deadline = Column(DateTime, comment="截止日期")
    generation_status = Column(String(20), default='pending', comment="生成状态")
    error_message = Column(Text, comment="错误信息")
    generated_at = Column(DateTime, comment="生成完成时间")
    created_at = Column(DateTime, default=datetime.now, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    # 关系
    user = relationship("User", back_populates="practice_plans")
    knowledge_point = relationship("KnowledgePoint", back_populates="practice_plans")
    submissions = relationship("PracticeSubmission", back_populates="plan", cascade="all, delete-orphan")

    __table_args__ = (
        {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}
    )


class Venue(Base):
    """场馆表"""
    __tablename__ = "venues"

    id = Column(String(36), primary_key=True, comment="场馆ID")
    name = Column(String(200), nullable=False, comment="场馆名称")
    category = Column(String(50), comment="场馆类别")
    address = Column(String(500), nullable=False, comment="详细地址")
    latitude = Column(Float, comment="纬度")
    longitude = Column(Float, comment="经度")
    description = Column(Text, comment="场馆简介")
    opening_hours = Column(String(200), comment="开放时间")
    contact_phone = Column(String(50), comment="联系电话")
    official_website = Column(String(500), comment="官方网站")
    related_knowledge_points = Column(JSON, comment="关联知识点ID列表")
    images = Column(JSON, comment="场馆图片URL列表")
    source = Column(String(50), comment="数据来源")
    source_url = Column(String(500), comment="来源新闻URL")
    case_id = Column(String(36), comment="来源案例ID（对应 iptc_main.iptc_cases.id）")
    relevance_reason = Column(Text, comment="与案例的关联理由（AI提取）")
    is_verified = Column(Boolean, default=False, comment="是否已人工审核")
    is_active = Column(Boolean, default=True, comment="是否启用")
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    # 关系
    submissions = relationship("PracticeSubmission", back_populates="venue")

    __table_args__ = (
        {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}
    )


class PracticeSubmission(Base):
    """实践提交表"""
    __tablename__ = "practice_submissions"

    id = Column(String(36), primary_key=True, comment="提交ID")
    plan_id = Column(String(36), ForeignKey('practice_plans.id', ondelete='CASCADE'), nullable=False, index=True, comment="方案ID")
    user_id = Column(String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True, comment="学生ID")
    practice_type = Column(_enum(PracticeType), nullable=False, comment="实践类型")
    title = Column(String(200), nullable=False, comment="提交标题")
    content = Column(Text, nullable=False, comment="实践内容描述")
    reflection = Column(Text, comment="学生建议")
    files = Column(JSON, comment="附件列表")
    venue_id = Column(String(36), ForeignKey('venues.id', ondelete='SET NULL'), comment="实践场馆ID")
    # 基本信息字段
    result_form = Column(String(100), comment="成果形式（逗号分隔：文本图片,音频视频,实物,其他）")
    class_name_id = Column(String(200), comment="班级姓名学号")
    showcase_preference = Column(String(20), default="original", comment="公众号展示偏好: none/original/anonymous")
    instructor_name = Column(String(100), comment="任课教师姓名")
    completion_date = Column(DateTime, comment="完成日期")
    status = Column(_enum(SubmissionStatus), default=SubmissionStatus.DRAFT, nullable=False, index=True, comment="提交状态")
    is_showcased = Column(Boolean, default=False, comment="是否展示在优秀作品墙")
    submitted_at = Column(DateTime, comment="提交时间")
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    # 关系
    plan = relationship("PracticePlan", back_populates="submissions")
    user = relationship("User", back_populates="submissions")
    venue = relationship("Venue", back_populates="submissions")
    review = relationship("PracticeReview", back_populates="submission", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}
    )


class PracticeReview(Base):
    """审核记录表"""
    __tablename__ = "practice_reviews"

    id = Column(String(36), primary_key=True, comment="审核ID")
    submission_id = Column(String(36), ForeignKey('practice_submissions.id', ondelete='CASCADE'), nullable=False, index=True, comment="提交ID")
    reviewer_id = Column(String(36), ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True, comment="审核教师ID")
    status = Column(_enum(SubmissionStatus), nullable=False, comment="审核结果")
    score = Column(Integer, comment="评分 (0-100)")
    comment = Column(Text, comment="评语")
    reviewed_at = Column(DateTime, default=datetime.now, nullable=False, comment="审核时间")
    created_at = Column(DateTime, default=datetime.now, nullable=False)

    # 关系
    submission = relationship("PracticeSubmission", back_populates="review")
    reviewer = relationship("User", back_populates="reviews")

    __table_args__ = (
        {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}
    )


class SubmissionAnnotation(Base):
    """提交批注表"""
    __tablename__ = "submission_annotations"

    id = Column(String(36), primary_key=True, comment="批注ID")
    submission_id = Column(String(36), ForeignKey('practice_submissions.id', ondelete='CASCADE'), nullable=False, index=True, comment="提交ID")
    reviewer_id = Column(String(36), ForeignKey('users.id', ondelete='SET NULL'), nullable=True, comment="批注教师ID")
    content = Column(Text, nullable=False, comment="批注内容")
    target_text = Column(Text, comment="被批注的原文片段")
    position = Column(JSON, comment="批注位置信息 {section, start, end}")
    created_at = Column(DateTime, default=datetime.now, nullable=False)

    # 关系
    submission = relationship("PracticeSubmission", backref=backref("annotations", cascade="all, delete-orphan"))
    reviewer = relationship("User")

    __table_args__ = (
        {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'}
    )
