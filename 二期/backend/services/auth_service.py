# -*- coding: utf-8 -*-

"""
认证服务
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from database.entities import User, UserRole
from utils.password_hasher import hash_password, verify_password
from utils.jwt_handler import create_access_token, decode_access_token
from schemas.auth import LoginRequest, LoginResponse, UserInfo, ChangePasswordRequest, RegisterRequest


class AuthService:
    """认证服务类"""

    def __init__(self, db: Session):
        self.db = db

    def login(self, request: LoginRequest) -> LoginResponse:
        """
        用户登录

        Args:
            request: 登录请求

        Returns:
            登录响应（包含token和用户信息）

        Raises:
            HTTPException: 用户名或密码错误
        """
        # 查询用户
        user = self.db.query(User).filter(User.username == request.username).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="该用户未注册，请先注册"
            )

        # 验证密码
        if not verify_password(request.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="密码错误"
            )

        # 检查用户是否激活
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="用户已被禁用"
            )

        # 更新最后登录时间
        user.last_login_at = datetime.now()
        self.db.commit()

        # 生成JWT token
        token_data = {
            "user_id": user.id,
            "username": user.username,
            "role": user.role.value
        }
        access_token = create_access_token(token_data)

        # 返回登录响应
        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=86400,  # 24小时
            user=UserInfo.from_orm(user)
        )

    def get_current_user(self, token: str) -> User:
        """
        根据token获取当前用户

        Args:
            token: JWT token

        Returns:
            用户对象

        Raises:
            HTTPException: token无效或用户不存在
        """
        # 解码token
        payload = decode_access_token(token)

        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的认证凭证",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user_id = payload.get("user_id")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的认证凭证",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 查询用户
        user = self.db.query(User).filter(User.id == user_id).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户不存在"
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="用户已被禁用"
            )

        return user

    def change_password(self, user: User, request: ChangePasswordRequest) -> dict:
        """
        修改密码

        Args:
            user: 当前用户
            request: 修改密码请求

        Returns:
            成功消息

        Raises:
            HTTPException: 旧密码错误
        """
        # 验证旧密码
        if not verify_password(request.old_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="旧密码错误"
            )

        # 更新密码
        user.password_hash = hash_password(request.new_password)
        user.updated_at = datetime.now()
        self.db.commit()

        return {"message": "密码修改成功"}

    def register_user(self, request: RegisterRequest) -> UserInfo:
        """
        注册用户（管理员功能）

        Args:
            request: 注册请求

        Returns:
            用户信息

        Raises:
            HTTPException: 用户名已存在
        """
        # 检查用户名是否已存在
        existing_user = self.db.query(User).filter(User.username == request.username).first()

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户名已存在"
            )

        # 创建新用户
        new_user = User(
            id=str(uuid.uuid4()),
            username=request.username,
            password_hash=hash_password(request.password),
            real_name=request.real_name,
            role=UserRole(request.role),
            email=request.email,
            phone=request.phone,
            department=request.department,
            class_name=request.class_name,
            teacher_id=request.teacher_id,
            major=request.major,
            interests=request.interests,
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        self.db.add(new_user)
        self.db.commit()
        self.db.refresh(new_user)

        return UserInfo.from_orm(new_user)

    def self_register(self, request: RegisterRequest) -> UserInfo:
        """
        用户自助注册（公开接口）

        Args:
            request: 注册请求

        Returns:
            用户信息

        Raises:
            HTTPException: 用户名已存在
        """
        # 检查用户名是否已存在
        existing_user = self.db.query(User).filter(User.username == request.username).first()

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="该学号/工号已注册"
            )

        # 创建新用户
        new_user = User(
            id=str(uuid.uuid4()),
            username=request.username,
            password_hash=hash_password(request.password),
            real_name=request.real_name,
            role=UserRole(request.role),
            email=request.email,
            phone=request.phone,
            department=request.department,
            class_name=request.class_name,
            teacher_id=request.teacher_id,
            major=request.major,
            interests=request.interests,
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        self.db.add(new_user)
        self.db.commit()
        self.db.refresh(new_user)

        return UserInfo.from_orm(new_user)
