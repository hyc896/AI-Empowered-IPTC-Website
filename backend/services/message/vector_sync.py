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

from backend.database.entities import TongHuaShunMessage, Kr36Message, ArxivMessage, MessageSource
from backend.database.connection import create_session
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
        logger.info(f"[向量同步] 检查消息源: {source_name} (全量模式: {full_sync})")

        # message_platform的表名映射（mp_前缀）
        model_map = {
            "mp_tonghuashun_messages": TongHuaShunMessage,
            "mp_kr36_messages": Kr36Message,
            "mp_arxiv_messages": ArxivMessage,
            # 兼容旧配置（无mp_前缀）
            "tonghuashun_messages": TongHuaShunMessage,
            "kr36_messages": Kr36Message,
            "arxiv_messages": ArxivMessage
        }

        model = model_map.get(mysql_table)
        if not model:
            logger.warning(f"[向量同步] 未找到表 {mysql_table} 的ORM模型")
            return []

        # 确定唯一ID字段
        if 'tonghuashun' in mysql_table:
            id_field = 'seq'
        elif 'kr36' in mysql_table:
            id_field = 'item_id'
        else:  # arxiv
            id_field = 'arxiv_id'

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
                logger.info(f"[向量同步] {source_name} - MySQL表为空")
                return []

            # 提取ID列表
            mysql_ids = [str(row[0]) for row in results if row[0] is not None]

            if not mysql_ids:
                logger.warning(f"[向量同步] {source_name} - 未找到有效唯一ID")
                return []

            logger.info(f"[向量同步] {source_name} - MySQL共有{len(mysql_ids)}条记录")

        # 第二阶段：批量查询ChromaDB现有ID
        chroma_storage = get_chromadb_storage()
        try:
            chroma_result = chroma_storage._collections.get(chroma_collection)
            if chroma_result is None:
                # 创建新collection（无前缀）
                chroma_storage._client.get_or_create_collection(
                    name=chroma_collection,
                    metadata={{"hnsw:space": "cosine"}}
                )
                chroma_storage._collections[chroma_collection] = chroma_storage._client.get_collection(
                    name=chroma_collection
                )
                chroma_result = chroma_storage._collections[chroma_collection]

            # ChromaDB的get()方法可以处理大量ID，批量查询现有数据
            existing_data = chroma_result.get(ids=mysql_ids)
            existing_ids = set(existing_data.get('ids', []))

            logger.info(f"[向量同步] {source_name} - ChromaDB现有{len(existing_ids)}条")

        except Exception as e:
            logger.warning(f"[向量同步] {source_name} - ChromaDB查询失败: {e}")
            existing_ids = set()

        # 第三阶段：计算差集（缺失的ID）
        missing_ids = set(mysql_ids) - existing_ids

        if not missing_ids:
            logger.info(f"[向量同步] {source_name} - ✓ 数据完整，无需同步 (MySQL={len(mysql_ids)}, ChromaDB={len(existing_ids)})")
            return []

        logger.info(f"[向量同步] {source_name} - 发现缺失 {len(missing_ids)}/{len(mysql_ids)} 条")

        # 第四阶段：批量查询缺失记录的完整数据
        with create_session() as db:
            if 'tonghuashun' in mysql_table:
                missing_records = db.query(TongHuaShunMessage).filter(
                    TongHuaShunMessage.seq.in_(missing_ids)
                ).all()
            elif 'kr36' in mysql_table:
                missing_records = db.query(Kr36Message).filter(
                    Kr36Message.item_id.in_(missing_ids)
                ).all()
            else:  # arxiv
                missing_records = db.query(ArxivMessage).filter(
                    ArxivMessage.arxiv_id.in_(missing_ids)
                ).all()

            result = []
            for record in missing_records:
                item = {
                    'id': getattr(record, id_field),
                    'title': record.title,
                    'content': record.content,
                    'summary': record.summary,
                    'published_at': record.published_at
                }

                if hasattr(record, 'url'):
                    item['url'] = record.url
                if hasattr(record, 'source_url'):
                    item['source_url'] = record.source_url
                if hasattr(record, 'provider'):
                    item['provider'] = record.provider
                if hasattr(record, 'seq'):
                    item['seq'] = record.seq
                if hasattr(record, 'item_id'):
                    item['item_id'] = record.item_id
                if hasattr(record, 'arxiv_id'):
                    item['arxiv_id'] = record.arxiv_id
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

        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]

            try:
                texts = []
                ids = []
                metadatas = []

                for record in batch:
                    summary = record.get('summary', '')
                    document_text = f"{record['title']} {summary}"
                    texts.append(document_text)

                    record_id = record.get('seq') or record.get('item_id') or record.get('arxiv_id') or record.get('url')
                    ids.append(str(record_id))

                    metadata = {
                        "source_id": source_id,
                        "title": record['title'],
                        "published_at": record['published_at'].isoformat() if record.get('published_at') else ''
                    }

                    if 'url' in record:
                        metadata['url'] = record['url']
                    if 'source_url' in record:
                        metadata['source_url'] = record['source_url']
                    if 'provider' in record:
                        metadata['provider'] = record['provider']
                    if 'item_id' in record:
                        metadata['item_id'] = record['item_id']
                    if 'kr_route' in record:
                        metadata['kr_route'] = record['kr_route']
                    if 'arxiv_id' in record:
                        metadata['arxiv_id'] = record['arxiv_id']
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
                logger.debug(f"[向量同步] {source_name} - 批次同步完成: {len(batch)}条")

            except Exception as e:
                logger.error(f"[向量同步] {source_name} - 批次同步失败: {e}")
                continue

        logger.info(f"[向量同步] {source_name} - ✓ 同步完成: {success_count}条")
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

        sync_mode = "全量同步" if full_sync else "增量同步"
        logger.info(f"[向量同步] 后台检查启动（{sync_mode}）...")

        # 从数据库读取激活的消息源（而非registry）
        with create_session() as db:
            sources_db = db.query(MessageSource).filter(MessageSource.is_active == True).all()

            if not sources_db:
                logger.warning("[向量同步] 未找到激活的消息源")
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
                logger.error(f"[向量同步] {source_name} - 处理失败: {e}")
                continue

        if total_synced > 0:
            logger.info(f"[向量同步] ✓ 全部同步完成，总计 {total_synced} 条")
        else:
            logger.info("[向量同步] ✓ 检查完成，数据完整")

    except Exception as e:
        logger.error(f"[向量同步] 启动检查失败: {e}")
