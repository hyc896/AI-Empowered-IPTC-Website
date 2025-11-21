# -*- coding: utf-8 -*-
"""
简单测试Financial Times采集器（不依赖LLM服务）
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

import feedparser
from backend.database.connection import create_session
from backend.database.entities import FinancialTimesMessage
from datetime import datetime
from time import mktime
import uuid
from sqlalchemy.exc import IntegrityError


async def simple_test():
    """简单测试：仅测试RSS解析和数据库插入"""

    print("=" * 80)
    print("Financial Times 简单功能测试（不使用LLM服务）")
    print("=" * 80)

    rss_url = "https://www.ft.com/technology?format=rss"

    print(f"\n[步骤1] 解析RSS Feed: {rss_url}")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    feed = feedparser.parse(rss_url, request_headers=headers)

    if not feed.entries:
        print(f"[错误] RSS feed为空 (Bozo: {feed.bozo}, Status: {feed.get('status', 'N/A')})")
        return

    print(f"[成功] 获取到 {len(feed.entries)} 条记录")

    source_id = '8d4bdf4e-c4a2-11f0-b75e-08bfb82ee112'

    print(f"\n[步骤2] 检查数据库最新记录")

    with create_session() as db:
        latest = db.query(FinancialTimesMessage).filter(
            FinancialTimesMessage.source_id == source_id
        ).order_by(
            FinancialTimesMessage.published_at.desc()
        ).first()

        latest_url = latest.url if latest else None
        print(f"最新URL: {latest_url or '无记录'}")

    print(f"\n[步骤3] 提取新记录并存储")

    stored = 0
    duplicates = 0

    with create_session() as db:
        for entry in feed.entries[:5]:
            url = entry.get('link', '').strip()
            if not url:
                continue

            if latest_url and url == latest_url:
                print(f"[停止] 遇到已存在URL: {url}")
                break

            guid = entry.get('id') or entry.get('guid')
            if isinstance(guid, dict):
                guid = guid.get('href', '')

            title = entry.get('title', '').strip()
            description = entry.get('description') or entry.get('summary', '')

            author = entry.get('author', '').strip()

            published_parsed = entry.get('published_parsed')
            published_at = None
            if published_parsed:
                try:
                    published_at = datetime.fromtimestamp(mktime(published_parsed))
                except Exception as e:
                    print(f"[警告] 解析时间失败: {e}")

            try:
                message = FinancialTimesMessage(
                    id=str(uuid.uuid4()),
                    source_id=source_id,
                    external_id=guid,
                    title=title,
                    content=description,
                    summary=description,
                    provider=author or None,
                    published_at=published_at,
                    crawled_at=datetime.now(),
                    url=url,
                    region='英国',
                    industry_tags=None,
                    ai_tag=None,
                    language='en'
                )

                db.add(message)
                db.commit()
                stored += 1
                print(f"[OK] 存储: {title[:50]}...")

            except IntegrityError:
                db.rollback()
                duplicates += 1
                print(f"[重复] {url}")

            except Exception as e:
                db.rollback()
                print(f"[错误] {e}")

    print(f"\n[结果] 成功存储: {stored}, 重复: {duplicates}")

    print(f"\n[步骤4] 验证数据库")

    with create_session() as db:
        total = db.query(FinancialTimesMessage).filter(
            FinancialTimesMessage.source_id == source_id
        ).count()

        print(f"数据库总记录数: {total}")

        if total > 0:
            latest = db.query(FinancialTimesMessage).filter(
                FinancialTimesMessage.source_id == source_id
            ).order_by(
                FinancialTimesMessage.published_at.desc()
            ).first()

            print(f"\n最新记录示例:")
            print(f"  标题: {latest.title}")
            print(f"  URL: {latest.url}")
            print(f"  发布时间: {latest.published_at}")
            print(f"  作者: {latest.provider or 'N/A'}")
            print(f"  地区: {latest.region}")

    print("\n" + "=" * 80)
    print("[完成] 测试成功")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(simple_test())
