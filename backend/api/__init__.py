# -*- coding: utf-8 -*-

"""
消息平台API模块
提供标准化的RESTful API接口
"""

from fastapi import APIRouter

# API版本前缀
API_PREFIX = "/api/v1"

# 创建主路由器
api_router = APIRouter()

__all__ = ["api_router", "API_PREFIX"]