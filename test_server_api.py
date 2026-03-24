#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
服务器端 API 测试脚本
在 message_platform 服务器上运行此脚本来验证API
"""

import requests
import json

def test_local_api():
    """测试本地API"""
    print("="*60)
    print("Message Platform 本地API测试")
    print("="*60)

    # 测试1: 获取消息源列表
    print("\n[测试1] 获取消息源列表")
    try:
        response = requests.get("http://localhost:11528/mp/v1/sources", timeout=5)
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            sources = response.json()
            print(f"✓ 成功获取 {len(sources)} 个消息源")
            print("\n前5个消息源:")
            for s in sources[:5]:
                print(f"  - {s.get('name')}: {s.get('display_name')}")
        else:
            print(f"✗ 请求失败: {response.text}")
    except Exception as e:
        print(f"✗ 错误: {e}")

    # 测试2: 获取最近消息
    print("\n[测试2] 获取最近24小时的消息")
    try:
        response = requests.get(
            "http://localhost:11528/search/messages",
            params={"hours": 24, "limit": 5},
            timeout=5
        )
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            messages = response.json()
            print(f"✓ 成功获取 {len(messages)} 条消息")
            if messages:
                print("\n第一条消息:")
                msg = messages[0]
                print(f"  标题: {msg.get('title', 'N/A')[:60]}")
                print(f"  来源: {msg.get('source_name', 'N/A')}")
                print(f"  URL: {msg.get('url', 'N/A')[:60]}")
        else:
            print(f"✗ 请求失败: {response.text}")
    except Exception as e:
        print(f"✗ 错误: {e}")

    print("\n" + "="*60)
    print("测试完成")
    print("="*60)

if __name__ == '__main__':
    test_local_api()
