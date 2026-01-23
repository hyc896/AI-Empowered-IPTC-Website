"""
测试 qwen-max 模型
"""
import asyncio
from openai import AsyncOpenAI

async def test_qwen_max():
    """测试阿里云通义千问 qwen-max 模型"""

    api_key = "sk-da598e8ebde449dfbb3d4578854b0502"
    base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    client = AsyncOpenAI(
        api_key=api_key,
        base_url=base_url,
        timeout=60.0
    )

    try:
        print("🔄 测试 qwen-max 模型...")
        response = await client.chat.completions.create(
            model="qwen-max",
            messages=[
                {"role": "user", "content": "你好，请回复'测试成功'"}
            ],
            temperature=0.3,
            max_tokens=100
        )

        print("✅ qwen-max 模型连接成功！")
        print(f"响应: {response.choices[0].message.content}")
        return True

    except Exception as e:
        print(f"❌ qwen-max 模型连接失败: {e}")
        print(f"错误类型: {type(e).__name__}")
        print(f"错误详情: {str(e)}")
        return False

if __name__ == "__main__":
    asyncio.run(test_qwen_max())
