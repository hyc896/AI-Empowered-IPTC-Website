# The Guardian AI与科技新闻采集器

## 简介

The Guardian采集器用于采集英国卫报(The Guardian)的AI与科技相关新闻。

## 数据源

### RSS订阅源

1. **AI栏目**：https://www.theguardian.com/technology/artificialintelligenceai/rss
   - 专注于人工智能领域的深度报道
   - 包含AI伦理、AI政策、AI应用等内容

2. **技术栏目**：https://www.theguardian.com/uk/technology/rss
   - 广泛的科技新闻覆盖
   - 包含大型科技公司、技术创新等内容

3. **数据安全栏目**：https://www.theguardian.com/technology/data-computer-security/rss
   - 网络安全、隐私保护相关报道
   - 数据治理和安全政策新闻

## 技术特点

### 架构设计

- **RSS解析**：使用feedparser库解析RSS订阅源
- **无需浏览器**：直接HTTP请求，效率更高
- **多源并发**：同时采集3个RSS源，并发处理提高效率
- **预处理模式**：翻译和字段增强在数据库会话外完成，避免阻塞

### 数据处理

- **去重策略**：基于URL字段的UNIQUE约束
- **增量采集**：按category查询最新URL，遇到已存在记录立即停止
- **翻译策略**：英文→中文全文翻译（The Guardian是纯英文源）
- **字段增强**：自动添加region（地区）、industry_tags（行业标签）、ai_tag（AI分类标签）

### 数据字段

#### 核心必备字段（遵循2025统一标准）

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | VARCHAR(36) | UUID主键 |
| source_id | VARCHAR(36) | 外键→mp_message_sources |
| external_id | VARCHAR(200) | RSS guid |
| title | VARCHAR(500) | 标题 |
| content | TEXT | 正文内容（RSS description或summary） |
| summary | TEXT | 摘要（中文翻译） |
| provider | VARCHAR(500) | 作者（多个用逗号分隔） |
| published_at | DATETIME | 发布时间 |
| crawled_at | DATETIME | 抓取时间 |
| url | VARCHAR(500) | 原文链接（用于去重） |

#### 新增必备字段（2025年强制要求）

| 字段名 | 类型 | 说明 |
|--------|------|------|
| region | VARCHAR(200) | 地区（中文格式，如"英国"、"全球"等） |
| industry_tags | TEXT | 行业标签（逗号分隔，最多3个） |
| ai_tag | VARCHAR(50) | AI分类标签（AI科研信息/AI产业信息/AI治理信息） |

#### 扩展字段

| 字段名 | 类型 | 说明 |
|--------|------|------|
| category | VARCHAR(100) | 分类（AI/Technology/Security等） |
| language | VARCHAR(10) | 语言（en） |

## 使用方式

### 通过主服务运行

采集器已注册到message_platform主服务，会自动按照配置的时间表执行：

- **采集频率**：每小时一次（0 */1 * * *）
- **自动启动**：message_platform启动时自动加载

### 手动运行测试

```bash
# 进入项目根目录
cd D:/TechWork/message_platform

# 运行测试脚本
python backend/sources/guardian/test_collector.py
```

**注意**：手动测试需要先启动message_platform主服务以初始化LLM客户端，否则翻译和字段增强功能将不可用。

## 配置说明

### 数据库配置

```json
{
  "interval": 3600,
  "mysql_table": "mp_guardian_messages",
  "chroma_collection": "guardian_news",
  "collector_module": "backend.sources.guardian.collector.GuardianCollector",
  "region": "UK",
  "language": "en",
  "rss_feeds": [
    {
      "url": "https://www.theguardian.com/technology/artificialintelligenceai/rss",
      "category": "AI"
    },
    {
      "url": "https://www.theguardian.com/uk/technology/rss",
      "category": "Technology"
    },
    {
      "url": "https://www.theguardian.com/technology/data-computer-security/rss",
      "category": "Security"
    }
  ]
}
```

### 添加新的RSS源

如需添加其他The Guardian的RSS源：

1. 修改数据库配置中的`rss_feeds`数组
2. 添加新的RSS源URL和对应的category
3. 重启message_platform服务

## 依赖项

- **feedparser**：RSS/XML解析库
- **sqlalchemy**：ORM框架
- **llm服务**：翻译和字段增强（通过get_translator和get_field_enricher获取）

## 故障排查

### 常见问题

1. **采集失败**：检查RSS源URL是否可访问
2. **翻译失败**：确认LLM服务已正确配置和初始化
3. **字段增强失败**：确认FieldEnricherService已启动
4. **ChromaDB错误**：确认ChromaDB服务已启动并正确配置

### 日志位置

- **主服务日志**：logs/platform.log
- **采集日志标识**：【Guardian】

### 检查采集状态

```sql
-- 查看采集到的消息数量
SELECT COUNT(*) FROM mp_guardian_messages;

-- 查看最近采集的消息
SELECT title, category, published_at, crawled_at
FROM mp_guardian_messages
ORDER BY crawled_at DESC
LIMIT 10;

-- 按分类统计
SELECT category, COUNT(*) as count
FROM mp_guardian_messages
GROUP BY category;

-- 查看消息源状态
SELECT name, is_active, last_crawled_at
FROM mp_message_sources
WHERE name = 'guardian';
```

## 代码结构

```
backend/sources/guardian/
├── __init__.py          # 模块导出
├── collector.py         # 采集器核心逻辑
├── register.sql         # 数据库注册脚本
├── test_collector.py    # 测试脚本
└── README.md            # 本文档
```

## 维护记录

- **2025-11-18**：初始版本创建，支持3个RSS源的并发采集

## 相关资源

- [The Guardian官网](https://www.theguardian.com)
- [RSS Feeds说明](https://www.theguardian.com/help/feeds)
- [feedparser文档](https://pythonhosted.org/feedparser/)
