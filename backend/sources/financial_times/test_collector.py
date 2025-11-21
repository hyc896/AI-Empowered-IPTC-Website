# -*- coding: utf-8 -*-
"""
测试Financial Times采集器功能
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from backend.sources.financial_times.collector import FTCollector
from backend.database.connection import create_session
from backend.database.entities import FinancialTimesMessage


async def test_collector():
    """测试采集器"""

    config = {
        'id': '8d4bdf4e-c4a2-11f0-b75e-08bfb82ee112',
        'interval': 3600,
        'config': {
            'mysql_table': 'mp_financial_times_messages',
            'chroma_collection': 'financial_times_tech',
            'region': '英国',
            'language': 'en'
        }
    }

    print("=" * 80)
    print("Financial Times Technology 采集器测试")
    print("=" * 80)

    collector = FTCollector(config)

    if not await collector.initialize():
        print("初始化失败")
        return

    print("\n[第一次运行] 采集新数据...")
    print("-" * 80)

    await collector._collect_once()

    with create_session() as db:
        count = db.query(FinancialTimesMessage).filter(
            FinancialTimesMessage.source_id == config['id']
        ).count()
        print(f"\n数据库记录数: {count}")

        if count > 0:
            latest = db.query(FinancialTimesMessage).filter(
                FinancialTimesMessage.source_id == config['id']
            ).order_by(
                FinancialTimesMessage.published_at.desc()
            ).first()

            print(f"\n最新记录示例:")
            print(f"  标题: {latest.title}")
            print(f"  URL: {latest.url}")
            print(f"  发布时间: {latest.published_at}")
            print(f"  作者: {latest.provider or 'N/A'}")
            print(f"  摘要长度: {len(latest.summary or '')} 字符")
            print(f"  内容长度: {len(latest.content)} 字符")
            print(f"  地区: {latest.region}")
            print(f"  行业标签: {latest.industry_tags or 'N/A'}")
            print(f"  AI标签: {latest.ai_tag or 'N/A'}")

    print("\n" + "-" * 80)
    print("[第二次运行] 测试去重机制...")
    print("-" * 80)

    await collector._collect_once()

    with create_session() as db:
        count_after = db.query(FinancialTimesMessage).filter(
            FinancialTimesMessage.source_id == config['id']
        ).count()
        print(f"\n数据库记录数（第二次）: {count_after}")

        if count_after == count:
            print("[OK] 去重机制正常工作！第二次运行未产生重复数据")
        else:
            print(f"[警告] 去重可能有问题，记录数增加了 {count_after - count} 条")

    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_collector())
