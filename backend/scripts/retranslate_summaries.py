# -*- coding: utf-8 -*-

"""
批量重新翻译Summary脚本

保留历史数据，仅重新翻译summary字段。
支持5个错误消息源：RAND, OECD, GovAI, CSIS, CSET

使用方法：
    python backend/scripts/retranslate_summaries.py --dry-run --source all
    python backend/scripts/retranslate_summaries.py --source rand --batch-size 20
"""

import sys
import os
import argparse
import asyncio
import logging
from typing import List, Dict, Any
from datetime import datetime

# Windows兼容性
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# 添加项目根目录到路径（需要找到backend模块）
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from backend.database.connection import create_session
from backend.database.entities import (
    RANDMessage, OECDAIMessage, GovAIMessage, CSISMessage, CSETMessage
)
from sqlalchemy import text
import yaml

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


# ORM类映射
ORM_MODELS = {
    'rand': RANDMessage,
    'oecd': OECDAIMessage,
    'govai': GovAIMessage,
    'csis': CSISMessage,
    'cset': CSETMessage
}


# 消息源配置
SOURCES_CONFIG = {
    'rand': {
        'name': 'RAND Corporation',
        'context': 'RAND智库研究报告摘要',
        'chroma_collection': 'rand_research'
    },
    'oecd': {
        'name': 'OECD AI Policy Observatory',
        'context': 'OECD AI政策研究文章摘要',
        'chroma_collection': 'oecd_ai_policy'
    },
    'govai': {
        'name': 'GovAI',
        'context': 'AI治理研究论文摘要',
        'chroma_collection': 'govai_papers'
    },
    'csis': {
        'name': 'CSIS',
        'context': 'CSIS智库文章摘要',
        'chroma_collection': 'csis_analysis'
    },
    'cset': {
        'name': 'CSET Georgetown',
        'context': 'AI安全研究论文',
        'chroma_collection': 'cset_publications'
    }
}


def init_llm_clients():
    """初始化LLM客户端（必须在异步函数外）"""
    try:
        # 使用ConfigManager加载配置（会自动解析环境变量）
        from backend.config import ConfigManager
        config_manager = ConfigManager()
        config_manager.load_config('config.yaml')
        config = config_manager.get_config()

        # 初始化GlobalLLMManager
        from backend.llm import GlobalLLMManager
        llm_config = config.get('llm', {})

        # 配置Fast模型（用于翻译）
        fast_config = llm_config.get('fast', {})
        if not fast_config:
            raise ValueError("config.yaml中未找到llm.fast配置")

        # 获取embedding配置
        embedding_config = llm_config.get('embedding', {})
        if not embedding_config:
            logger.warning("⚠ config.yaml中未找到llm.embedding配置，将跳过向量更新")

        # 一次性初始化GlobalLLMManager（Fast + Embedding）
        llm_manager = GlobalLLMManager()
        llm_manager.initialize(
            chat_config=None,  # 不需要主模型
            embedding_config=embedding_config if embedding_config else None,
            fast_config=fast_config
        )

        logger.info("✓ LLM客户端初始化成功（Fast + Embedding）")
        return True

    except Exception as e:
        logger.error(f"✗ LLM客户端初始化失败: {e}")
        return False


def init_chromadb():
    """初始化ChromaDB（Embedding已在init_llm_clients中初始化）"""
    try:
        # 使用ConfigManager加载配置（会自动解析环境变量）
        from backend.config import ConfigManager
        config_manager = ConfigManager()
        config_manager.load_config('config.yaml')
        config = config_manager.get_config()

        # 初始化ChromaDB
        from backend.storage import get_chromadb_storage
        chroma_config = config.get('database', {}).get('chromadb', {})

        if not chroma_config:
            logger.warning("⚠ config.yaml中未找到database.chromadb配置，将跳过向量更新")
            return True  # 不算失败，只是跳过

        chroma_storage = get_chromadb_storage()
        success = chroma_storage.initialize(chroma_config)

        if success:
            logger.info("✓ ChromaDB初始化成功")
        else:
            logger.warning("⚠ ChromaDB初始化失败，将跳过向量数据更新")

        return True  # ChromaDB失败不影响翻译

    except Exception as e:
        logger.warning(f"⚠ ChromaDB初始化失败: {e}")
        return True  # ChromaDB失败不影响翻译


def query_records(source_key: str, limit: int = None) -> List[Any]:
    """
    查询需要重新翻译的记录

    Args:
        source_key: 消息源键名
        limit: 限制查询数量（None表示全部）

    Returns:
        记录列表
    """
    model = ORM_MODELS[source_key]

    try:
        with create_session() as db:
            query = db.query(model).order_by(model.published_at.desc())

            if limit:
                query = query.limit(limit)

            records = query.all()
            logger.info(f"  查询到 {len(records)} 条记录")
            return records

    except Exception as e:
        logger.error(f"  ✗ 查询记录失败: {e}")
        return []


def chunk(lst: List, size: int):
    """将列表分批"""
    for i in range(0, len(lst), size):
        yield lst[i:i + size]


async def translate_batch(translator, records: List[Any], context: str) -> Dict[str, str]:
    """
    批量翻译summary

    Args:
        translator: 翻译器实例
        records: 记录列表
        context: 翻译上下文

    Returns:
        {record.id: translated_summary}字典
    """
    # 提取content作为待翻译文本
    texts = [r.content for r in records]
    record_ids = [r.id for r in records]

    # 批量翻译
    translations = await translator.translate_batch(texts, context=context)

    # 构建ID→翻译结果映射
    result = {}
    for record_id, translation in zip(record_ids, translations):
        result[record_id] = translation

    return result


def update_mysql_summaries(source_key: str, summaries: Dict[str, str]) -> int:
    """
    更新MySQL中的summary字段

    Args:
        source_key: 消息源键名
        summaries: {record_id: translated_summary}字典

    Returns:
        更新的记录数
    """
    model = ORM_MODELS[source_key]
    updated_count = 0

    try:
        with create_session() as db:
            for record_id, summary in summaries.items():
                record = db.query(model).filter(model.id == record_id).first()
                if record:
                    record.summary = summary
                    updated_count += 1

            db.commit()
            logger.info(f"  ✓ 已更新 {updated_count} 条记录的summary")
            return updated_count

    except Exception as e:
        logger.error(f"  ✗ 更新MySQL失败: {e}")
        return 0


def update_chroma_embeddings(chroma_collection: str, summaries: Dict[str, str], records: List[Any]):
    """
    更新ChromaDB中的向量数据

    Args:
        chroma_collection: ChromaDB collection名称
        summaries: {record_id: translated_summary}字典
        records: 原始记录列表
    """
    try:
        from backend.storage import get_chromadb_storage
        from backend.llm import get_embedding_client

        chroma_storage = get_chromadb_storage()
        embedding_client = get_embedding_client()

        # 检查ChromaDB是否已初始化
        if not chroma_storage.is_initialized():
            logger.warning(f"  ⚠ ChromaDB未初始化，跳过向量更新")
            return

        # 为每条记录生成新的向量
        updated_count = 0
        for record in records:
            if record.id not in summaries:
                continue

            summary = summaries[record.id]
            document_text = f"{record.title} {summary}"

            # 生成向量
            embedding = embedding_client.generate_embedding(document_text)

            # 更新ChromaDB（使用upsert）
            chroma_id = record.url or record.id
            chroma_storage.upsert(
                collection_name=chroma_collection,
                ids=[chroma_id],
                documents=[document_text],
                metadatas=[{
                    "source_id": str(record.source_id),
                    "external_id": record.external_id or '',
                    "published_at": record.published_at.isoformat() if record.published_at else '',
                    "url": record.url or '',
                    "title": record.title,
                    "provider": record.provider or ''
                }],
                embeddings=[embedding]
            )
            updated_count += 1

        logger.info(f"  ✓ 已更新 {updated_count} 条ChromaDB向量数据")

    except ImportError:
        logger.warning(f"  ⚠ ChromaDB不可用，跳过向量更新")
    except Exception as e:
        logger.error(f"  ✗ 更新ChromaDB失败: {e}")


async def process_source(source_key: str, batch_size: int, limit: int, dry_run: bool):
    """
    处理单个消息源的批量翻译

    Args:
        source_key: 消息源键名
        batch_size: 批次大小
        limit: 限制翻译数量（None表示全部）
        dry_run: 是否为试运行模式
    """
    source_config = SOURCES_CONFIG[source_key]

    logger.info(f"\n{'=' * 60}")
    logger.info(f"【{source_config['name']}】")
    logger.info(f"{'=' * 60}")

    # 1. 查询记录
    records = query_records(source_key, limit=limit)

    if not records:
        logger.info("  无记录需要翻译")
        return

    if dry_run:
        logger.info(f"  [DRY RUN] 将翻译 {len(records)} 条记录")
        logger.info(f"  [DRY RUN] 批次大小: {batch_size}")
        return

    # 2. 获取翻译器
    from backend.llm import get_translator
    translator = get_translator()

    # 3. 分批翻译
    total_batches = (len(records) + batch_size - 1) // batch_size
    all_summaries = {}

    for batch_idx, batch_records in enumerate(chunk(records, batch_size), 1):
        logger.info(f"\n  批次 {batch_idx}/{total_batches}：翻译 {len(batch_records)} 条记录...")

        try:
            # 批量翻译
            summaries = await translate_batch(
                translator,
                batch_records,
                context=source_config['context']
            )

            # 检查翻译结果是否包含降级标记
            failed_count = sum(1 for s in summaries.values() if '[AI翻译暂不可用]' in s)
            success_count = len(summaries) - failed_count

            logger.info(f"  ✓ 翻译完成: 成功 {success_count} 条, 失败 {failed_count} 条")

            # 更新数据库
            update_mysql_summaries(source_key, summaries)

            # 更新ChromaDB
            update_chroma_embeddings(
                source_config['chroma_collection'],
                summaries,
                batch_records
            )

            all_summaries.update(summaries)

        except Exception as e:
            logger.error(f"  ✗ 批次 {batch_idx} 翻译失败: {e}")

        # 批次间延迟（避免API过载）
        if batch_idx < total_batches:
            await asyncio.sleep(1)

    # 4. 统计结果
    logger.info(f"\n  总计: {len(all_summaries)} 条记录已翻译")


async def main_async(args):
    """异步主函数"""
    # 解析消息源列表
    if args.source == 'all':
        source_keys = list(SOURCES_CONFIG.keys())
    else:
        source_keys = [args.source]

    logger.info("=" * 60)
    if args.dry_run:
        logger.info("批量重新翻译预览（DRY RUN模式）")
    else:
        logger.info("批量重新翻译Summary")
    logger.info("=" * 60)

    # 处理每个消息源
    for source_key in source_keys:
        await process_source(
            source_key,
            batch_size=args.batch_size,
            limit=args.limit,
            dry_run=args.dry_run
        )

    logger.info("\n" + "=" * 60)
    if args.dry_run:
        logger.info("[DRY RUN] 这是试运行模式，未实际修改数据")
    else:
        logger.info("批量翻译完成！")
    logger.info("=" * 60)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='批量重新翻译summary')
    parser.add_argument(
        '--source',
        choices=['rand', 'oecd', 'govai', 'csis', 'cset', 'all'],
        required=True,
        help='指定要翻译的消息源（all表示全部）'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=20,
        help='批次大小（默认20条/批）'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='限制翻译数量（默认全部）'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='试运行模式，仅预览影响范围，不实际翻译'
    )

    args = parser.parse_args()

    # 初始化LLM客户端（Fast + Embedding）
    if not args.dry_run:
        if not init_llm_clients():
            logger.error("LLM客户端初始化失败，退出")
            sys.exit(1)

        # 初始化ChromaDB（用于向量化）
        init_chromadb()

    # 运行异步主函数
    asyncio.run(main_async(args))


if __name__ == '__main__':
    main()
