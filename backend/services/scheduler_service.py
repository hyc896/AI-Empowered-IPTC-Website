# -*- coding: utf-8 -*-

"""
Scheduler Service
使用APScheduler管理定时任务
"""

import asyncio
import logging
from typing import Optional
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

from backend.services.ai_report_generator import get_report_generator

logger = logging.getLogger(__name__)


class SchedulerService:
    """
    调度服务

    管理所有定时任务，包括：
    - AI日报生成（每晚8点）
    - 其他定时任务...
    """

    def __init__(self):
        """初始化调度器"""
        self.scheduler: Optional[AsyncIOScheduler] = None
        self.is_running = False

    def _job_listener(self, event):
        """
        任务执行监听器

        Args:
            event: APScheduler事件
        """
        if event.exception:
            logger.error(
                f"【Scheduler】任务执行失败: {event.job_id}",
                exc_info=event.exception
            )
        else:
            logger.info(f"【Scheduler】任务执行成功: {event.job_id}")

    async def _generate_daily_report_job(self):
        """
        定时任务：生成AI日报

        每晚8点自动执行
        """
        logger.info("【Scheduler】开始执行AI日报生成任务")

        try:
            report_generator = get_report_generator()
            report_id = await report_generator.generate_daily_report()

            if report_id:
                logger.info(f"【Scheduler】AI日报生成成功（ID: {report_id}）")
            else:
                logger.warning("【Scheduler】AI日报生成失败或无数据")

        except Exception as e:
            logger.error(f"【Scheduler】AI日报生成任务异常: {e}", exc_info=True)

    def start(self):
        """
        启动调度器

        注册所有定时任务并启动调度器
        """
        if self.is_running:
            logger.warning("【Scheduler】调度器已在运行中")
            return

        logger.info("【Scheduler】初始化调度器...")

        # 创建AsyncIOScheduler
        self.scheduler = AsyncIOScheduler(
            timezone='Asia/Shanghai',
            job_defaults={
                'coalesce': True,  # 合并堆积的任务
                'max_instances': 1,  # 同一任务最多1个实例
                'misfire_grace_time': 3600  # 容忍1小时的延迟执行
            }
        )

        # 添加任务监听器
        self.scheduler.add_listener(
            self._job_listener,
            EVENT_JOB_EXECUTED | EVENT_JOB_ERROR
        )

        # 注册任务：每晚8点生成AI日报
        self.scheduler.add_job(
            self._generate_daily_report_job,
            trigger=CronTrigger(hour=20, minute=0),  # 每晚20:00
            id='generate_ai_daily_report',
            name='生成AI日报',
            replace_existing=True
        )

        logger.info("【Scheduler】已注册任务：")
        logger.info("  - 生成AI日报: 每晚20:00执行")

        # 启动调度器
        self.scheduler.start()
        self.is_running = True

        logger.info("【Scheduler】调度器启动成功")

    def shutdown(self, wait: bool = True):
        """
        关闭调度器

        Args:
            wait: 是否等待正在执行的任务完成
        """
        if not self.is_running or self.scheduler is None:
            logger.warning("【Scheduler】调度器未运行")
            return

        logger.info("【Scheduler】正在关闭调度器...")

        self.scheduler.shutdown(wait=wait)
        self.is_running = False

        logger.info("【Scheduler】调度器已关闭")

    def get_scheduled_jobs(self):
        """
        获取所有已调度的任务

        Returns:
            任务列表
        """
        if self.scheduler is None:
            return []

        jobs = self.scheduler.get_jobs()
        return [
            {
                'id': job.id,
                'name': job.name,
                'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
                'trigger': str(job.trigger)
            }
            for job in jobs
        ]

    async def trigger_daily_report_now(self):
        """
        手动触发AI日报生成（用于测试或手动执行）

        Returns:
            报告ID
        """
        logger.info("【Scheduler】手动触发AI日报生成")
        return await self._generate_daily_report_job()


# 全局单例
_scheduler_service = None


def get_scheduler_service() -> SchedulerService:
    """获取全局调度服务实例"""
    global _scheduler_service
    if _scheduler_service is None:
        _scheduler_service = SchedulerService()
    return _scheduler_service
