# -*- coding: utf-8 -*-

"""
测试FieldEnricher的串行等待逻辑
验证：仅当industry_tags包含"人工智能"时才执行ai_tag分类
"""

import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(__file__))

from backend.config import GlobalConfig
from backend.llm import GlobalLLMManager
from backend.services import get_field_enricher


async def init_llm_clients():
    """初始化LLM客户端"""
    # 初始化GlobalConfig
    global_config = GlobalConfig.get_instance()
    global_config.initialize("config.yaml")

    llm_config = global_config.get_config("llm", {})
    chat_config = llm_config.get('chat', {})
    embedding_config = llm_config.get('embedding', {})
    fast_config = llm_config.get('fast', {})

    llm_manager = GlobalLLMManager()
    llm_manager.initialize(chat_config, embedding_config, fast_config)

    print("[OK] LLM客户端初始化完成")


async def test_ai_message():
    """测试1: AI相关消息（应该执行ai_tag分类）"""
    print("\n" + "="*60)
    print("测试1: AI相关消息")
    print("="*60)

    field_enricher = get_field_enricher()

    title = "Anthropic将在美国投资500亿美元建设数据中心"
    content = "Anthropic公司宣布将在美国投资500亿美元建设AI数据中心，用于训练大型语言模型。"

    print(f"标题: {title}")
    print(f"内容: {content[:50]}...")

    result = await field_enricher.enrich_fields(title, content)

    print(f"\n结果:")
    print(f"  region: {result['region']}")
    print(f"  industry_tags: {result['industry_tags']}")
    print(f"  ai_tag: {result['ai_tag']}")

    # 验证：应该包含"人工智能"且ai_tag不为None
    if result['industry_tags'] and "人工智能" in result['industry_tags']:
        print("[OK] industry_tags包含'人工智能'")
        if result['ai_tag']:
            print(f"[OK] ai_tag已执行: {result['ai_tag']}")
        else:
            print("[FAIL] ai_tag未执行（预期应该执行）")
    else:
        print(f"[FAIL] industry_tags不包含'人工智能': {result['industry_tags']}")


async def test_non_ai_message():
    """测试2: 非AI相关消息（不应该执行ai_tag分类）"""
    print("\n" + "="*60)
    print("测试2: 非AI相关消息")
    print("="*60)

    field_enricher = get_field_enricher()

    title = "现货黄金站上4170美元/盎司"
    content = "国际现货黄金价格突破4170美元/盎司，创历史新高。市场分析认为，全球经济不确定性推动避险需求上升。"

    print(f"标题: {title}")
    print(f"内容: {content[:50]}...")

    result = await field_enricher.enrich_fields(title, content)

    print(f"\n结果:")
    print(f"  region: {result['region']}")
    print(f"  industry_tags: {result['industry_tags']}")
    print(f"  ai_tag: {result['ai_tag']}")

    # 验证：不应该包含"人工智能"且ai_tag为None
    if result['industry_tags'] and "人工智能" in result['industry_tags']:
        print(f"[FAIL] industry_tags包含'人工智能'（预期不应该包含）: {result['industry_tags']}")
    else:
        print(f"[OK] industry_tags不包含'人工智能': {result['industry_tags']}")

    if result['ai_tag'] is None:
        print("[OK] ai_tag未执行（符合预期）")
    else:
        print(f"[FAIL] ai_tag已执行（预期不应该执行）: {result['ai_tag']}")


async def test_mixed_message():
    """测试3: 混合行业但包含AI（应该执行ai_tag分类）"""
    print("\n" + "="*60)
    print("测试3: 混合行业但包含AI")
    print("="*60)

    field_enricher = get_field_enricher()

    title = "英伟达发布新一代AI芯片，性能提升10倍"
    content = "英伟达公司发布新一代AI训练芯片，采用全新架构，性能较上一代提升10倍。"

    print(f"标题: {title}")
    print(f"内容: {content[:50]}...")

    result = await field_enricher.enrich_fields(title, content)

    print(f"\n结果:")
    print(f"  region: {result['region']}")
    print(f"  industry_tags: {result['industry_tags']}")
    print(f"  ai_tag: {result['ai_tag']}")

    # 验证：应该包含"人工智能"（可能还有"半导体/芯片"）且ai_tag不为None
    if result['industry_tags'] and "人工智能" in result['industry_tags']:
        print("[OK] industry_tags包含'人工智能'")
        if result['ai_tag']:
            print(f"[OK] ai_tag已执行: {result['ai_tag']}")
        else:
            print("[FAIL] ai_tag未执行（预期应该执行）")
    else:
        print(f"[FAIL] industry_tags不包含'人工智能': {result['industry_tags']}")


async def main():
    """主函数"""
    print("="*60)
    print("FieldEnricher串行等待逻辑测试")
    print("="*60)

    # 初始化LLM客户端
    await init_llm_clients()

    # 运行三个测试
    await test_ai_message()
    await test_non_ai_message()
    await test_mixed_message()

    print("\n" + "="*60)
    print("测试完成")
    print("="*60)


if __name__ == "__main__":
    # Windows环境设置
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(main())
