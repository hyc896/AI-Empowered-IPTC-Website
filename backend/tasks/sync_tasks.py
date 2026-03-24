# -*- coding: utf-8 -*-

"""
消息同步 Celery 任务
从 message_platform 获取消息并同步到本地
"""

import logging
from backend.tasks import app
from backend.services.message_platform_client import MessagePlatformClient
from backend.services.message_sync_service import MessageSyncService

logger = logging.getLogger(__name__)


@app.task(name='sync_messages_from_platform', bind=True)
def sync_messages_from_platform(self):
    """
    从 message_platform 同步消息

    每2小时执行一次，获取最近3小时的消息
    """
    try:
        logger.info("【同步任务】开始从 message_platform 同步消息")

        # 1. 获取消息
        client = MessagePlatformClient()
        messages = client.fetch_recent_messages(hours=3, limit=1000)

        if not messages:
            logger.warning("【同步任务】未获取到消息")
            return {'success': 0, 'duplicate': 0, 'error': 0}

        # 2. 同步到本地
        sync_service = MessageSyncService()
        stats = sync_service.sync_messages(messages)

        logger.info(f"【同步任务】完成: 成功{stats['success']}, 重复{stats['duplicate']}, 失败{stats['error']}")
        return stats

    except Exception as e:
        logger.error(f"【同步任务】失败: {e}", exc_info=True)
        raise
