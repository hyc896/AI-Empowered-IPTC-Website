"""测试API接口并查看响应内容"""
import requests
import json

base_url = "https://mfindecupl.libsp.cn"
endpoints = ['/api/books', '/api/book/list', '/api/search']

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://mfindecupl.libsp.cn/'
})

for endpoint in endpoints:
    print(f"\n{'='*60}")
    print(f"测试: {endpoint}")
    print('='*60)

    try:
        resp = session.get(f"{base_url}{endpoint}", timeout=10)
        print(f"状态码: {resp.status_code}")
        print(f"Content-Type: {resp.headers.get('Content-Type')}")

        try:
            data = resp.json()
            print(f"\nJSON响应:")
            print(json.dumps(data, ensure_ascii=False, indent=2)[:500])
        except:
            print(f"\nHTML/文本响应 (前500字符):")
            print(resp.text[:500])

    except Exception as e:
        print(f"错误: {e}")
