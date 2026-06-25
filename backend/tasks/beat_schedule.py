# -*- coding: utf-8 -*-

"""
Celery Beat Schedule
定时任务调度配置

定时任务清单：
- 采集器任务：从数据库动态加载 is_active=1 的消息源
- 案例生成任务：每周一 03:00 执行 batch_match_cases
- 场馆同步任务：每周一 04:00 执行 venue_sync_from_cases
"""

import logging
import os
from datetime import timedelta
from celery.schedules import crontab

logger = logging.getLogger(__name__)


def _env_enabled(name: str, default: str = "1") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def _get_collector_tasks() -> dict:
    """
    获取采集器定时任务配置（动态从数据库加载）

    Returns:
        采集器任务调度配置字典
    """
    collector_tasks = {}

    try:
        from backend.database.connection import create_session
        from backend.database.entities import MessageSource

        with create_session() as db:
            active_sources = db.query(MessageSource).filter(
                MessageSource.is_active == True
            ).all()

            logger.info(f"【Beat调度】加载到 {len(active_sources)} 个激活消息源")

            for source in active_sources:
                source_config = source.config or {}
                if not source_config.get('auto_collect_enabled', True):
                    logger.info(f"【Beat调度】跳过自动采集源: {source.display_name or source.name}")
                    continue

                interval_seconds = source_config.get('interval', 300)

                task_name = f"collector_{source.name}"
                collector_tasks[task_name] = {
                    'task': 'backend.tasks.collector_tasks.run_collector',
                    'schedule': timedelta(seconds=interval_seconds),
                    'args': (source.name,),
                    'options': {
                        'queue': 'collector',
                        'priority': 3,
                    }
                }

    except Exception as e:
        logger.error(f"【Beat调度】加载消息源失败（采集器任务不可用）: {e}")
        logger.warning("【Beat调度】案例生成任务不受影响")

    return collector_tasks


def get_beat_schedule() -> dict:
    """
    生成 Celery Beat 调度配置

    Returns:
        完整的调度配置字典
    """
    beat_schedule = {}

    # 1. 批量案例生成任务（每周一 03:00）
    beat_schedule['batch_match_cases_weekly'] = {
        'task': 'backend.tasks.case_tasks.run_batch_match_cases',
        'schedule': crontab(hour=3, minute=0, day_of_week=1),
        'options': {'queue': 'default'},
    }

    # 2. 场馆同步任务（每周一 04:00，在案例生成后执行）
    beat_schedule['venue_sync_from_cases_weekly'] = {
        'task': 'backend.tasks.case_tasks.run_venue_sync_from_cases',
        'schedule': crontab(hour=4, minute=0, day_of_week=1),
        'options': {'queue': 'default'},
    }

    # 3. 采集器任务（动态加载，可能失败，不影响上面两个任务）
    if _env_enabled("COLLECTOR_SCHEDULE_ENABLED", "1"):
        collector_tasks = _get_collector_tasks()
        beat_schedule.update(collector_tasks)
    else:
        collector_tasks = {}
        logger.info("[Beat] Collector schedules disabled by COLLECTOR_SCHEDULE_ENABLED")

    logger.info(f"【Beat调度】配置完成 — 固定任务: 2, 采集器任务: {len(collector_tasks)}")

    return beat_schedule


_startup_triggered = False


def trigger_startup_collectors():
    """Beat 启动时触发所有采集器（仅调用一次）"""
    global _startup_triggered
    if not _env_enabled("COLLECTOR_TRIGGER_ON_STARTUP", "0"):
        logger.info("[Beat] Startup collector trigger disabled by COLLECTOR_TRIGGER_ON_STARTUP")
        return

    if _startup_triggered:
        return

    _startup_triggered = True

    try:
        from backend.tasks.collector_tasks import trigger_all_collectors
        result = trigger_all_collectors.apply_async(queue='default')
        logger.info(f"【Beat启动】已触发启动任务: {result.id}")
    except Exception as e:
        logger.error(f"【Beat启动】触发启动任务失败: {e}")


beat_schedule = get_beat_schedule()
