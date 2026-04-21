# -*- coding: utf-8 -*-

"""
实践提交相关的Pydantic Schema
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime


class FileInfo(BaseModel):
    """文件信息"""
    filename: Optional[str] = None
    path: str
    type: Optional[str] = None
    size: Optional[int] = None


class ReviewInfo(BaseModel):
    """审核信息（嵌套在提交响应中）"""
    id: str
    status: str
    score: Optional[int] = None
    comment: Optional[str] = None
    reviewer_id: Optional[str] = None
    reviewed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SubmissionCreate(BaseModel):
    """创建提交请求"""
    plan_id: str = Field(..., description="方案ID")
    practice_type: str = Field(..., description="实践类型")
    title: str = Field(..., description="提交标题")
    content: str = Field(..., description="实践内容描述")
    reflection: Optional[str] = Field(None, description="学生建议")
    venue_id: Optional[str] = Field(None, description="实践场馆ID")
    completion_date: Optional[datetime] = Field(None, description="完成日期")
    # 基本信息字段
    result_form: Optional[str] = Field(None, description="成果形式")
    class_name_id: Optional[str] = Field(None, description="班级姓名学号")
    showcase_preference: Optional[str] = Field("original", description="公众号展示偏好")
    instructor_name: Optional[str] = Field(None, description="任课教师姓名")

    @field_validator('completion_date', mode='before')
    @classmethod
    def parse_completion_date(cls, v):
        """处理空字符串和纯日期字符串"""
        if v is None or v == '':
            return None
        if isinstance(v, str) and len(v) == 10:
            # "YYYY-MM-DD" → 添加时间部分
            return f"{v}T00:00:00"
        return v

    @field_validator('venue_id', 'reflection', 'result_form', 'class_name_id', 'instructor_name', mode='before')
    @classmethod
    def empty_str_to_none(cls, v):
        """将空字符串转为None"""
        if v == '':
            return None
        return v


class SubmissionUpdate(BaseModel):
    """更新提交请求"""
    title: Optional[str] = None
    content: Optional[str] = None
    reflection: Optional[str] = None
    venue_id: Optional[str] = None
    completion_date: Optional[datetime] = None
    result_form: Optional[str] = None
    class_name_id: Optional[str] = None
    showcase_preference: Optional[str] = None
    instructor_name: Optional[str] = None

    @field_validator('completion_date', mode='before')
    @classmethod
    def parse_completion_date(cls, v):
        """处理空字符串和纯日期字符串"""
        if v is None or v == '':
            return None
        if isinstance(v, str) and len(v) == 10:
            return f"{v}T00:00:00"
        return v

    @field_validator('venue_id', 'reflection', 'result_form', 'class_name_id', 'instructor_name', mode='before')
    @classmethod
    def empty_str_to_none(cls, v):
        """将空字符串转为None"""
        if v == '':
            return None
        return v


class SubmissionResponse(BaseModel):
    """提交响应"""
    id: str
    plan_id: str
    user_id: str
    user_name: Optional[str] = None
    practice_type: str
    title: str
    content: str
    reflection: Optional[str] = None
    files: Optional[List[FileInfo]] = None
    venue_id: Optional[str] = None
    completion_date: Optional[datetime] = None
    status: str
    is_showcased: bool = False
    submitted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    # 基本信息
    result_form: Optional[str] = None
    class_name_id: Optional[str] = None
    showcase_preference: Optional[str] = None
    instructor_name: Optional[str] = None
    # 审核信息
    review: Optional[ReviewInfo] = None

    class Config:
        from_attributes = True


class SubmissionListResponse(BaseModel):
    """提交列表响应"""
    total: int
    items: List[SubmissionResponse]


class FileUploadResponse(BaseModel):
    """文件上传响应"""
    file_id: str
    filename: str
    path: str
    size: int
    type: str
