# -*- coding: utf-8 -*-

"""
认证相关的Pydantic Schema
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class LoginRequest(BaseModel):
    """登录请求"""
    username: str = Field(..., description="用户名（学号/工号）")
    password: str = Field(..., description="密码")


class LoginResponse(BaseModel):
    """登录响应"""
    access_token: str = Field(..., description="访问令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    expires_in: int = Field(..., description="过期时间（秒）")
    user: "UserInfo"


class UserInfo(BaseModel):
    """用户信息"""
    id: str
    username: str
    real_name: str
    role: str
    email: Optional[str] = None
    phone: Optional[str] = None
    department: Optional[str] = None
    class_name: Optional[str] = None
    teacher_id: Optional[str] = None
    major: Optional[str] = None
    interests: Optional[str] = None
    created_at: datetime
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ChangePasswordRequest(BaseModel):
    """修改密码请求"""
    old_password: str = Field(..., description="旧密码")
    new_password: str = Field(..., min_length=6, description="新密码（至少6位）")


class RegisterRequest(BaseModel):
    """注册请求（管理员创建用户）"""
    username: str = Field(..., description="用户名（学号/工号）")
    password: str = Field(..., min_length=6, description="密码（至少6位）")
    real_name: str = Field(..., description="真实姓名")
    role: str = Field(..., description="角色（student/teacher/admin）")
    email: Optional[str] = None
    phone: Optional[str] = None
    department: Optional[str] = None
    class_name: Optional[str] = None
    teacher_id: Optional[str] = Field(None, description="指导教师ID（学生注册时可选）")
    major: Optional[str] = Field(None, description="专业")
    interests: Optional[str] = Field(None, description="兴趣爱好/特长")


class ProfileUpdateRequest(BaseModel):
    """个人资料更新请求"""
    major: Optional[str] = Field(None, description="专业")
    interests: Optional[str] = Field(None, description="兴趣爱好/特长")
    department: Optional[str] = Field(None, description="院系/部门")
    email: Optional[str] = Field(None, description="邮箱")
    phone: Optional[str] = Field(None, description="手机号")


# 更新前向引用
LoginResponse.model_rebuild()
