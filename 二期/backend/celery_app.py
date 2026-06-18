# -*- coding: utf-8 -*-

"""
Celery配置
"""

from celery import Celery
import os
from dotenv import load_dotenv

load_dotenv()

# 创建Celery应用
celery_app = Celery(
    "iptc_practice",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2"),
    include=["tasks.plan_generation"]
)

# 配置
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5分钟超时
    result_expires=3600,  # 结果保留1小时
)
