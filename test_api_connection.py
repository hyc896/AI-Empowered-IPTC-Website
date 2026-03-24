#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
API 连接诊断脚本
测试 message_platform API 的可访问性
"""

import socket
import requests
import time
import os

API_HOST = "8.153.174.176"
API_PORT = 11528
API_URL = f"http://{API_HOST}:{API_PORT}"

# 认证信息
CLIENT_ID = os.getenv('MESSAGE_PLATFORM_CLIENT_ID', 'b861b6cd-af4a-4daf-8d71-3d006bf9737d')
API_KEY = os.getenv('MESSAGE_PLATFORM_API_KEY', 'GSuNRKNF7sYZlm8Xif5nSFVQh_wBiBFua_txgQIVvAJdNAaGNXBGpEAVt-YZBbcc')

def get_headers():
    """获取认证请求头"""
    return {
        'X-Client-ID': CLIENT_ID,
        'X-API-Key': API_KEY
    }

def test_tcp_connection():
    """测试TCP连接"""
    print("\n[测试1] TCP端口连接测试")
    print(f"目标: {API_HOST}:{API_PORT}")

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        result = sock.connect_ex((API_HOST, API_PORT))
        sock.close()

        if result == 0:
            print("✓ TCP端口可达")
            return True
        else:
            print(f"✗ TCP端口不可达 (错误码: {result})")
            return False
    except Exception as e:
        print(f"✗ 连接失败: {e}")
        return False

def test_http_request():
    """测试HTTP请求"""
    print("\n[测试2] HTTP请求测试")
    print(f"URL: {API_URL}/mp/v1/sources")

    try:
        response = requests.get(
            f"{API_URL}/mp/v1/sources",
            headers=get_headers(),
            timeout=10
        )
        print(f"✓ HTTP请求成功")
        print(f"  状态码: {response.status_code}")
        print(f"  响应大小: {len(response.content)} bytes")

        if response.status_code == 200:
            data = response.json()
            print(f"  消息源数量: {len(data)}")
            return True
        return False

    except requests.exceptions.Timeout:
        print("✗ 请求超时（10秒）")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"✗ 连接错误: {e}")
        return False
    except Exception as e:
        print(f"✗ 请求失败: {e}")
        return False

def test_search_messages():
    """测试消息搜索API"""
    print("\n[测试3] 消息搜索API测试")
    print(f"URL: {API_URL}/search/messages")

    try:
        response = requests.get(
            f"{API_URL}/search/messages",
            params={"hours": 24, "limit": 5},
            headers=get_headers(),
            timeout=10
        )
        print(f"✓ API请求成功")
        print(f"  状态码: {response.status_code}")

        if response.status_code == 200:
            messages = response.json()
            print(f"  返回消息数: {len(messages)}")
            if messages:
                print(f"  第一条消息标题: {messages[0].get('title', 'N/A')[:50]}...")
            return True
        return False

    except Exception as e:
        print(f"✗ 请求失败: {e}")
        return False

def main():
    print("="*60)
    print("Message Platform API 连接诊断")
    print("="*60)
    print(f"\n目标服务器: {API_HOST}")
    print(f"目标端口: {API_PORT}")
    print(f"API地址: {API_URL}")

    results = []

    # 测试1: TCP连接
    results.append(("TCP连接", test_tcp_connection()))
    time.sleep(1)

    # 测试2: HTTP请求
    results.append(("HTTP请求", test_http_request()))
    time.sleep(1)

    # 测试3: 消息API
    results.append(("消息API", test_search_messages()))

    # 总结
    print("\n" + "="*60)
    print("诊断结果总结")
    print("="*60)

    for name, success in results:
        status = "✓ 通过" if success else "✗ 失败"
        print(f"{name:15s}: {status}")

    all_passed = all(r[1] for r in results)

    if all_passed:
        print("\n✓ 所有测试通过！API可以正常访问。")
    else:
        print("\n✗ 部分测试失败。可能的原因：")
        print("  1. 服务器防火墙未开放端口11528")
        print("  2. 本地网络限制（公司防火墙、代理等）")
        print("  3. message_platform服务未启动")
        print("\n建议：")
        print("  - 检查服务器防火墙配置")
        print("  - 尝试使用VPN或其他网络环境")
        print("  - 联系服务器管理员确认端口开放情况")

if __name__ == '__main__':
    main()
