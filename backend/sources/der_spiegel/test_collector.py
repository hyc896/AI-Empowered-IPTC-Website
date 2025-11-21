# -*- coding: utf-8 -*-

"""
Der Spiegel采集器测试脚本

测试流程：
1. 测试RSS Feed解析
2. 测试采集器初始化
3. 测试单次采集（包括德语翻译）
4. 验证数据库存储
5. 检查去重机制
"""

import sys
import asyncio
import io
from pathlib import Path

# 设置UTF-8输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.sources.der_spiegel.collector import DerSpiegelCollector
from backend.database.connection import create_session
from backend.database.entities import DerSpiegelMessage
from sqlalchemy import func


async def test_collector():
    """测试采集器"""

    print("=" * 80)
    print("Der Spiegel Netzwelt 采集器测试")
    print("=" * 80)

    # 从数据库获取消息源配置
    with create_session() as db:
        from backend.database.entities import MessageSource
        source = db.query(MessageSource).filter(
            MessageSource.name == 'Der Spiegel Netzwelt'
        ).first()

        if not source:
            print("❌ 错误：未找到Der Spiegel Netzwelt消息源配置")
            print("请先执行 register.sql 注册消息源")
            return

        print(f"\n✅ 找到消息源配置:")
        print(f"   ID: {source.id}")
        print(f"   名称: {source.name}")
        print(f"   分类: {source.category}")
        print(f"   状态: {'启用' if source.is_active else '禁用'}")

        # 准备配置
        config = {
            'id': source.id,
            'interval': 3600,
            'config': source.config
        }

    # 初始化采集器
    print("\n" + "=" * 80)
    print("步骤1: 初始化采集器")
    print("=" * 80)

    collector = DerSpiegelCollector(config)
    success = await collector.initialize()

    if not success:
        print("❌ 采集器初始化失败")
        return

    print("✅ 采集器初始化成功")

    # 检查数据库当前状态
    print("\n" + "=" * 80)
    print("步骤2: 检查数据库当前状态")
    print("=" * 80)

    with create_session() as db:
        count_before = db.query(func.count(DerSpiegelMessage.id)).scalar()
        print(f"当前数据库记录数: {count_before}")

        if count_before > 0:
            latest = db.query(DerSpiegelMessage).order_by(
                DerSpiegelMessage.published_at.desc()
            ).first()
            print(f"最新记录:")
            print(f"  标题: {latest.title}")
            print(f"  URL: {latest.url}")
            print(f"  发布时间: {latest.published_at}")
            print(f"  语言: {latest.language}")

    # 执行采集
    print("\n" + "=" * 80)
    print("步骤3: 执行单次采集（包括德语翻译）")
    print("=" * 80)

    await collector._collect_once()

    # 检查采集结果
    print("\n" + "=" * 80)
    print("步骤4: 检查采集结果")
    print("=" * 80)

    with create_session() as db:
        count_after = db.query(func.count(DerSpiegelMessage.id)).scalar()
        new_count = count_after - count_before

        print(f"采集前记录数: {count_before}")
        print(f"采集后记录数: {count_after}")
        print(f"新增记录数: {new_count}")

        if new_count > 0:
            print(f"\n✅ 成功采集 {new_count} 条新记录")

            # 显示前3条新记录
            latest_records = db.query(DerSpiegelMessage).order_by(
                DerSpiegelMessage.crawled_at.desc()
            ).limit(3).all()

            print("\n最新采集的记录（前3条）:")
            for i, record in enumerate(latest_records, 1):
                print(f"\n【记录 {i}】")
                print(f"  标题: {record.title}")
                print(f"  URL: {record.url}")
                print(f"  发布时间: {record.published_at}")
                print(f"  语言: {record.language}")
                print(f"  地区: {record.region}")
                print(f"  行业标签: {record.industry_tags}")
                print(f"  AI标签: {record.ai_tag}")
                print(f"  作者: {record.provider or 'N/A'}")
                print(f"  原文内容长度: {len(record.content)} 字符")
                print(f"  原文前150字: {record.content[:150]}...")
                if record.summary:
                    print(f"  中文摘要长度: {len(record.summary)} 字符")
                    print(f"  中文摘要前150字: {record.summary[:150]}...")
                else:
                    print(f"  中文摘要: 无")
        else:
            print("\n⚠️  没有新增记录（可能所有记录都已存在）")

    # 测试去重机制
    print("\n" + "=" * 80)
    print("步骤5: 测试去重机制（第二次采集）")
    print("=" * 80)

    await collector._collect_once()

    with create_session() as db:
        count_second = db.query(func.count(DerSpiegelMessage.id)).scalar()
        new_count_second = count_second - count_after

        print(f"第二次采集前记录数: {count_after}")
        print(f"第二次采集后记录数: {count_second}")
        print(f"第二次新增记录数: {new_count_second}")

        if new_count_second == 0:
            print("\n✅ 去重机制正常工作（第二次采集没有重复插入）")
        else:
            print(f"\n⚠️  第二次采集新增了 {new_count_second} 条记录（可能是RSS更新了）")

    # 字段映射验证
    print("\n" + "=" * 80)
    print("步骤6: 字段映射验证")
    print("=" * 80)

    with create_session() as db:
        sample = db.query(DerSpiegelMessage).order_by(
            DerSpiegelMessage.crawled_at.desc()
        ).first()

        if sample:
            print("✅ 字段映射检查:")
            print(f"  ✓ external_id: {sample.external_id}")
            print(f"  ✓ title: {sample.title[:50]}...")
            print(f"  ✓ content (德语): {len(sample.content)} 字符")
            print(f"  ✓ summary (中文): {len(sample.summary) if sample.summary else 0} 字符")
            print(f"  ✓ url: {sample.url}")
            print(f"  ✓ provider: {sample.provider or 'N/A'}")
            print(f"  ✓ published_at: {sample.published_at}")
            print(f"  ✓ crawled_at: {sample.crawled_at}")
            print(f"  ✓ region: {sample.region}")
            print(f"  ✓ industry_tags: {sample.industry_tags}")
            print(f"  ✓ ai_tag: {sample.ai_tag}")
            print(f"  ✓ language: {sample.language}")

            # 验证德语内容标记
            if sample.language == 'de':
                print("\n✅ 语言标记正确: language='de' (德语)")
            else:
                print(f"\n❌ 语言标记错误: language='{sample.language}' (应为'de')")

            # 验证翻译
            if sample.summary and sample.summary != sample.content:
                print("✅ 翻译功能正常: summary与content不同（已翻译成中文）")
            elif sample.summary == sample.content:
                print("⚠️  翻译可能未生效: summary与content相同")
            else:
                print("⚠️  summary为空")

    print("\n" + "=" * 80)
    print("测试完成！")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_collector())
