# -*- coding: utf-8 -*-

"""
案例生成与场馆同步 Celery 任务
"""

import logging
from datetime import datetime
from typing import Dict, Any

from backend.tasks import app, run_async_task

logger = logging.getLogger(__name__)


@app.task(
    name='backend.tasks.case_tasks.run_batch_match_cases',
    bind=True,
    max_retries=1,
    default_retry_delay=1800,
    time_limit=10800,
    soft_time_limit=10200,
)
def run_batch_match_cases(self) -> Dict[str, Any]:
    """
    批量撞库案例生成任务（每周一 03:00 执行）
    """
    start_time = datetime.now()
    logger.info("【案例生成】开始批量撞库任务")

    try:
        from backend.scripts.batch_match_cases import BatchMatchCasesService
        service = BatchMatchCasesService()
        result = service.run_batch_match()

        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"【案例生成】完成，耗时 {duration:.1f}s，结果: {result.get('status')}")
        result['duration_seconds'] = duration
        return result

    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        logger.error(f"【案例生成】失败: {e}", exc_info=True)

        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)

        return {'status': 'error', 'error': str(e), 'duration_seconds': duration}


@app.task(
    name='backend.tasks.case_tasks.run_venue_sync_from_cases',
    bind=True,
    max_retries=1,
    default_retry_delay=600,
    time_limit=3600,
    soft_time_limit=3300,
)
def run_venue_sync_from_cases(self) -> Dict[str, Any]:
    """
    从案例中提取场馆信息并同步到 iptc_practice.venues（每周一 04:00 执行）
    """
    start_time = datetime.now()
    logger.info("【场馆同步】开始从案例提取场馆信息")

    try:
        from backend.services.venue_sync_service import VenueSyncService

        async def _run():
            service = VenueSyncService()
            return await service.sync_venues_from_cases()

        result = run_async_task(_run())

        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"【场馆同步】完成，耗时 {duration:.1f}s")
        return {'status': 'success', 'duration_seconds': duration, **(result or {})}

    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        logger.error(f"【场馆同步】失败: {e}", exc_info=True)

        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)

        return {'status': 'error', 'error': str(e), 'duration_seconds': duration}
