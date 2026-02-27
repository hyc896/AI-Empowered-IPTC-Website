"""
测试 LLM API 连接
"""
import asyncio
from openai import AsyncOpenAI

async def test_api():
    """测试阿里云通义千问 API"""

    api_key = "sk-da598e8ebde449dfbb3d4578854b0502"
    base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    client = AsyncOpenAI(
        api_key=api_key,
        base_url=base_url,
        timeout=30.0  # 设置 30 秒超时
    )

    try:
        print("🔄 测试 API 连接...")
        response = await client.chat.completions.create(
            model="qwen-plus",
            messages=[
                {"role": "user", "content": "你好，请回复'测试成功'"}
            ],
            temperature=0.3,
            max_tokens=100
        )

        print("✅ API 连接成功！")
        print(f"响应: {response.choices[0].message.content}")
        return True

    except Exception as e:
        print(f"❌ API 连接失败: {e}")
        print(f"错误类型: {type(e).__name__}")
        return False

if __name__ == "__main__":
    asyncio.run(test_api())
