# -*- coding: utf-8 -*-

"""
Celery Configuration
从config.yaml读取Celery配置并转换为Celery格式
"""

import os
import logging
from kombu import Queue, Exchange

# 直接使用ConfigManager加载配置（Celery启动时GlobalConfig可能未初始化）
from backend.config import ConfigManager

logger = logging.getLogger(__name__)

# 创建独立的ConfigManager实例并加载配置
config_manager = ConfigManager()
if not config_manager.load_config('config.yaml'):
    logger.error("Config manager not initialized")
    raise RuntimeError("Failed to load config.yaml")

config = config_manager.get_config()
celery_config = config.get('celery', {})

# ========================
# Broker Configuration
# ========================
broker_url = celery_config.get('broker', {}).get('url', 'redis://localhost:6379/1')
broker_connection_retry_on_startup = True

# ========================
# Result Backend Configuration
# ========================
result_backend = celery_config.get('result_backend', {}).get('url', 'redis://localhost:6379/2')
result_expires = celery_config.get('result_backend', {}).get('result_expires', 3600)

# ========================
# Serialization
# ========================
task_serializer = celery_config.get('task', {}).get('serializer', 'json')
result_serializer = celery_config.get('task', {}).get('result_serializer', 'json')
accept_content = celery_config.get('task', {}).get('accept_content', ['json'])
timezone = 'Asia/Shanghai'
enable_utc = False

# ========================
# Task Execution
# ========================
task_acks_late = celery_config.get('task', {}).get('acks_late', True)
task_reject_on_worker_lost = celery_config.get('task', {}).get('reject_on_worker_lost', True)

# ========================
# Worker Configuration
# ========================
worker_prefetch_multiplier = celery_config.get('worker', {}).get('prefetch_multiplier', 1)
worker_max_tasks_per_child = celery_config.get('worker', {}).get('max_tasks_per_child', 1000)
worker_pool = celery_config.get('worker', {}).get('pool', 'prefork')
worker_concurrency = celery_config.get('worker', {}).get('concurrency', 4)

# ========================
# Task Time Limits
# ========================
task_time_limit = 3600  # 默认1小时硬限制
task_soft_time_limit = 3300  # 默认55分钟软限制

# 特定任务时间限制
task_time_limits = celery_config.get('task_time_limits', {})

# ========================
# Task Routing
# ========================
# 定义队列
task_queues = (
    Queue('default', Exchange('default'), routing_key='default', priority=5),
    Queue('collector', Exchange('collector'), routing_key='collector', priority=3),
    Queue('report', Exchange('report'), routing_key='report', priority=9),
)

# 默认队列
task_default_queue = 'default'
task_default_exchange = 'default'
task_default_routing_key = 'default'

# 任务路由规则
task_routes = celery_config.get('task_routes', {})

# ========================
# Beat Schedule (从beat_schedule.py导入)
# ========================
try:
    from backend.tasks.beat_schedule import beat_schedule
except Exception as e:
    logger.error(f"加载beat_schedule失败: {e}")
    beat_schedule = {}

# ========================
# Beat Scheduler (使用非持久化调度器，避免Windows下的dbm兼容性问题)
# ========================
beat_scheduler = 'celery.beat:Scheduler'

# ========================
# Logging
# ========================
worker_log_format = '[%(asctime)s: %(levelname)s/%(processName)s] %(message)s'
worker_task_log_format = '[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s'

# ========================
# Monitoring
# ========================
worker_send_task_events = True
task_send_sent_event = True

# ========================
# Imports
# ========================
# 启动时自动导入的模块（包含所有任务定义）
imports = (
    'backend.tasks.collector_tasks',
    'backend.tasks.ai_report_tasks',
)
