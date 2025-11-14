# -*- coding: utf-8 -*-

"""
FARI采集器测试脚本

用途：测试采集器的基本功能，包括：
1. 初始化成功
2. 列表页爬取
3. 详情页提取
4. 数据存储
"""

import asyncio
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from collector import FARICollector

# 测试配置
test_config = {
    'id': '62d0c054-bf22-11f0-8cb6-00ff40160484',
    'name': 'fari',
    'mysql_table': 'mp_fari_messages',
    'chroma_collection': 'fari',
    'interval': 86400,
    'config': {
        'news_url': 'https://www.fari.brussels/news-and-media/news',
        'publications_url': 'https://www.fari.brussels/research-and-innovation/publications',
        'region': 'BE',
        'language': 'en'
    }
}


async def main():
    """主测试函数"""
    print("=" * 60)
    print("FARI Collector Test Script")
    print("=" * 60)

    # 创建采集器实例
    collector = FARICollector(test_config)

    # 初始化
    print("\n[1/3] 初始化采集器...")
    if not await collector.initialize():
        print("❌ 初始化失败")
        return

    print("✓ 初始化成功")

    # 执行一次采集
    print("\n[2/3] 执行采集（仅采集第一页）...")
    try:
        await collector._collect_once()
        print("✓ 采集完成")
    except Exception as e:
        print(f"❌ 采集失败: {e}")
        import traceback
        traceback.print_exc()

    # 关闭浏览器
    print("\n[3/3] 清理资源...")
    await collector._close_browser()
    print("✓ 资源清理完成")

    print("\n" + "=" * 60)
    print("测试完成！请检查数据库 mp_fari_messages 表中的数据")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
