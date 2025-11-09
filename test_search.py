#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试消息平台搜索功能
"""

import asyncio
import httpx
import json

async def test_search():
    """测试搜索功能"""
    print("=== 测试消息平台搜索功能 ===")

    try:
        async with httpx.AsyncClient() as client:
            # 测试新闻搜索
            url = "http://localhost:11523/api/v1/search/messages"
            data = {
                "query": "中国",
                "source_type": "news",
                "limit": 3
            }

            print(f"发送请求: {url}")
            print(f"请求数据: {json.dumps(data, ensure_ascii=False)}")

            response = await client.post(url, json=data)

            print(f"状态码: {response.status_code}")
            print(f"响应: {response.text}")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_search())