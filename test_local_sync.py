#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
本地测试脚本：模拟消息同步流程
用于在无法连接 message_platform API 时测试整套流程
"""

import sys
from datetime import datetime, timedelta

# 模拟 API 返回的消息数据
MOCK_MESSAGES = [
    {
        "id": "test_001",
        "title": "人工智能技术在医疗领域的应用研究",
        "content": "近年来，人工智能技术在医疗领域取得了显著进展。深度学习算法在医学影像诊断、疾病预测等方面展现出巨大潜力。",
        "summary": "AI技术在医疗领域的应用进展",
        "url": "https://example.com/ai-medical-001",
        "published_at": (datetime.now() - timedelta(hours=1)).isoformat(),
        "provider": "测试作者",
        "source_name": "guardian"
    },
    {
        "id": "test_002",
        "title": "全球气候变化对经济的影响分析",
        "content": "气候变化正在对全球经济产生深远影响。极端天气事件频发，给农业、能源等行业带来挑战。",
        "summary": "气候变化的经济影响",
        "url": "https://example.com/climate-002",
        "published_at": (datetime.now() - timedelta(hours=2)).isoformat(),
        "provider": "经济学家",
        "source_name": "bloomberg"
    },
]


def test_sync_service():
    """测试消息同步服务"""
    print("="*60)
    print("【本地测试】开始测试消息同步流程")
    print("="*60)

    try:
        # 先注册 ORM 模型
        from backend.database.orm_registry import auto_register_all_models
        auto_register_all_models()

        from backend.services.message_sync_service import MessageSyncService

        # 创建同步服务
        sync_service = MessageSyncService()

        # 同步模拟消息
        print(f"\n正在同步 {len(MOCK_MESSAGES)} 条模拟消息...")
        stats = sync_service.sync_messages(MOCK_MESSAGES)

        print(f"\n同步结果:")
        print(f"  成功: {stats['success']}")
        print(f"  重复: {stats['duplicate']}")
        print(f"  失败: {stats['error']}")

        if stats['success'] > 0:
            print("\n[成功] 消息同步成功！")
            return True
        else:
            print("\n[失败] 消息同步失败")
            return False

    except Exception as e:
        print(f"\n[错误] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_vector_sync():
    """测试向量同步"""
    print("\n" + "="*60)
    print("【本地测试】测试向量同步")
    print("="*60)

    try:
        from backend.services.message.vector_sync import startup_vector_sync
        import asyncio

        print("\n正在检查向量同步...")
        asyncio.run(startup_vector_sync(full_sync=False))

        print("\n[成功] 向量同步完成！")
        return True

    except Exception as e:
        print(f"\n[失败] 向量同步失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试流程"""
    print("\n" + "="*60)
    print("IPTC 消息同步本地测试")
    print("="*60)
    print("\n说明: 由于无法连接服务器 API，使用模拟数据测试")
    print("\n测试流程:")
    print("  1. 消息同步服务测试")
    print("  2. 向量同步测试")
    print("  3. (可选) 案例生成测试")
    print("\n" + "="*60)

    # 测试1: 消息同步
    if not test_sync_service():
        print("\n测试中断：消息同步失败")
        return

    # 测试2: 向量同步
    if not test_vector_sync():
        print("\n警告：向量同步失败，但可以继续")

    print("\n" + "="*60)
    print("【测试完成】")
    print("="*60)
    print("\n后续步骤:")
    print("  1. 检查 MySQL 数据库中是否有新消息")
    print("  2. 检查 ChromaDB 中是否有新向量")
    print("  3. 运行案例生成: python backend/scripts/batch_match_cases.py")
    print("\n" + "="*60)


if __name__ == '__main__':
    main()
