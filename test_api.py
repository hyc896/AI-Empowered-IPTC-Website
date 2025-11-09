#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
直接测试消息平台API
"""

import asyncio
import httpx
import json

async def test_api():
    """测试API"""
    print("=== 直接测试消息平台API ===")

    try:
        # 测试搜索API
        url = "http://localhost:11523/api/v1/search/messages"
        data = {
            "query": "汽车",
            "source_type": "news",
            "limit": 3
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=data)

            print(f"状态码: {response.status_code}")
            print(f"响应: {response.text}")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_api())