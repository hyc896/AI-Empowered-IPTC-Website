# -*- coding: utf-8 -*-

"""
Celery Beat Schedule
定时任务调度配置

设计原则：
- 日报任务（从config.yaml读取）始终注册，不依赖数据库
- 采集器任务（动态配置）从数据库加载，失败不影响日报任务
"""

import logging
from datetime import timedelta
from celery.schedules import crontab, schedule

from backend.config import ConfigManager

logger = logging.getLogger(__name__)


# ========================
# 日报任务默认配置（当config.yaml未配置时使用）
# ========================
DEFAULT_AI_REPORT_SCHEDULE = {
    'governance': {'hour': 8, 'minute': 0},
    'research': {'hour': 8, 'minute': 10},
    'industry': {'hour': 8, 'minute': 20},
    'comprehensive': {'hour': 8, 'minute': 30},
    'china_ai': {'hour': 8, 'minute': 40},
    'shanghai_weekly': {'hour': 9, 'minute': 0, 'day_of_week': 1},
}


def _load_ai_report_schedule() -> dict:
    """
    从config.yaml加载日报时间配置

    配置路径: celery.beat.ai_report_schedule

    Returns:
        日报时间配置字典
    """
    try:
        config_manager = ConfigManager()
        if not config_manager.load_config('config.yaml'):
            logger.warning("【Beat调度】配置加载失败，使用默认日报时间")
            return DEFAULT_AI_REPORT_SCHEDULE

        config = config_manager.get_config()
        ai_report_schedule = (
            config
            .get('celery', {})
            .get('beat', {})
            .get('ai_report_schedule', {})
        )

        if not ai_report_schedule:
            logger.warning("【Beat调度】未找到ai_report_schedule配置，使用默认时间")
            return DEFAULT_AI_REPORT_SCHEDULE

        logger.info(f"【Beat调度】从config.yaml加载日报时间配置")
        return ai_report_schedule

    except Exception as e:
        logger.error(f"【Beat调度】加载日报配置失败: {e}，使用默认时间")
        return DEFAULT_AI_REPORT_SCHEDULE


def _get_ai_report_tasks() -> dict:
    """
    获取AI日报定时任务配置（从config.yaml读取，始终可用）

    支持日报和周报两种调度模式：
    - 日报：仅配置hour和minute，每天执行
    - 周报：配置hour、minute和day_of_week，每周指定日执行

    Returns:
        日报任务调度配置字典
    """
    report_tasks = {}
    ai_report_schedule = _load_ai_report_schedule()

    for report_type, schedule_config in ai_report_schedule.items():
        hour = schedule_config.get('hour', 8)
        minute = schedule_config.get('minute', 0)
        day_of_week = schedule_config.get('day_of_week')

        if day_of_week is not None:
            task_schedule = crontab(hour=hour, minute=minute, day_of_week=day_of_week)
            task_name = f"ai_report_{report_type}_weekly"
            schedule_desc = f"每周{day_of_week} {hour:02d}:{minute:02d}"
        else:
            task_schedule = crontab(hour=hour, minute=minute)
            task_name = f"ai_report_{report_type}_daily"
            schedule_desc = f"每天 {hour:02d}:{minute:02d}"

        report_tasks[task_name] = {
            'task': 'backend.tasks.ai_report_tasks.generate_daily_report',
            'schedule': task_schedule,
            'args': (report_type, None),
            'options': {
                'queue': 'report',
                'priority': 9,
            }
        }
        logger.info(f"【Beat调度】注册报告任务: {report_type} ({schedule_desc})")

    return report_tasks


def _get_collector_tasks() -> dict:
    """
    获取采集器定时任务配置（动态从数据库加载）

    数据库查询失败时返回空字典，不影响日报任务

    Returns:
        采集器任务调度配置字典
    """
    collector_tasks = {}

    try:
        # 延迟导入，避免模块加载时触发数据库连接
        from backend.database.connection import create_session
        from backend.database.entities import MessageSource

        with create_session() as db:
            active_sources = db.query(MessageSource).filter(
                MessageSource.is_active == True
            ).all()

            logger.info(f"【Beat调度】加载到 {len(active_sources)} 个激活消息源")

            for source in active_sources:
                source_config = source.config or {}
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

                logger.debug(
                    f"【Beat调度】注册采集任务: {source.display_name or source.name} "
                    f"(间隔: {interval_seconds}秒)"
                )

    except Exception as e:
        logger.error(f"【Beat调度】加载消息源失败（采集器任务不可用）: {e}")
        logger.warning("【Beat调度】日报任务不受影响，采集器任务需要手动触发或重启Beat")

    return collector_tasks


_startup_triggered = False

def trigger_startup_collectors():
    """
    Beat启动时触发所有采集器（仅调用一次）

    所有采集器任务直接加入队列排队
    使用全局标记防止模块被多次导入时重复触发
    """
    global _startup_triggered
    if _startup_triggered:
        logger.debug("【Beat启动】启动触发已执行过，跳过")
        return

    _startup_triggered = True

    try:
        from backend.tasks.collector_tasks import trigger_all_collectors

        result = trigger_all_collectors.apply_async(queue='default')
        logger.info(f"【Beat启动】已触发启动任务: {result.id}（所有采集器将加入队列排队）")

    except Exception as e:
        logger.error(f"【Beat启动】触发启动任务失败: {e}")


def get_beat_schedule() -> dict:
    """
    生成Celery Beat调度配置

    执行顺序：
    1. 先注册日报任务（从config.yaml读取，始终成功）
    2. 再尝试加载采集器任务（动态配置，可能失败）

    注意：启动采集触发已移至 Worker 启动信号（__init__.py），
    避免模块导入时意外发送任务

    Returns:
        完整的调度配置字典
    """
    beat_schedule = {}

    # 1. 先注册日报任务（从config.yaml读取，不依赖数据库，始终成功）
    logger.info("【Beat调度】注册日报任务...")
    report_tasks = _get_ai_report_tasks()
    beat_schedule.update(report_tasks)
    logger.info(f"【Beat调度】日报任务注册完成: {len(report_tasks)} 个")

    # 2. 再尝试加载采集器任务（动态配置，可能失败）
    logger.info("【Beat调度】加载采集器任务...")
    collector_tasks = _get_collector_tasks()
    beat_schedule.update(collector_tasks)
    logger.info(f"【Beat调度】采集器任务加载完成: {len(collector_tasks)} 个")

    # 3. 输出调度摘要
    logger.info("=" * 50)
    logger.info(f"【Beat调度】调度配置生成完成")
    logger.info(f"  - 日报任务: {len(report_tasks)} 个")
    logger.info(f"  - 采集器任务: {len(collector_tasks)} 个")
    logger.info(f"  - 总计: {len(beat_schedule)} 个定时任务")
    logger.info("=" * 50)

    return beat_schedule


# ========================
# 导出调度配置（供celeryconfig.py导入）
# ========================
beat_schedule = get_beat_schedule()
