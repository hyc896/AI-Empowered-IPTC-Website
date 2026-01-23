"""
测试实体提取功能
"""
import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, r"E:\All Code\Vue\luxinglong\GraphRAG")

from graphrag.llm.openai_client import OpenAIClient

async def test_extraction():
    """测试实体提取"""

    # 从环境变量读取配置
    api_key = "sk-da598e8ebde449dfbb3d4578854b0502"
    base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    model = "qwen-plus"

    print(f"🔄 初始化 OpenAI 客户端...")
    print(f"   模型: {model}")
    print(f"   Base URL: {base_url}")

    client = OpenAIClient(
        api_key=api_key,
        model=model,
        base_url=base_url
    )

    # 测试文本
    test_text = """
    苹果公司（Apple Inc.）是一家美国跨国科技公司，总部位于加利福尼亚州库比蒂诺。
    该公司由史蒂夫·乔布斯、史蒂夫·沃兹尼亚克和罗纳德·韦恩于1976年创立。
    苹果公司以其创新的产品而闻名，包括iPhone、iPad和Mac电脑。
    """

    prompt = f"""
请从以下文本中提取实体和关系，以JSON格式返回。

文本：
{test_text}

要求：
1. 提取所有重要实体（公司、人物、地点、产品等）
2. 提取实体之间的关系
3. 返回格式：
{{
  "entities": [
    {{"name": "实体名称", "type": "实体类型", "description": "描述"}}
  ],
  "relations": [
    {{"source": "源实体", "target": "目标实体", "type": "关系类型"}}
  ]
}}
"""

    try:
        print(f"\n🔄 开始提取实体...")
        response = await client.generate_async(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=2000
        )

        print(f"\n✅ 提取成功！")
        print(f"\n响应内容：")
        print(response.choices[0].message.content)

        return True

    except Exception as e:
        print(f"\n❌ 提取失败: {e}")
        print(f"错误类型: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(test_extraction())
