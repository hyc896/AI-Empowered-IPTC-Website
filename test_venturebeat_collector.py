# -*- coding: utf-8 -*-

"""
VentureBeat采集器测试脚本
测试VentureBeat科技媒体采集功能
"""

import asyncio
import sys
import os
from pathlib import Path

# 设置UTF-8编码输出（Windows终端兼容）
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加项目根目录到系统路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Windows环境设置异步事件循环策略
if sys.platform.startswith('win'):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


async def test_venturebeat_collector():
    """测试VentureBeat采集器"""
    print("=" * 80)
    print("VentureBeat采集器测试")
    print("=" * 80)

    try:
        # 导入配置和采集器
        from backend.config import get_config, GlobalConfig
        from backend.sources.venturebeat.collector import VentureBeatCollector
        from backend.database.connection import create_session
        from backend.database.entities import VentureBeatMessage

        # 初始化配置
        global_config = GlobalConfig.get_instance()
        global_config.initialize("config.yaml")

        # 获取配置
        config = get_config()
        print("\n✓ 配置加载成功")

        # 初始化LLM客户端（用于翻译和字段增强）
        from backend.llm.global_llm_manager import GlobalLLMManager
        llm_config = config.get("llm", {})
        llm_manager = GlobalLLMManager.get_instance()
        llm_manager.initialize(
            chat_config=None,  # 消息平台不需要Chat主模型
            embedding_config=llm_config.get("embedding", {}),
            fast_config=llm_config.get("fast", {})
        )
        print("✓ LLM客户端初始化成功")

        # 从数据库获取消息源配置
        with create_session() as db:
            from backend.database.entities import MessageSource
            source = db.query(MessageSource).filter(MessageSource.name == 'venturebeat').first()

            if not source:
                print("\n✗ 错误：未找到VentureBeat消息源配置")
                print("请先执行注册脚本：mysql -e 'source backend/sources/venturebeat/register.sql'")
                return

            source_config = {
                'id': source.id,
                'name': source.name,
                'interval': 86400,
                'mysql_table': source.config.get('mysql_table'),
                'chroma_collection': source.config.get('chroma_collection'),
                'config': {
                    'categories': source.config.get('categories', ['ai', 'data-infrastructure', 'security']),
                    'region': source.config.get('region', 'US'),
                    'language': source.config.get('language', 'en')
                }
            }

        print(f"✓ 消息源配置加载成功")
        print(f"  - 消息源ID: {source_config['id']}")
        print(f"  - 采集栏目: {', '.join(source_config['config']['categories'])}")

        # 创建采集器实例
        collector = VentureBeatCollector(source_config)
        print("\n✓ 采集器实例创建成功")

        # 初始化采集器
        if not await collector.initialize():
            print("\n✗ 采集器初始化失败")
            return

        print("✓ 采集器初始化成功")

        # 执行一次采集
        print("\n" + "=" * 80)
        print("开始采集...")
        print("=" * 80)

        await collector._collect_once()

        # 关闭采集器
        await collector.stop()

        # 查询采集结果
        print("\n" + "=" * 80)
        print("采集结果统计")
        print("=" * 80)

        with create_session() as db:
            total_count = db.query(VentureBeatMessage).filter(
                VentureBeatMessage.source_id == source_config['id']
            ).count()

            latest_messages = db.query(VentureBeatMessage).filter(
                VentureBeatMessage.source_id == source_config['id']
            ).order_by(
                VentureBeatMessage.published_at.desc()
            ).limit(5).all()

            print(f"\n总记录数: {total_count}")
            print("\n最新5条消息:")
            print("-" * 80)

            for idx, msg in enumerate(latest_messages, 1):
                print(f"\n[{idx}] {msg.title}")
                print(f"    URL: {msg.url}")
                print(f"    分类: {msg.category}")
                print(f"    作者: {msg.provider or 'N/A'}")
                print(f"    发布时间: {msg.published_at}")
                print(f"    地区: {msg.region or 'N/A'}")
                print(f"    行业标签: {msg.industry_tags or 'N/A'}")
                print(f"    摘要: {msg.summary[:100] if msg.summary else 'N/A'}...")

        print("\n" + "=" * 80)
        print("✓ 测试完成")
        print("=" * 80)

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_venturebeat_collector())
