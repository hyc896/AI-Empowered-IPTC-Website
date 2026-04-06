# -*- coding: utf-8 -*-

"""
认证相关API路由
"""

from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel

from database import get_db
from database.entities import User, UserRole
from services.auth_service import AuthService
from schemas.auth import LoginRequest, LoginResponse, UserInfo, ChangePasswordRequest, RegisterRequest, ProfileUpdateRequest

router = APIRouter()


def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    依赖注入：获取当前登录用户

    Args:
        authorization: Authorization header (Bearer token)
        db: 数据库会话

    Returns:
        当前用户对象

    Raises:
        HTTPException: 未提供token或token无效
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证凭证",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 提取token（格式：Bearer <token>）
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise ValueError
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭证格式",
            headers={"WWW-Authenticate": "Bearer"},
        )

    auth_service = AuthService(db)
    return auth_service.get_current_user(token)


@router.post("/login", response_model=LoginResponse, summary="用户登录")
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    用户登录接口

    - **username**: 用户名（学号/工号）
    - **password**: 密码

    返回JWT token和用户信息
    """
    auth_service = AuthService(db)
    return auth_service.login(request)


@router.post("/logout", summary="用户登出")
def logout(current_user = Depends(get_current_user)):
    """
    用户登出接口

    需要提供有效的JWT token
    """
    return {"message": "登出成功"}


@router.get("/me", response_model=UserInfo, summary="获取当前用户信息")
def get_me(current_user = Depends(get_current_user)):
    """
    获取当前登录用户的信息

    需要提供有效的JWT token
    """
    return UserInfo.from_orm(current_user)


@router.post("/change-password", summary="修改密码")
def change_password(
    request: ChangePasswordRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    修改当前用户密码

    - **old_password**: 旧密码
    - **new_password**: 新密码（至少6位）

    需要提供有效的JWT token
    """
    auth_service = AuthService(db)
    return auth_service.change_password(current_user, request)


@router.post("/register", response_model=UserInfo, summary="注册用户（管理员）")
def register(
    request: RegisterRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    注册新用户（仅管理员可用）

    - **username**: 用户名（学号/工号）
    - **password**: 密码（至少6位）
    - **real_name**: 真实姓名
    - **role**: 角色（student/teacher/admin）
    - **email**: 邮箱（可选）
    - **phone**: 手机号（可选）
    - **department**: 院系/部门（可选）
    - **class_name**: 班级（可选，学生）

    需要管理员权限
    """
    # 检查权限
    if current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足"
        )

    auth_service = AuthService(db)
    return auth_service.register_user(request)


@router.post("/self-register", response_model=UserInfo, summary="用户自助注册")
def self_register(
    request: RegisterRequest,
    db: Session = Depends(get_db)
):
    """
    用户自助注册（公开接口）

    - **username**: 用户名（学号/工号）
    - **password**: 密码（至少6位）
    - **real_name**: 真实姓名
    - **role**: 角色（student/teacher）
    - **email**: 邮箱（可选）
    - **phone**: 手机号（可选）
    - **department**: 院系/部门（可选）
    - **class_name**: 班级（可选，学生）

    无需登录即可注册
    """
    auth_service = AuthService(db)
    return auth_service.self_register(request)


class TeacherBrief(BaseModel):
    """教师简要信息"""
    id: str
    real_name: str
    department: Optional[str] = None

    class Config:
        from_attributes = True


class StudentBrief(BaseModel):
    """学生简要信息"""
    id: str
    username: str
    real_name: str
    class_name: Optional[str] = None

    class Config:
        from_attributes = True



@router.get("/teachers", response_model=List[TeacherBrief], summary="获取教师列表（公开）")
def list_teachers(db: Session = Depends(get_db)):
    """获取所有教师列表，用于学生注册时选择指导教师"""
    teachers = db.query(User).filter(User.role == UserRole.TEACHER, User.is_active == True).all()
    return [TeacherBrief.from_orm(t) for t in teachers]


@router.get("/my-students", response_model=List[StudentBrief], summary="获取我的学生列表")
def get_my_students(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """教师获取自己关联的学生列表"""
    if current_user.role.value not in ["teacher", "admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="权限不足")
    students = db.query(User).filter(User.teacher_id == current_user.id, User.is_active == True).all()
    return [StudentBrief.from_orm(s) for s in students]


@router.put("/update-teacher", summary="修改指导教师")
def update_teacher(
    teacher_id: Optional[str] = None,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """学生修改自己的指导教师"""
    if current_user.role.value != "student":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅学生可修改指导教师")
    current_user.teacher_id = teacher_id
    db.commit()
    return {"message": "指导教师已更新"}


@router.put("/profile", response_model=UserInfo, summary="更新个人资料")
def update_profile(
    request: ProfileUpdateRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """学生更新个人资料（专业、兴趣等）"""
    if request.major is not None:
        current_user.major = request.major
    if request.interests is not None:
        current_user.interests = request.interests
    if request.department is not None:
        current_user.department = request.department
    if request.email is not None:
        current_user.email = request.email
    if request.phone is not None:
        current_user.phone = request.phone
    db.commit()
    db.refresh(current_user)
    return UserInfo.from_orm(current_user)
