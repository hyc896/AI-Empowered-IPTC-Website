# -*- coding: utf-8 -*-

"""
历史消息批量增强脚本
为同花顺和36kr的历史消息批量添加region和industry_tags字段

使用方式：
    python backend/scripts/enrich_historical_messages.py --source tonghuashun --limit 10
    python backend/scripts/enrich_historical_messages.py --source kr36 --batch-size 20
    python backend/scripts/enrich_historical_messages.py --source all --dry-run
"""

import asyncio
import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.database.connection import create_session, init_database
from backend.database.entities import TongHuaShunMessage, Kr36Message
from backend.services import get_field_enricher
from backend.config import ConfigManager
from backend.llm import GlobalLLMManager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def init_llm_clients(config):
    """初始化LLM客户端"""
    llm_config = config.get_config('llm') or {}

    # 初始化Fast客户端（用于字段增强）
    fast_config = llm_config.get('fast', {})
    if not fast_config:
        logger.error("配置文件中缺少llm.fast配置")
        sys.exit(1)

    # 创建GlobalLLMManager实例并初始化fast客户端
    manager = GlobalLLMManager()
    manager.initialize(chat_config=None, embedding_config=None, fast_config=fast_config)
    logger.info("Fast LLM客户端初始化完成")


async def enrich_tonghuashun_messages(
    limit: int = None,
    batch_size: int = 20,
    dry_run: bool = False
):
    """增强同花顺消息"""
    logger.info("=" * 60)
    logger.info("开始处理同花顺消息")
    logger.info("=" * 60)

    with create_session() as db:
        # 查询待增强的消息（region为NULL）
        query = db.query(TongHuaShunMessage).filter(
            TongHuaShunMessage.region.is_(None)
        ).order_by(TongHuaShunMessage.published_at.desc())

        if limit:
            query = query.limit(limit)

        messages = query.all()
        total = len(messages)

        if total == 0:
            logger.info("没有需要增强的消息")
            return

        logger.info(f"找到 {total} 条待增强消息")

        if dry_run:
            logger.info("[试运行模式] 将处理以下消息：")
            for msg in messages[:5]:
                logger.info(f"  - seq={msg.seq}, title={msg.title[:50]}...")
            logger.info(f"  ... 还有 {max(0, total - 5)} 条")
            return

        # 获取字段增强服务（降低并发到1，避免TPM限制）
        enricher = get_field_enricher(max_concurrent=1)

        # 分批处理
        batch_count = (total + batch_size - 1) // batch_size
        success_count = 0
        failed_count = 0

        for i in range(0, total, batch_size):
            batch = messages[i:i+batch_size]
            batch_num = i // batch_size + 1
            logger.info(f"\n处理批次 {batch_num}/{batch_count} ({len(batch)}条消息)")

            # 批量增强
            tasks = [
                enricher.enrich_fields(msg.title, msg.content)
                for msg in batch
            ]
            results = await asyncio.gather(*tasks)

            # 批次间延迟1秒，避免TPM限制
            if i + batch_size < total:
                await asyncio.sleep(1)

            # 更新数据库
            for msg, enriched in zip(batch, results):
                try:
                    if enriched['region']:
                        msg.region = enriched['region']
                    if enriched['industry_tags']:
                        msg.industry_tags = enriched['industry_tags']

                    db.commit()
                    success_count += 1
                    logger.debug(
                        f"  ✓ seq={msg.seq}, region={enriched['region']}, "
                        f"tags={enriched['industry_tags']}"
                    )
                except Exception as e:
                    db.rollback()
                    failed_count += 1
                    logger.error(f"  ✗ 更新失败 seq={msg.seq}: {e}")

            logger.info(f"批次完成: 成功{len(batch)}, 累计成功{success_count}/{total}")

        logger.info(f"\n同花顺消息处理完成: 成功{success_count}, 失败{failed_count}")


async def enrich_kr36_messages(
    limit: int = None,
    batch_size: int = 20,
    dry_run: bool = False
):
    """增强36kr消息"""
    logger.info("=" * 60)
    logger.info("开始处理36kr消息")
    logger.info("=" * 60)

    with create_session() as db:
        # 查询待增强的消息（region为NULL）
        query = db.query(Kr36Message).filter(
            Kr36Message.region.is_(None)
        ).order_by(Kr36Message.published_at.desc())

        if limit:
            query = query.limit(limit)

        messages = query.all()
        total = len(messages)

        if total == 0:
            logger.info("没有需要增强的消息")
            return

        logger.info(f"找到 {total} 条待增强消息")

        if dry_run:
            logger.info("[试运行模式] 将处理以下消息：")
            for msg in messages[:5]:
                logger.info(f"  - item_id={msg.item_id}, title={msg.title[:50]}...")
            logger.info(f"  ... 还有 {max(0, total - 5)} 条")
            return

        # 获取字段增强服务（降低并发到1，避免TPM限制）
        enricher = get_field_enricher(max_concurrent=1)

        # 分批处理
        batch_count = (total + batch_size - 1) // batch_size
        success_count = 0
        failed_count = 0

        for i in range(0, total, batch_size):
            batch = messages[i:i+batch_size]
            batch_num = i // batch_size + 1
            logger.info(f"\n处理批次 {batch_num}/{batch_count} ({len(batch)}条消息)")

            # 批量增强
            tasks = [
                enricher.enrich_fields(msg.title, msg.content)
                for msg in batch
            ]
            results = await asyncio.gather(*tasks)

            # 批次间延迟1秒，避免TPM限制
            if i + batch_size < total:
                await asyncio.sleep(1)

            # 更新数据库
            for msg, enriched in zip(batch, results):
                try:
                    if enriched['region']:
                        msg.region = enriched['region']
                    if enriched['industry_tags']:
                        msg.industry_tags = enriched['industry_tags']

                    db.commit()
                    success_count += 1
                    logger.debug(
                        f"  ✓ item_id={msg.item_id}, region={enriched['region']}, "
                        f"tags={enriched['industry_tags']}"
                    )
                except Exception as e:
                    db.rollback()
                    failed_count += 1
                    logger.error(f"  ✗ 更新失败 item_id={msg.item_id}: {e}")

            logger.info(f"批次完成: 成功{len(batch)}, 累计成功{success_count}/{total}")

        logger.info(f"\n36kr消息处理完成: 成功{success_count}, 失败{failed_count}")


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='历史消息批量增强脚本')
    parser.add_argument(
        '--source',
        choices=['tonghuashun', 'kr36', 'all'],
        default='all',
        help='消息源（默认：all）'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='限制处理数量（用于测试）'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=20,
        help='批次大小（默认：20）'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='试运行模式（仅统计，不实际处理）'
    )

    args = parser.parse_args()

    logger.info("========== 历史消息批量增强脚本 ==========")
    logger.info(f"消息源: {args.source}")
    logger.info(f"批次大小: {args.batch_size}")
    if args.limit:
        logger.info(f"限制数量: {args.limit}")
    if args.dry_run:
        logger.info("模式: 试运行（不实际处理）")
    logger.info("=" * 60)

    start_time = datetime.now()

    try:
        # 加载配置
        config = ConfigManager()
        if not config.load_config("config.yaml"):
            logger.error("配置加载失败")
            sys.exit(1)

        # 初始化数据库
        init_database()
        logger.info("数据库初始化完成")

        # 初始化LLM客户端
        init_llm_clients(config)

        # 处理消息
        if args.source in ['tonghuashun', 'all']:
            await enrich_tonghuashun_messages(
                limit=args.limit,
                batch_size=args.batch_size,
                dry_run=args.dry_run
            )

        if args.source in ['kr36', 'all']:
            await enrich_kr36_messages(
                limit=args.limit,
                batch_size=args.batch_size,
                dry_run=args.dry_run
            )

        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info("=" * 60)
        logger.info(f"全部完成！总耗时: {elapsed:.1f}秒")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"脚本执行失败: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    # Windows环境需要设置事件循环策略
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(main())
