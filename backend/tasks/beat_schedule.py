# -*- coding: utf-8 -*-

"""
Celery Beat Schedule
定时任务调度配置（动态从数据库加载）
"""

import logging
from datetime import timedelta
from celery.schedules import crontab, schedule

from backend.database.connection import create_session
from backend.database.entities import MessageSource

logger = logging.getLogger(__name__)


def get_beat_schedule():
    """
    动态生成Celery Beat调度配置

    从数据库读取激活的消息源，为每个source创建周期性任务

    Returns:
        调度配置字典
    """
    beat_schedule = {}

    try:
        # 1. 从数据库加载激活的消息源
        with create_session() as db:
            active_sources = db.query(MessageSource).filter(
                MessageSource.is_active == True
            ).all()

            logger.info(f"【Beat调度】加载到 {len(active_sources)} 个激活消息源")

            # 2. 为每个消息源创建周期性任务
            for source in active_sources:
                source_config = source.config or {}
                interval_seconds = source_config.get('interval', 300)  # 默认5分钟

                # 任务名称（唯一标识）
                task_name = f"collector_{source.name}"

                # 调度配置
                beat_schedule[task_name] = {
                    'task': 'backend.tasks.collector_tasks.run_collector',
                    'schedule': timedelta(seconds=interval_seconds),
                    'args': (source.name,),  # 传递source_name参数
                    'options': {
                        'queue': 'collector',  # 路由到collector队列
                        'priority': 3,  # 中等优先级
                    }
                }

                logger.debug(
                    f"【Beat调度】注册采集任务: {source.display_name or source.name} "
                    f"(间隔: {interval_seconds}秒)"
                )

    except Exception as e:
        logger.error(f"【Beat调度】加载消息源失败: {e}", exc_info=True)

    # 3. 添加AI日报定时任务（固定时间）
    beat_schedule.update({
        # AI治理日报（每天早上8:00）
        'ai_report_governance_daily': {
            'task': 'backend.tasks.ai_report_tasks.generate_daily_report',
            'schedule': crontab(hour=8, minute=0),
            'args': ('governance', None),
            'options': {
                'queue': 'report',
                'priority': 9,  # 高优先级
            }
        },

        # AI科技日报（每天早上8:10）
        'ai_report_research_daily': {
            'task': 'backend.tasks.ai_report_tasks.generate_daily_report',
            'schedule': crontab(hour=8, minute=10),
            'args': ('research', None),
            'options': {
                'queue': 'report',
                'priority': 9,
            }
        },

        # AI产业日报（每天早上8:20）
        'ai_report_industry_daily': {
            'task': 'backend.tasks.ai_report_tasks.generate_daily_report',
            'schedule': crontab(hour=8, minute=20),
            'args': ('industry', None),
            'options': {
                'queue': 'report',
                'priority': 9,
            }
        },
    })

    logger.info(f"【Beat调度】调度配置生成完成（共 {len(beat_schedule)} 个任务）")
    return beat_schedule


# ========================
# 导出调度配置（供celeryconfig.py导入）
# ========================
# 注意：这个函数会在Celery Beat启动时被调用，动态生成调度配置
beat_schedule = get_beat_schedule()
