# -*- coding: utf-8 -*-

"""
The Guardian Collector测试脚本

用途：
1. 测试采集器基本功能
2. 验证去重逻辑
3. 检查数据质量

运行方式：
python backend/sources/guardian/test_collector.py
"""

import sys
import os
import asyncio

# Windows控制台编码设置
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from backend.sources.guardian.collector import GuardianCollector
from backend.database.connection import create_session
from backend.database.entities import GuardianMessage, MessageSource


async def test_guardian_collector():
    """测试Guardian采集器"""
    print("=" * 80)
    print("The Guardian Collector测试")
    print("=" * 80)

    # 1. 从数据库获取消息源配置
    print("\n[1] 加载消息源配置...")
    with create_session() as db:
        source = db.query(MessageSource).filter(MessageSource.name == 'guardian').first()
        if not source:
            print("❌ 错误：guardian消息源未注册")
            return

        config = {
            'id': source.id,
            'config': source.config
        }
        print(f"✓ 消息源ID: {source.id}")
        print(f"✓ 显示名称: {source.display_name}")
        print(f"✓ RSS源数量: {len(source.config.get('rss_feeds', []))}")

    # 2. 初始化采集器
    print("\n[2] 初始化采集器...")
    collector = GuardianCollector(config)
    if not await collector.initialize():
        print("❌ 采集器初始化失败")
        return
    print("✓ 采集器初始化成功")

    # 3. 查询初始状态
    print("\n[3] 查询初始数据库状态...")
    with create_session() as db:
        initial_count = db.query(GuardianMessage).count()
        latest = db.query(GuardianMessage).order_by(
            GuardianMessage.crawled_at.desc()
        ).first()

        print(f"✓ 数据库中已有 {initial_count} 条消息")
        if latest:
            print(f"✓ 最新消息URL: {latest.url}")
            print(f"✓ 最新消息时间: {latest.published_at}")

    # 4. 执行采集
    print("\n[4] 执行采集...")
    await collector._collect_once()

    # 5. 查询采集后状态
    print("\n[5] 查询采集后状态...")
    with create_session() as db:
        final_count = db.query(GuardianMessage).count()
        new_count = final_count - initial_count

        print(f"✓ 数据库中现有 {final_count} 条消息")
        print(f"✓ 新增 {new_count} 条消息")

        # 抽样检查
        if new_count > 0:
            print("\n[6] 抽样检查新消息...")
            sample = db.query(GuardianMessage).order_by(
                GuardianMessage.crawled_at.desc()
            ).limit(3).all()

            for i, msg in enumerate(sample, 1):
                print(f"\n--- 样本 {i} ---")
                print(f"标题: {msg.title[:80]}...")
                print(f"URL: {msg.url}")
                print(f"分类: {msg.category}")
                print(f"发布时间: {msg.published_at}")
                print(f"作者: {msg.provider}")
                print(f"地区: {msg.region}")
                print(f"行业标签: {msg.industry_tags}")
                print(f"AI标签: {msg.ai_tag}")

                if msg.summary:
                    summary_preview = msg.summary[:200] + "..." if len(msg.summary) > 200 else msg.summary
                    print(f"摘要预览: {summary_preview}")
                else:
                    print("摘要: (无)")

    # 6. 测试去重
    print("\n[7] 测试去重逻辑（再次采集）...")
    await collector._collect_once()

    with create_session() as db:
        duplicate_count = db.query(GuardianMessage).count()
        print(f"✓ 数据库中仍有 {duplicate_count} 条消息（应与上次相同）")

        if duplicate_count == final_count:
            print("✓ 去重逻辑正常工作")
        else:
            print(f"⚠️ 警告：消息数量变化（{final_count} → {duplicate_count}）")

    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)


if __name__ == "__main__":
    # Windows环境兼容
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(test_guardian_collector())
