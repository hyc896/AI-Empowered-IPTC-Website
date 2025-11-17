# -*- coding: utf-8 -*-

"""
向量数据一致性验证和清理脚本

功能：
1. 检查MySQL和ChromaDB数据一致性
2. 显示详细的统计报告
3. 可选择性清理孤立向量
4. 可选择性同步缺失向量

使用方法：
    # 检查所有消息源的一致性（dry-run模式）
    python backend/scripts/verify_vector_consistency.py --check-all

    # 检查特定消息源
    python backend/scripts/verify_vector_consistency.py --source tonghuashun

    # 清理孤立向量（实际执行）
    python backend/scripts/verify_vector_consistency.py --source tonghuashun --cleanup-orphaned

    # 同步缺失向量
    python backend/scripts/verify_vector_consistency.py --source tonghuashun --sync-missing

    # 完整修复：同步缺失 + 清理孤立
    python backend/scripts/verify_vector_consistency.py --source tonghuashun --full-repair
"""

import sys
import os
import argparse
import logging
import asyncio
from typing import Dict, List, Any, Set
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from backend.database.connection import create_session
from backend.database.entities import MessageSource
from backend.database.orm_registry import get_orm_registry
from backend.storage import get_chromadb_storage
from backend.services.message.vector_sync import (
    check_missing_records,
    check_orphaned_vectors,
    sync_to_chromadb,
    cleanup_orphaned_vectors
)

logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


def init_chromadb():
    """初始化ChromaDB"""
    try:
        from backend.config import ConfigManager

        config_manager = ConfigManager()
        config_manager.load_config('config.yaml')
        config = config_manager.get_config()

        chroma_config = config.get('database', {}).get('chromadb', {})

        if not chroma_config:
            logger.error("❌ config.yaml中未找到database.chromadb配置")
            return False

        chroma_storage = get_chromadb_storage()
        success = chroma_storage.initialize(chroma_config)

        if success:
            logger.info("✓ ChromaDB初始化成功")
        else:
            logger.error("❌ ChromaDB初始化失败")

        return success

    except Exception as e:
        logger.error(f"❌ ChromaDB初始化失败: {e}")
        return False


async def check_consistency(source_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    检查单个消息源的数据一致性

    Args:
        source_config: 消息源配置

    Returns:
        一致性检查结果
    """
    source_name = source_config.get('display_name', source_config['name'])
    mysql_table = source_config['mysql_table']
    chroma_collection = source_config['chroma_collection']

    result = {
        'source_name': source_name,
        'mysql_table': mysql_table,
        'chroma_collection': chroma_collection,
        'mysql_count': 0,
        'chroma_count': 0,
        'missing_in_chroma': 0,
        'orphaned_in_chroma': 0,
        'is_consistent': False
    }

    try:
        # 获取MySQL记录数
        registry = get_orm_registry()
        model = registry.get_model(mysql_table)

        if not model:
            logger.warning(f"⚠ {source_name}: 未找到ORM模型")
            return result

        with create_session() as db:
            mysql_count = db.query(model).count()
            result['mysql_count'] = mysql_count

        # 获取ChromaDB记录数
        chroma_storage = get_chromadb_storage()
        collection = chroma_storage._collections.get(chroma_collection)

        if collection:
            chroma_count = collection.count()
            result['chroma_count'] = chroma_count
        else:
            logger.warning(f"⚠ {source_name}: ChromaDB集合不存在")
            result['chroma_count'] = 0

        # 检查缺失的向量（MySQL有但ChromaDB没有）
        missing_records = await check_missing_records(source_config, full_sync=True)
        result['missing_in_chroma'] = len(missing_records)

        # 检查孤立的向量（ChromaDB有但MySQL没有）
        orphaned_ids = await check_orphaned_vectors(source_config)
        result['orphaned_in_chroma'] = len(orphaned_ids)

        # 判断是否一致
        result['is_consistent'] = (
            result['missing_in_chroma'] == 0 and
            result['orphaned_in_chroma'] == 0 and
            result['mysql_count'] == result['chroma_count']
        )

        return result

    except Exception as e:
        logger.error(f"❌ {source_name}: 检查失败 - {e}")
        return result


def print_consistency_report(results: List[Dict[str, Any]]):
    """
    打印一致性检查报告

    Args:
        results: 检查结果列表
    """
    logger.info("=" * 80)
    logger.info("向量数据一致性检查报告")
    logger.info("=" * 80)

    total_mysql = 0
    total_chroma = 0
    total_missing = 0
    total_orphaned = 0
    consistent_sources = 0

    for result in results:
        logger.info(f"\n【{result['source_name']}】")
        logger.info(f"  MySQL表: {result['mysql_table']}")
        logger.info(f"  ChromaDB集合: {result['chroma_collection']}")
        logger.info(f"  MySQL记录数: {result['mysql_count']}")
        logger.info(f"  ChromaDB向量数: {result['chroma_count']}")

        if result['is_consistent']:
            logger.info("  状态: ✓ 数据完全一致")
            consistent_sources += 1
        else:
            logger.warning("  状态: ⚠ 数据不一致")

            if result['missing_in_chroma'] > 0:
                logger.warning(f"    - 缺失向量: {result['missing_in_chroma']}条（MySQL有但ChromaDB没有）")

            if result['orphaned_in_chroma'] > 0:
                logger.warning(f"    - 孤立向量: {result['orphaned_in_chroma']}条（ChromaDB有但MySQL没有）")

        total_mysql += result['mysql_count']
        total_chroma += result['chroma_count']
        total_missing += result['missing_in_chroma']
        total_orphaned += result['orphaned_in_chroma']

    logger.info("\n" + "=" * 80)
    logger.info("汇总统计")
    logger.info("=" * 80)
    logger.info(f"总消息源数: {len(results)}")
    logger.info(f"数据一致的消息源: {consistent_sources}/{len(results)}")
    logger.info(f"MySQL总记录数: {total_mysql}")
    logger.info(f"ChromaDB总向量数: {total_chroma}")
    logger.info(f"缺失向量总数: {total_missing}")
    logger.info(f"孤立向量总数: {total_orphaned}")

    if total_missing == 0 and total_orphaned == 0:
        logger.info("\n✓ 所有消息源数据完全一致！")
    else:
        logger.warning("\n⚠ 发现数据不一致，建议执行修复操作")
        logger.info("\n修复命令：")
        if total_missing > 0:
            logger.info("  同步缺失向量: --sync-missing")
        if total_orphaned > 0:
            logger.info("  清理孤立向量: --cleanup-orphaned")
        logger.info("  完整修复: --full-repair")


async def repair_source(
    source_config: Dict[str, Any],
    sync_missing: bool = False,
    cleanup_orphaned: bool = False
) -> Dict[str, int]:
    """
    修复单个消息源的数据一致性

    Args:
        source_config: 消息源配置
        sync_missing: 是否同步缺失向量
        cleanup_orphaned: 是否清理孤立向量

    Returns:
        修复结果统计
    """
    source_name = source_config.get('display_name', source_config['name'])
    stats = {'synced': 0, 'cleaned': 0}

    try:
        # 同步缺失向量
        if sync_missing:
            logger.info(f"\n【{source_name}】开始同步缺失向量...")
            missing_records = await check_missing_records(source_config, full_sync=True)

            if missing_records:
                synced_count = await sync_to_chromadb(missing_records, source_config)
                stats['synced'] = synced_count
                logger.info(f"✓ 同步完成: {synced_count}条")
            else:
                logger.info("✓ 无缺失向量")

        # 清理孤立向量
        if cleanup_orphaned:
            logger.info(f"\n【{source_name}】开始清理孤立向量...")
            orphaned_ids = await check_orphaned_vectors(source_config)

            if orphaned_ids:
                cleaned_count = await cleanup_orphaned_vectors(orphaned_ids, source_config)
                stats['cleaned'] = cleaned_count
                logger.info(f"✓ 清理完成: {cleaned_count}条")
            else:
                logger.info("✓ 无孤立向量")

        return stats

    except Exception as e:
        logger.error(f"❌ {source_name}: 修复失败 - {e}")
        return stats


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='向量数据一致性验证和清理')
    parser.add_argument(
        '--source',
        type=str,
        help='指定消息源名称（不指定则检查所有）'
    )
    parser.add_argument(
        '--check-all',
        action='store_true',
        help='检查所有消息源的一致性'
    )
    parser.add_argument(
        '--sync-missing',
        action='store_true',
        help='同步缺失的向量（MySQL → ChromaDB）'
    )
    parser.add_argument(
        '--cleanup-orphaned',
        action='store_true',
        help='清理孤立的向量（ChromaDB多余的）'
    )
    parser.add_argument(
        '--full-repair',
        action='store_true',
        help='完整修复（同步缺失 + 清理孤立）'
    )

    args = parser.parse_args()

    # 初始化ChromaDB
    if not init_chromadb():
        logger.error("初始化失败，退出")
        sys.exit(1)

    # 获取消息源配置
    with create_session() as db:
        if args.source:
            # 指定消息源
            sources_db = db.query(MessageSource).filter(
                MessageSource.name == args.source,
                MessageSource.is_active == True
            ).all()

            if not sources_db:
                logger.error(f"❌ 未找到激活的消息源: {args.source}")
                sys.exit(1)
        else:
            # 所有激活的消息源
            sources_db = db.query(MessageSource).filter(MessageSource.is_active == True).all()

            if not sources_db:
                logger.error("❌ 未找到任何激活的消息源")
                sys.exit(1)

        # 构造配置
        sources = []
        for source in sources_db:
            config = source.config or {}
            source_data = {
                "id": source.id,
                "name": source.name,
                "display_name": source.display_name or source.name,
                "mysql_table": config.get("mysql_table", f"{source.name}_messages"),
                "chroma_collection": config.get("chroma_collection", f"{source.name}"),
                "config": config
            }
            sources.append(source_data)

    # 检查一致性
    logger.info(f"开始检查{len(sources)}个消息源的数据一致性...\n")
    results = []

    for source in sources:
        result = await check_consistency(source)
        results.append(result)

    # 打印报告
    print_consistency_report(results)

    # 执行修复操作
    if args.full_repair or args.sync_missing or args.cleanup_orphaned:
        logger.info("\n" + "=" * 80)
        logger.info("开始修复操作")
        logger.info("=" * 80)

        sync_missing = args.full_repair or args.sync_missing
        cleanup_orphaned = args.full_repair or args.cleanup_orphaned

        total_synced = 0
        total_cleaned = 0

        for source in sources:
            stats = await repair_source(source, sync_missing, cleanup_orphaned)
            total_synced += stats['synced']
            total_cleaned += stats['cleaned']

        logger.info("\n" + "=" * 80)
        logger.info("修复完成")
        logger.info("=" * 80)

        if total_synced > 0:
            logger.info(f"✓ 同步向量: {total_synced}条")
        if total_cleaned > 0:
            logger.info(f"✓ 清理向量: {total_cleaned}条")

        if total_synced == 0 and total_cleaned == 0:
            logger.info("✓ 数据已是一致状态，无需修复")


if __name__ == '__main__':
    asyncio.run(main())
