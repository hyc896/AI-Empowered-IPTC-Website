# -*- coding: utf-8 -*-

"""
Vector Sync Service
MySQL ↔ ChromaDB 数据一致性保障
程序启动时自动检查并修复缺失的向量数据
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
from sqlalchemy import desc

from backend.database.entities import MessageSource
from backend.database.connection import create_session
from backend.database.orm_registry import get_orm_registry
from backend.storage import get_chromadb_storage
from backend.llm import get_embedding_client

logger = logging.getLogger(__name__)


async def check_missing_records(
    source_config: Dict[str, Any],
    full_sync: bool = True
) -> List[Dict[str, Any]]:
    """
    检查单个消息源的缺失记录（MySQL有但ChromaDB没有）

    Args:
        source_config: 消息源配置
        full_sync: 是否全量同步（True=检查所有记录，False=仅检查最近1000条）

    Returns:
        缺失记录的完整数据列表
    """
    source_name = source_config.get('display_name', source_config['name'])
    mysql_table = source_config['mysql_table']
    chroma_collection = source_config['chroma_collection']  # 直接使用，无前缀处理

    try:
        # 从ORM Registry获取模型（自动注册，零硬编码）
        registry = get_orm_registry()
        model = registry.get_model(mysql_table)
        if not model:
            logger.warning(f"【向量同步】{source_name}: 未找到ORM模型")
            return []

        # 使用统一的external_id字段（通过@hybrid_property映射，旧表自动适配）
        id_field = 'external_id'

        # 第一阶段：查询MySQL所有记录的ID（只查ID列，减少内存占用）
        with create_session() as db:
            if full_sync:
                # 全量模式：查询所有ID
                id_column = getattr(model, id_field)
                query = db.query(id_column)
            else:
                # 增量模式：只查最近1000条ID
                id_column = getattr(model, id_field)
                query = db.query(id_column).order_by(desc(model.published_at)).limit(1000)

            results = query.all()

            if not results:
                logger.info(f"【向量同步】{source_name}: MySQL表为空")
                return []

            # 提取ID列表
            mysql_ids = [str(row[0]) for row in results if row[0] is not None]

            if not mysql_ids:
                logger.warning(f"【向量同步】{source_name}: 未找到有效ID")
                return []

        # 第二阶段：批量查询ChromaDB现有ID
        chroma_storage = get_chromadb_storage()
        try:
            chroma_result = chroma_storage._collections.get(chroma_collection)
            if chroma_result is None:
                # 创建新collection（无前缀）
                chroma_storage._client.get_or_create_collection(
                    name=chroma_collection,
                    metadata={"hnsw:space": "cosine"}
                )
                chroma_storage._collections[chroma_collection] = chroma_storage._client.get_collection(
                    name=chroma_collection
                )
                chroma_result = chroma_storage._collections[chroma_collection]

            # ChromaDB的get()方法可以处理大量ID，批量查询现有数据
            existing_data = chroma_result.get(ids=mysql_ids)
            existing_ids = set(existing_data.get('ids', []))

        except Exception as e:
            logger.warning(f"【向量同步】{source_name}: ChromaDB查询失败 - {e}")
            existing_ids = set()

        # 第三阶段：计算差集（缺失的ID）
        missing_ids = set(mysql_ids) - existing_ids

        if not missing_ids:
            logger.info(f"【向量同步】{source_name}: {len(mysql_ids)}条完整 ✓")
            return []

        logger.info(f"【向量同步】{source_name}: 缺失{len(missing_ids)}条，开始同步...")

        # 第四阶段：批量查询缺失记录的完整数据（使用动态模型和统一字段）
        with create_session() as db:
            # 动态获取external_id字段（通过Registry和@hybrid_property统一访问）
            id_column = getattr(model, id_field)
            missing_records = db.query(model).filter(
                id_column.in_(missing_ids)
            ).all()

            result = []
            for record in missing_records:
                item = {
                    'id': record.external_id,  # 统一使用external_id（旧表自动映射）
                    'title': record.title,
                    'content': record.content,
                    'summary': record.summary,
                    'published_at': record.published_at
                }

                # 可选字段（防御式检查）
                if hasattr(record, 'url'):
                    item['url'] = record.url
                if hasattr(record, 'source_url'):
                    item['source_url'] = record.source_url
                if hasattr(record, 'provider'):
                    item['provider'] = record.provider
                if hasattr(record, 'primary_category'):
                    item['primary_category'] = record.primary_category

                result.append(item)

            return result

    except Exception as e:
        logger.error(f"[向量同步] {source_name} - 检查失败: {e}")
        return []


async def sync_to_chromadb(
    records: List[Dict[str, Any]],
    source_config: Dict[str, Any]
) -> int:
    """
    批量向量化并插入ChromaDB

    Args:
        records: 待同步的记录列表
        source_config: 消息源配置

    Returns:
        成功同步的记录数
    """
    if not records:
        return 0

    source_name = source_config.get('display_name', source_config['name'])
    chroma_collection = source_config['chroma_collection']  # 直接使用，无前缀处理
    source_id = source_config['name']

    try:
        embedding_client = get_embedding_client()
        chroma_storage = get_chromadb_storage()

        batch_size = 50
        success_count = 0
        total_batches = (len(records) + batch_size - 1) // batch_size

        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            batch_num = i // batch_size + 1

            try:
                texts = []
                ids = []
                metadatas = []

                for record in batch:
                    summary = record.get('summary', '')
                    document_text = f"{record['title']} {summary}"
                    texts.append(document_text)

                    # 统一使用'id'字段（已在check_missing_records中填充为external_id）
                    record_id = record.get('id') or record.get('url')
                    ids.append(str(record_id))

                    metadata = {
                        "source_id": source_id,
                        "title": record['title'],
                        "published_at": record['published_at'].isoformat() if record.get('published_at') else ''
                    }

                    # 可选字段（统一处理，不再区分旧字段）
                    if 'url' in record:
                        metadata['url'] = record['url']
                    if 'source_url' in record:
                        metadata['source_url'] = record['source_url']
                    if 'provider' in record:
                        metadata['provider'] = record['provider']
                    if 'primary_category' in record:
                        metadata['primary_category'] = record['primary_category']

                    metadatas.append(metadata)

                embeddings = []
                for text in texts:
                    embedding = embedding_client.generate_embedding(text)
                    embeddings.append(embedding)

                chroma_storage.upsert(
                    collection_name=chroma_collection,
                    ids=ids,
                    documents=texts,
                    metadatas=metadatas,
                    embeddings=embeddings
                )

                success_count += len(batch)
                logger.info(f"【向量同步】{source_name}: 批次{batch_num}/{total_batches} ({len(batch)}条向量化) ✓")

            except Exception as e:
                logger.error(f"【向量同步】{source_name}: 批次{batch_num}失败 - {e}")
                continue

        logger.info(f"【向量同步】{source_name}: 同步完成 {success_count}条 ✓")
        return success_count

    except Exception as e:
        logger.error(f"[向量同步] {source_name} - 同步失败: {e}")
        return 0


async def startup_vector_sync(full_sync: bool = None):
    """
    程序启动时的向量同步入口函数

    Args:
        full_sync: 是否全量同步（None=从配置读取，True=全量，False=增量）
    """
    try:
        if full_sync is None:
            # message_platform使用ConfigManager而非GlobalConfig
            from backend.config.config_manager import ConfigManager
            config_manager = ConfigManager()
            config_manager.load_config("config.yaml")
            config = config_manager.get_config()

            vector_sync_config = config.get("vector_sync", {})
            mode = vector_sync_config.get("mode", "incremental")
            full_sync = (mode == "full")

        # 从数据库读取激活的消息源（而非registry）
        with create_session() as db:
            sources_db = db.query(MessageSource).filter(MessageSource.is_active == True).all()

            if not sources_db:
                logger.warning("【向量同步】未找到激活的消息源")
                return

            # 构造source_config格式
            sources = []
            for source in sources_db:
                config = source.config or {}
                source_data = {
                    "id": source.id,
                    "name": source.name,
                    "display_name": source.display_name or source.name,
                    "mysql_table": config.get("mysql_table", f"{source.name}_messages"),
                    "chroma_collection": config.get("chroma_collection", f"{source.name}"),
                    "enabled": True,
                    "config": config
                }
                sources.append(source_data)

        total_synced = 0

        for source in sources:
            if not source.get('enabled', True):
                continue

            try:
                missing_records = await check_missing_records(source, full_sync=full_sync)

                if missing_records:
                    synced_count = await sync_to_chromadb(missing_records, source)
                    total_synced += synced_count

            except Exception as e:
                source_name = source.get('display_name', source.get('name', 'unknown'))
                logger.error(f"【向量同步】{source_name}: 处理失败 - {e}")
                continue

        if total_synced > 0:
            logger.info(f"【向量同步】全部完成，总计{total_synced}条 ✓")
        else:
            logger.info("【向量同步】检查完成，数据完整 ✓")

    except Exception as e:
        logger.error(f"【向量同步】启动失败: {e}")
