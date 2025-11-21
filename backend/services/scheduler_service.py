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

    async def _generate_comprehensive_report_job(self):
        """
        定时任务：生成AI综合日报

        每天凌晨2点自动执行
        """
        logger.info("【Scheduler】开始执行AI综合日报生成任务")

        try:
            report_generator = get_report_generator()
            report_id = await report_generator.generate_daily_report(report_type='comprehensive')

            if report_id:
                logger.info(f"【Scheduler】AI综合日报生成成功（ID: {report_id}）")
            else:
                logger.warning("【Scheduler】AI综合日报生成失败或无数据")

        except Exception as e:
            logger.error(f"【Scheduler】AI综合日报生成任务异常: {e}", exc_info=True)

    async def _generate_industry_report_job(self):
        """
        定时任务：生成AI产业日报

        每天早上7点自动执行
        """
        logger.info("【Scheduler】开始执行AI产业日报生成任务")

        try:
            report_generator = get_report_generator()
            report_id = await report_generator.generate_industry_report()

            if report_id:
                logger.info(f"【Scheduler】AI产业日报生成成功（ID: {report_id}）")
            else:
                logger.warning("【Scheduler】AI产业日报生成失败或无数据")

        except Exception as e:
            logger.error(f"【Scheduler】AI产业日报生成任务异常: {e}", exc_info=True)

    async def _generate_governance_report_job(self):
        """
        定时任务：生成AI治理日报

        每天中午12点自动执行
        """
        logger.info("【Scheduler】开始执行AI治理日报生成任务")

        try:
            report_generator = get_report_generator()
            report_id = await report_generator.generate_governance_report()

            if report_id:
                logger.info(f"【Scheduler】AI治理日报生成成功（ID: {report_id}）")
            else:
                logger.warning("【Scheduler】AI治理日报生成失败或无数据")

        except Exception as e:
            logger.error(f"【Scheduler】AI治理日报生成任务异常: {e}", exc_info=True)

    async def _generate_research_report_job(self):
        """
        定时任务：生成AI科研日报

        每天下午13点自动执行
        """
        logger.info("【Scheduler】开始执行AI科研日报生成任务")

        try:
            report_generator = get_report_generator()
            report_id = await report_generator.generate_research_report()

            if report_id:
                logger.info(f"【Scheduler】AI科研日报生成成功（ID: {report_id}）")
            else:
                logger.warning("【Scheduler】AI科研日报生成失败或无数据")

        except Exception as e:
            logger.error(f"【Scheduler】AI科研日报生成任务异常: {e}", exc_info=True)

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

        # 注册任务1：每天凌晨2点生成AI综合日报
        self.scheduler.add_job(
            self._generate_comprehensive_report_job,
            trigger=CronTrigger(hour=2, minute=0),
            id='generate_comprehensive_report',
            name='生成AI综合日报',
            replace_existing=True
        )

        # 注册任务2：每天早上7点生成AI产业日报
        self.scheduler.add_job(
            self._generate_industry_report_job,
            trigger=CronTrigger(hour=7, minute=0),
            id='generate_industry_report',
            name='生成AI产业日报',
            replace_existing=True
        )

        # 注册任务3：每天中午12点生成AI治理日报
        self.scheduler.add_job(
            self._generate_governance_report_job,
            trigger=CronTrigger(hour=12, minute=0),
            id='generate_governance_report',
            name='生成AI治理日报',
            replace_existing=True
        )

        # 注册任务4：每天下午13点生成AI科研日报
        self.scheduler.add_job(
            self._generate_research_report_job,
            trigger=CronTrigger(hour=13, minute=0),
            id='generate_research_report',
            name='生成AI科研日报',
            replace_existing=True
        )

        logger.info("【Scheduler】已注册任务：")
        logger.info("  - 生成AI综合日报: 每天02:00执行")
        logger.info("  - 生成AI产业日报: 每天07:00执行")
        logger.info("  - 生成AI治理日报: 每天12:00执行")
        logger.info("  - 生成AI科研日报: 每天13:00执行")

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
