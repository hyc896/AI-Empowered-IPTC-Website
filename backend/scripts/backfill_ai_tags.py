#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
批量补充历史数据的ai_tag字段

功能：
- 查询所有ai_tag为NULL或空的记录
- 使用FieldEnricherService的AI分类功能生成ai_tag
- 批量更新数据库

使用方法：
    python backend/scripts/backfill_ai_tags.py --source tonghuashun --limit 100
    python backend/scripts/backfill_ai_tags.py --source kr36 --limit 1000
    python backend/scripts/backfill_ai_tags.py --all  # 处理所有消息源
"""

import asyncio
import argparse
import logging
from datetime import datetime
from typing import List, Dict, Optional

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.database.connection import create_session
from backend.database.entities import (
    TongHuaShunMessage,
    Kr36Message,
    TechCrunchMessage,
    NikkeiAsiaAIMessage,
    InvestingComMessage
)
from backend.services import get_field_enricher
from backend.config import GlobalConfig, get_config
from backend.llm.global_llm_manager import initialize_llm

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def init_config_and_llm():
    """初始化配置和LLM客户端"""
    try:
        # 直接加载配置文件（不依赖GlobalConfig的prompts初始化）
        from backend.config.config_manager import ConfigManager
        config_manager = ConfigManager()
        if not config_manager.load_config("config.yaml"):
            logger.error("配置文件加载失败")
            return False

        logger.info("配置文件加载成功")

        # 获取LLM配置
        chat_config = config_manager.get_config('llm.chat')
        embedding_config = config_manager.get_config('llm.embedding')
        fast_config = config_manager.get_config('llm.fast')

        if not chat_config or not embedding_config:
            logger.error("LLM配置缺失")
            return False

        # 初始化LLM管理器
        initialize_llm(chat_config, embedding_config, fast_config)
        logger.info("LLM客户端初始化成功")
        return True

    except Exception as e:
        logger.error(f"初始化失败: {e}", exc_info=True)
        return False


# 消息源配置：表名 -> ORM类
SOURCE_CONFIG = {
    'tonghuashun': {
        'model': TongHuaShunMessage,
        'name': '同花顺快讯'
    },
    'kr36': {
        'model': Kr36Message,
        'name': '36氪快讯'
    },
    'techcrunch': {
        'model': TechCrunchMessage,
        'name': 'TechCrunch'
    },
    'nikkei_asia': {
        'model': NikkeiAsiaAIMessage,
        'name': 'Nikkei Asia AI'
    },
    'investing_com': {
        'model': InvestingComMessage,
        'name': 'Investing.com'
    }
}


async def backfill_source_ai_tags(
    source_key: str,
    batch_size: int = 50,
    limit: Optional[int] = None,
    dry_run: bool = False
) -> Dict[str, int]:
    """
    为指定消息源批量补充ai_tag

    Args:
        source_key: 消息源键名（如'tonghuashun'）
        batch_size: 批次大小
        limit: 最大处理条数
        dry_run: 是否为试运行（不写入数据库）

    Returns:
        统计信息字典
    """
    if source_key not in SOURCE_CONFIG:
        logger.error(f"未知的消息源: {source_key}")
        return {}

    config = SOURCE_CONFIG[source_key]
    model = config['model']
    source_name = config['name']

    logger.info(f"开始处理消息源: {source_name}")

    # 统计信息
    stats = {
        'total': 0,
        'processed': 0,
        'ai_related': 0,
        'non_ai': 0,
        'failed': 0,
        'skipped': 0
    }

    try:
        # 获取字段增强服务
        field_enricher = get_field_enricher(max_concurrent=2, max_retries=3)

        # 查询ai_tag为NULL或空，且industry_tags包含"人工智能"的记录
        with create_session() as db:
            query = db.query(model).filter(
                (model.ai_tag.is_(None)) | (model.ai_tag == ''),
                model.industry_tags.like('%人工智能%')
            )

            if limit:
                query = query.limit(limit)

            records = query.all()
            stats['total'] = len(records)

            logger.info(f"【{source_name}】找到 {stats['total']} 条需要补充ai_tag的记录（仅包含'人工智能'标签的消息）")

            if stats['total'] == 0:
                return stats

        # 分批处理
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(records) + batch_size - 1) // batch_size

            logger.info(f"【{source_name}】处理批次 {batch_num}/{total_batches} ({len(batch)}条)")

            # 批量增强
            for record in batch:
                try:
                    # 直接调用AI分类（因为已通过SQL筛选出包含"人工智能"标签的记录）
                    ai_tag = await field_enricher._classify_ai_tag(
                        title=record.title or '',
                        content=record.content or ''
                    )

                    if dry_run:
                        logger.info(
                            f"【试运行】记录ID={record.id[:8]}..., "
                            f"标题={record.title[:30]}..., "
                            f"ai_tag={ai_tag}"
                        )
                        stats['processed'] += 1
                        if ai_tag:
                            stats['ai_related'] += 1
                        else:
                            stats['non_ai'] += 1
                    else:
                        # 更新数据库
                        with create_session() as db:
                            db_record = db.query(model).filter(
                                model.id == record.id
                            ).first()

                            if db_record:
                                db_record.ai_tag = ai_tag
                                db.commit()

                                stats['processed'] += 1
                                if ai_tag:
                                    stats['ai_related'] += 1
                                    logger.debug(f"更新成功: ID={record.id[:8]}..., ai_tag={ai_tag}")
                                else:
                                    stats['non_ai'] += 1
                                    logger.debug(f"更新成功: ID={record.id[:8]}..., ai_tag=None (非AI相关)")
                            else:
                                logger.warning(f"记录不存在: ID={record.id}")
                                stats['skipped'] += 1

                except Exception as e:
                    logger.error(f"处理失败: ID={record.id}, 错误={e}")
                    stats['failed'] += 1
                    continue

            # 批次间短暂休息，避免API限流
            if i + batch_size < len(records):
                logger.info(f"批次完成，等待5秒...")
                await asyncio.sleep(5)

        # 输出统计信息
        logger.info(f"【{source_name}】处理完成:")
        logger.info(f"  总记录数: {stats['total']}")
        logger.info(f"  成功处理: {stats['processed']}")
        logger.info(f"  AI相关: {stats['ai_related']} ({stats['ai_related']/stats['total']*100:.1f}%)")
        logger.info(f"  非AI相关: {stats['non_ai']} ({stats['non_ai']/stats['total']*100:.1f}%)")
        logger.info(f"  失败: {stats['failed']}")
        logger.info(f"  跳过: {stats['skipped']}")

        return stats

    except Exception as e:
        logger.error(f"【{source_name}】处理失败: {e}", exc_info=True)
        return stats


async def backfill_all_sources(
    batch_size: int = 50,
    limit_per_source: Optional[int] = None,
    dry_run: bool = False
):
    """
    为所有消息源批量补充ai_tag

    Args:
        batch_size: 批次大小
        limit_per_source: 每个消息源最大处理条数
        dry_run: 是否为试运行
    """
    logger.info("开始处理所有消息源...")

    all_stats = {}
    for source_key in SOURCE_CONFIG.keys():
        stats = await backfill_source_ai_tags(
            source_key=source_key,
            batch_size=batch_size,
            limit=limit_per_source,
            dry_run=dry_run
        )
        all_stats[source_key] = stats

        # 消息源间休息10秒
        logger.info("等待10秒后处理下一个消息源...")
        await asyncio.sleep(10)

    # 汇总统计
    logger.info("\n=== 全部消息源处理汇总 ===")
    total_all = sum(s.get('total', 0) for s in all_stats.values())
    processed_all = sum(s.get('processed', 0) for s in all_stats.values())
    ai_related_all = sum(s.get('ai_related', 0) for s in all_stats.values())
    non_ai_all = sum(s.get('non_ai', 0) for s in all_stats.values())
    failed_all = sum(s.get('failed', 0) for s in all_stats.values())

    logger.info(f"总记录数: {total_all}")
    logger.info(f"成功处理: {processed_all}")
    logger.info(f"AI相关: {ai_related_all} ({ai_related_all/total_all*100:.1f}%)")
    logger.info(f"非AI相关: {non_ai_all} ({non_ai_all/total_all*100:.1f}%)")
    logger.info(f"失败: {failed_all}")


def main():
    parser = argparse.ArgumentParser(description='批量补充历史数据的ai_tag字段')
    parser.add_argument(
        '--source',
        type=str,
        choices=list(SOURCE_CONFIG.keys()),
        help='指定消息源（tonghuashun/kr36/techcrunch/nikkei_asia/investing_com）'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='处理所有消息源'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=50,
        help='批次大小（默认50）'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='最大处理条数（每个消息源）'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='试运行（不写入数据库）'
    )

    args = parser.parse_args()

    if not args.source and not args.all:
        parser.print_help()
        print("\n错误: 必须指定 --source 或 --all")
        sys.exit(1)

    # 初始化配置和LLM客户端
    if not init_config_and_llm():
        logger.error("初始化失败，退出")
        sys.exit(1)

    if args.dry_run:
        logger.warning("=== 试运行模式，不会写入数据库 ===")

    if args.all:
        asyncio.run(backfill_all_sources(
            batch_size=args.batch_size,
            limit_per_source=args.limit,
            dry_run=args.dry_run
        ))
    else:
        asyncio.run(backfill_source_ai_tags(
            source_key=args.source,
            batch_size=args.batch_size,
            limit=args.limit,
            dry_run=args.dry_run
        ))


if __name__ == '__main__':
    main()
