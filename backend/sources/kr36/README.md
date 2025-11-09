# 36氪快讯采集器

## 概述

36氪快讯采集器是一个独立的Playwright爬虫服务，负责从36氪网站采集科技资讯快讯并存储到MySQL和ChromaDB。

## 特性

- 使用Playwright进行动态网页爬取
- 提取页面中的window.initialState JSON数据
- 基于item_id进行增量采集和去重
- 并发存储到MySQL（关系型数据）和ChromaDB（向量检索）
- 自动解析Unix时间戳（毫秒）
- 支持定时任务调度

## 数据库注册

在使用采集器前，需要先执行数据库注册SQL：

```bash
cd backend/services/message/sources/kr36; mysql -u root -p your_database < register.sql
```

注册SQL会完成以下操作：
1. 创建kr36_messages表
2. 在message_sources表中注册36氪消息源
3. 验证注册结果

## 配置说明

采集器配置通过构造函数的config字典传入：

```python
config = {
    'id': 'source_uuid',
    'interval': 30,
    'mysql_table': 'kr36_messages',
    'chroma_collection': 'personal_agent_kr36',
    'config': {
        'url': 'https://www.36kr.com/newsflashes'
    }
}
```

配置项说明：
- id: 消息源ID（关联message_sources表）
- interval: 采集间隔（秒），默认30秒
- mysql_table: MySQL表名
- chroma_collection: ChromaDB collection名称
- config.url: 36氪快讯页面URL

## 使用方法

### 独立运行

```python
import asyncio
from backend.services.message.sources.kr36 import Kr36Collector

async def main():
    config = {
        'id': 'your_source_id',
        'interval': 30,
        'mysql_table': 'kr36_messages',
        'chroma_collection': 'personal_agent_kr36',
        'config': {
            'url': 'https://www.36kr.com/newsflashes'
        }
    }

    collector = Kr36Collector(config)
    await collector.run()

if __name__ == '__main__':
    asyncio.run(main())
```

### 手动单次采集

```python
import asyncio
from backend.services.message.sources.kr36 import Kr36Collector

async def collect_once():
    config = {
        'id': 'your_source_id',
        'interval': 30,
        'mysql_table': 'kr36_messages',
        'chroma_collection': 'personal_agent_kr36',
        'config': {
            'url': 'https://www.36kr.com/newsflashes'
        }
    }

    collector = Kr36Collector(config)

    if await collector.initialize():
        await collector._collect_once()
        await collector.stop()

if __name__ == '__main__':
    asyncio.run(collect_once())
```

## 测试建议

### 1. 数据库连接测试

确保MySQL连接正常：

```python
from backend.database.connection import create_session
from backend.database import Kr36Message

with create_session() as db:
    count = db.query(Kr36Message).count()
    print(f"Current kr36 messages count: {count}")
```

### 2. 网页爬取测试

测试Playwright是否能正常访问36氪网站：

```python
import asyncio
from playwright.async_api import async_playwright

async def test_scrape():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto('https://www.36kr.com/newsflashes', wait_until='domcontentloaded', timeout=30000)

        await asyncio.sleep(2)

        initial_state = await page.evaluate("""
            () => {
                if (window.initialState &&
                    window.initialState.newsflashCatalogData &&
                    window.initialState.newsflashCatalogData.data &&
                    window.initialState.newsflashCatalogData.data.newsflashList &&
                    window.initialState.newsflashCatalogData.data.newsflashList.data &&
                    window.initialState.newsflashCatalogData.data.newsflashList.data.itemList) {
                    return window.initialState.newsflashCatalogData.data.newsflashList.data.itemList;
                }
                return null;
            }
        """)

        if initial_state:
            print(f"Found {len(initial_state)} newsflash items")
            print(f"First item: {initial_state[0]}")
        else:
            print("Failed to extract initial state")

        await browser.close()

asyncio.run(test_scrape())
```

### 3. 单条数据提取测试

测试JSON数据提取逻辑：

```python
from backend.services.message.sources.kr36 import Kr36Collector

collector = Kr36Collector({
    'id': 'test',
    'interval': 30,
    'mysql_table': 'kr36_messages',
    'chroma_collection': 'personal_agent_kr36',
    'config': {'url': 'https://www.36kr.com/newsflashes'}
})

test_item = {
    'itemId': '3499974612688005',
    'templateMaterial': {
        'widgetTitle': '测试标题',
        'widgetContent': '测试内容',
        'publishTime': 1759893497356,
        'sourceUrlRoute': 'https://example.com',
        'widgetImage': 'https://example.com/image.jpg',
        'statComment': 5,
        'hasRelevant': 1
    },
    'route': '/newsflashes/3499974612688005'
}

article = collector._extract_article_from_json(test_item, None)
print(f"Extracted article: {article}")
```

### 4. ChromaDB存储测试

测试向量存储功能：

```python
from backend.storage import get_chromadb_storage

storage = get_chromadb_storage()
storage.create_collection('kr36_test')

test_query = storage.query(
    collection_name='kr36_test',
    query_embeddings=[[0.1] * 768],
    n_results=5
)
print(f"Query results: {test_query}")
```

### 5. 完整采集流程测试

执行单次完整采集：

```bash
cd backend/services/message/sources/kr36; python -c "import asyncio; from collector import Kr36Collector; asyncio.run(Kr36Collector({'id': 'test', 'interval': 30, 'mysql_table': 'kr36_messages', 'chroma_collection': 'personal_agent_kr36', 'config': {'url': 'https://www.36kr.com/newsflashes'}})._collect_once())"
```

### 6. 数据验证

检查采集的数据：

```python
from backend.database.connection import create_session
from backend.database import Kr36Message

with create_session() as db:
    latest_messages = db.query(Kr36Message).order_by(
        Kr36Message.published_at.desc()
    ).limit(5).all()

    for msg in latest_messages:
        print(f"ID: {msg.item_id}")
        print(f"Title: {msg.title}")
        print(f"Published: {msg.published_at}")
        print(f"Content: {msg.content[:100]}...")
        print("-" * 80)
```

## 常见问题

### 1. Playwright浏览器启动失败

确保已安装Playwright浏览器：

```bash
playwright install chromium
```

### 2. 数据库连接失败

检查backend/database/connection.py中的数据库配置是否正确。

### 3. ChromaDB collection已存在

采集器会自动创建collection，如果已存在则会复用。如需重建：

```python
from backend.storage import get_chromadb_storage

storage = get_chromadb_storage()
storage.client.delete_collection('kr36')
storage.create_collection('kr36')
```

### 4. 网站结构变化导致爬取失败

36氪可能会更新页面结构或window.initialState的数据格式。此时需要：
1. 使用浏览器开发者工具检查新的数据结构
2. 更新collector.py中的数据提取逻辑
3. 调整_extract_article_from_json方法中的字段映射

## 技术特点

### 数据提取策略

36氪快讯页面使用服务端渲染（SSR），快讯数据直接嵌入在HTML中的window.initialState对象中。采集器通过以下步骤提取数据：

1. Playwright加载页面
2. 执行JavaScript获取window.initialState.newsflashCatalogData.data.newsflashList.data.itemList
3. 遍历itemList中的每个item
4. 从templateMaterial对象中提取字段

这种方式相比DOM解析更稳定，因为：
- 不受CSS样式变化影响
- 数据结构相对稳定
- 包含完整的原始数据

### 去重策略

使用36氪的item_id作为唯一标识：
- 在数据库中item_id字段设置为UNIQUE索引
- 每次采集前查询最新的item_id
- 遇到相同item_id立即停止采集
- 插入时利用UNIQUE约束自动去重

### 时间处理

36氪使用Unix时间戳（毫秒）表示发布时间：
- publishTime字段存储毫秒级时间戳
- 采集器将其除以1000转换为秒
- 使用datetime.fromtimestamp()转换为datetime对象
- 所有datetime操作使用datetime.now()而非datetime.utcnow()

### 增量采集

采集器支持增量采集，避免重复处理：
1. 从MySQL查询最新的item_id
2. 爬取时遇到该item_id立即停止
3. 只处理和存储新快讯
4. 定时循环执行，持续获取最新内容

## 性能优化

- 并发存储：MySQL和ChromaDB存储并发执行
- 浏览器复用：浏览器实例在采集器生命周期内保持运行
- 增量采集：只处理新数据，减少数据库操作
- 索引优化：在item_id、published_at等字段上建立索引

## 数据字段映射

| 36氪字段 | 数据库字段 | 类型 | 说明 |
|---------|----------|------|------|
| itemId | item_id | String(50) | 唯一标识符 |
| templateMaterial.widgetTitle | title | String(500) | 标题 |
| templateMaterial.widgetContent | content | Text | 内容 |
| templateMaterial.publishTime | published_at | DateTime | 发布时间（毫秒时间戳转换） |
| route | kr_route | String(500) | 36氪页面路由 |
| templateMaterial.sourceUrlRoute | source_url | String(500) | 原文链接 |
| templateMaterial.widgetImage | image_url | String(1000) | 图片链接 |
| templateMaterial.statComment | comment_count | Integer | 评论数 |
| templateMaterial.hasRelevant | has_relevant | Boolean | 是否有相关内容 |

## 维护建议

1. 定期监控采集日志，及时发现异常
2. 检查数据库中的数据量增长，确保采集正常
3. 观察36氪网站的结构变化，必要时更新采集逻辑
4. 定期清理过期数据，控制数据库大小
5. 监控ChromaDB的性能和存储空间
