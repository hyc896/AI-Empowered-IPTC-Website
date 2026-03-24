# -*- coding: utf-8 -*-

"""
消息同步服务
从 message_platform 获取消息并同步到本地 MySQL
"""

import uuid
import logging
from typing import List, Dict, Any
from datetime import datetime
from sqlalchemy.exc import IntegrityError

from backend.database.connection import create_session
from backend.database.entities import MessageSource
from backend.database.orm_registry import get_orm_registry

logger = logging.getLogger(__name__)


class MessageSyncService:
    """消息同步服务"""

    def __init__(self):
        self.orm_registry = get_orm_registry()
        self._source_cache = {}  # 缓存 source_name -> source_id 映射

    def _load_source_mapping(self):
        """加载消息源映射"""
        if self._source_cache:
            return

        with create_session() as db:
            sources = db.query(MessageSource).all()
            for source in sources:
                self._source_cache[source.name] = {
                    'id': source.id,
                    'table': source.config.get('mysql_table') if source.config else f"mp_{source.name}_messages"
                }

        logger.info(f"【同步服务】加载 {len(self._source_cache)} 个消息源映射")

    def sync_messages(self, messages: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        同步消息到 MySQL

        Args:
            messages: 消息列表（来自 API）

        Returns:
            统计信息 {success: int, duplicate: int, error: int}
        """
        if not messages:
            return {'success': 0, 'duplicate': 0, 'error': 0}

        self._load_source_mapping()

        stats = {'success': 0, 'duplicate': 0, 'error': 0}

        # 按消息源分组
        grouped = {}
        for msg in messages:
            source_name = msg.get('source_name')
            if not source_name:
                continue
            if source_name not in grouped:
                grouped[source_name] = []
            grouped[source_name].append(msg)

        # 逐个消息源同步
        for source_name, source_messages in grouped.items():
            result = self._sync_source_messages(source_name, source_messages)
            stats['success'] += result['success']
            stats['duplicate'] += result['duplicate']
            stats['error'] += result['error']

        return stats

    def _sync_source_messages(self, source_name: str, messages: List[Dict[str, Any]]) -> Dict[str, int]:
        """同步单个消息源的消息"""
        stats = {'success': 0, 'duplicate': 0, 'error': 0}

        # 获取消息源信息
        source_info = self._source_cache.get(source_name)
        if not source_info:
            logger.warning(f"【同步服务】未找到消息源: {source_name}")
            stats['error'] += len(messages)
            return stats

        # 获取 ORM 模型
        table_name = source_info['table']
        model = self.orm_registry.get_model(table_name)
        if not model:
            logger.warning(f"【同步服务】未找到表模型: {table_name}")
            stats['error'] += len(messages)
            return stats

        # 批量插入
        with create_session() as db:
            for msg in messages:
                try:
                    # 转换数据格式
                    record = model(
                        id=str(uuid.uuid4()),
                        source_id=source_info['id'],
                        external_id=msg.get('id'),
                        title=msg.get('title', ''),
                        content=msg.get('content', ''),
                        summary=msg.get('summary'),
                        provider=msg.get('provider'),
                        published_at=self._parse_datetime(msg.get('published_at')),
                        crawled_at=datetime.now(),
                        url=msg.get('url', '')
                    )

                    db.add(record)
                    db.commit()
                    stats['success'] += 1

                except IntegrityError:
                    db.rollback()
                    stats['duplicate'] += 1
                except Exception as e:
                    db.rollback()
                    logger.error(f"【同步服务】插入失败: {e}")
                    stats['error'] += 1

        logger.info(f"【同步服务】{source_name}: 成功{stats['success']}, 重复{stats['duplicate']}, 失败{stats['error']}")
        return stats

    def _parse_datetime(self, dt_str) -> datetime:
        """解析日期时间"""
        if isinstance(dt_str, datetime):
            return dt_str
        if isinstance(dt_str, str):
            try:
                return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
            except:
                return datetime.now()
        return datetime.now()
