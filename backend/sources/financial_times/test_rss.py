# -*- coding: utf-8 -*-
"""
测试Financial Times RSS Feed的可访问性和数据结构
"""

import feedparser
from datetime import datetime
from time import mktime


def test_ft_rss():
    """测试FT的RSS Feed"""

    rss_url = "https://www.ft.com/technology?format=rss"

    print(f"正在获取RSS Feed: {rss_url}\n")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    feed = feedparser.parse(rss_url, request_headers=headers)

    if feed.bozo:
        print(f"⚠️ RSS解析警告: {feed.bozo_exception}")

    print(f"Feed标题: {feed.feed.get('title', 'N/A')}")
    print(f"Feed链接: {feed.feed.get('link', 'N/A')}")
    print(f"Feed描述: {feed.feed.get('description', 'N/A')}")
    print(f"HTTP状态: {feed.get('status', 'N/A')}")
    print(f"条目数量: {len(feed.entries)}\n")

    if not feed.entries:
        print("❌ RSS feed为空，可能无法访问")
        return

    print("=" * 80)
    print("前3条记录示例：")
    print("=" * 80)

    for i, entry in enumerate(feed.entries[:3], 1):
        print(f"\n【记录 {i}】")
        print(f"标题: {entry.get('title', 'N/A')}")
        print(f"链接: {entry.get('link', 'N/A')}")

        guid = entry.get('id') or entry.get('guid')
        if isinstance(guid, dict):
            guid = guid.get('href', '')
        print(f"GUID: {guid}")

        description = entry.get('description') or entry.get('summary', '')
        print(f"描述长度: {len(description)} 字符")
        print(f"描述预览: {description[:200]}...")

        author = entry.get('author', '').strip()
        if not author and hasattr(entry, 'dc_creator'):
            author = entry.dc_creator
        print(f"作者: {author or 'N/A'}")

        published_parsed = entry.get('published_parsed')
        if published_parsed:
            try:
                published_at = datetime.fromtimestamp(mktime(published_parsed))
                print(f"发布时间: {published_at}")
            except Exception as e:
                print(f"发布时间解析失败: {e}")
        else:
            print(f"发布时间: N/A")

        categories = []
        if hasattr(entry, 'tags'):
            categories = [tag.get('term', '') for tag in entry.tags if tag.get('term')]
        print(f"分类: {', '.join(categories) if categories else 'N/A'}")

        media_url = None
        if hasattr(entry, 'media_content'):
            media_content = entry.media_content
            if isinstance(media_content, list) and len(media_content) > 0:
                media_url = media_content[0].get('url', '')
        print(f"媒体URL: {media_url or 'N/A'}")

    print("\n" + "=" * 80)
    print(f"[OK] 测试完成！共获取 {len(feed.entries)} 条记录")
    print("=" * 80)


if __name__ == "__main__":
    test_ft_rss()
