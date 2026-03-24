# 消息平台 API 客户端使用指南

## 配置

在 `.env` 文件中配置消息平台地址：

```bash
MESSAGE_PLATFORM_URL=http://localhost:11528
```

## 使用示例

### 1. 获取最近消息

```python
from backend.clients import get_message_platform_client

client = get_message_platform_client()

# 获取最近20条消息
result = client.get_messages(limit=20)
print(f"获取到 {result['total']} 条消息")

for msg in result['messages']:
    print(f"- {msg['title']}")
```

### 2. 按消息源类型筛选

```python
# 获取新闻类消息
result = client.get_messages(source_type="news", limit=50)

# 获取学术类消息
result = client.get_messages(source_type="academic", limit=30)
```

### 3. 按时间范围筛选

```python
# 获取最近24小时的消息
result = client.get_messages(hours=24, limit=100)
```

### 4. 搜索消息

```python
# 关键词搜索
result = client.search_messages(
    query="人工智能",
    source_type="news",
    time_range={"hours": 48},
    limit=50
)

print(f"搜索到 {result['total']} 条相关消息")
print(f"搜索耗时: {result['search_time']}秒")

for msg in result['results']:
    print(f"- {msg['title']} (相似度: {msg.get('similarity', 'N/A')})")
```

## API 响应格式

### get_messages 响应

```json
{
  "messages": [
    {
      "id": "uuid",
      "title": "消息标题",
      "content": "消息内容",
      "summary": "摘要",
      "url": "原文链接",
      "published_at": "2026-03-07T00:00:00",
      "provider": "提供方",
      "source_name": "消息源名称"
    }
  ],
  "total": 100
}
```

### search_messages 响应

```json
{
  "results": [...],
  "total": 50,
  "query": "搜索关键词",
  "search_time": 0.5
}
```
