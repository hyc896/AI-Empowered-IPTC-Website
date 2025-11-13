# AISI (AI Security Institute) 采集器

## 消息源信息

- **机构名称**: AI Security Institute (AISI)
- **机构性质**: 英国政府AI安全研究机构
- **国家/地区**: 英国 (UK)
- **官方网站**: https://www.aisi.gov.uk/
- **采集目标**: https://www.aisi.gov.uk/research
- **内容类型**: 智库报告、技术博客、AI安全研究文章

## 采集器特性

### 核心功能

1. **内容采集**
   - 采集AISI研究页面的所有研究报告和博客文章
   - 自动提取标题、分类标签、发布时间、摘要等元数据
   - 访问详情页获取完整文章内容（4000-5000字符）

2. **智能去重**
   - 基于URL的UNIQUE约束去重
   - 查询数据库最新记录，遇到已存在URL立即停止采集
   - 避免重复采集，节省资源

3. **自动翻译**
   - 外文内容（英文）自动翻译成中文摘要
   - 使用预翻译模式（在数据库session外执行翻译）
   - 翻译失败时自动降级（返回截断原文+降级标记）

4. **多存储支持**
   - MySQL存储：结构化数据持久化
   - ChromaDB向量化：支持语义检索

### 技术架构

- **采集框架**: Playwright (异步爬虫)
- **加载机制**: 单页加载（无分页，一次性加载所有内容）
- **详情页访问**: 需要（列表页仅提供摘要，约150字）
- **翻译服务**: backend.llm.translator
- **数据库**: MySQL 8.0 + utf8mb4_unicode_ci
- **向量库**: ChromaDB

## 数据库表结构

### 表名
`mp_aisi_messages`

### 核心字段（遵循2025统一标准）

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | VARCHAR(36) | PRIMARY KEY | UUID主键 |
| source_id | VARCHAR(36) | FOREIGN KEY, NOT NULL | 外键→mp_message_sources |
| external_id | VARCHAR(200) | INDEX | URL slug（如"mapping-the-limitations-of-current-ai-systems"） |
| title | VARCHAR(500) | NOT NULL | 标题 |
| content | TEXT | NOT NULL | 完整文章内容（从详情页提取） |
| summary | TEXT | NULL | 中文摘要（翻译后） |
| provider | VARCHAR(500) | NULL | 作者（AISI文章通常无作者字段） |
| published_at | DATETIME | INDEX | 发布时间 |
| crawled_at | DATETIME | NOT NULL, INDEX | 抓取时间 |
| url | VARCHAR(500) | UNIQUE, NOT NULL | 原文链接（用于去重） |

### 扩展字段

| 字段名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| region | VARCHAR(50) | UK | 地区（UK=United Kingdom） |
| content_type | VARCHAR(100) | NULL | 内容类型（Research/Blog/Technical Report） |
| language | VARCHAR(10) | en | 语言（英文） |
| categories | JSON | NULL | 分类标签（如Safeguards, Control, Alignment等） |
| metadata | JSON | NULL | 其他元数据 |

### 索引设计

- PRIMARY KEY: id
- UNIQUE INDEX: url
- INDEX: source_id, published_at, crawled_at, external_id, content_type
- COMPOSITE INDEX: (source_id, published_at)

## 部署与使用

### 1. 数据库注册

已通过`register.sql`脚本完成注册：

```bash
mysql -h localhost -P 3306 -u root -p123456 --default-character-set=utf8mb4 message_platform -e "source backend/sources/aisi/register.sql"
```

**注册结果**：
- 表名: mp_aisi_messages
- 消息源ID: 1de0143c-bf25-11f0-8cb6-00ff40160484
- 状态: is_active=1
- ChromaDB集合: aisi_research

### 2. 采集器配置

**消息源配置** (mp_message_sources表)：

```json
{
  "url": "https://www.aisi.gov.uk/research",
  "region": "UK",
  "language": "en",
  "interval": 86400,
  "mysql_table": "mp_aisi_messages",
  "chroma_collection": "aisi_research",
  "collector_module": "backend.sources.aisi.collector.AISICollector"
}
```

**调度策略**：
- Cron表达式: `0 2 * * *` (每天凌晨2点执行)
- 采集间隔: 86400秒（24小时）

### 3. 手动运行采集器

```python
import asyncio
from backend.sources.aisi.collector import AISICollector

# 配置字典
config = {
    'id': '1de0143c-bf25-11f0-8cb6-00ff40160484',
    'interval': 86400,
    'mysql_table': 'mp_aisi_messages',
    'chroma_collection': 'aisi_research',
    'config': {
        'url': 'https://www.aisi.gov.uk/research',
        'region': 'UK',
        'language': 'en'
    }
}

# 创建并运行采集器
collector = AISICollector(config)
asyncio.run(collector.run())
```

### 4. 验证采集结果

```sql
-- 查询总记录数
SELECT COUNT(*) FROM mp_aisi_messages;

-- 查询最新10条记录
SELECT title, published_at, content_type, url
FROM mp_aisi_messages
ORDER BY published_at DESC
LIMIT 10;

-- 查询不同内容类型的分布
SELECT content_type, COUNT(*) as count
FROM mp_aisi_messages
GROUP BY content_type;
```

## 特殊考虑事项

### 网站访问限制

AISI网站（www.aisi.gov.uk）可能存在访问限制：

1. **访问被阻止问题**
   - Puppeteer直接访问可能返回`net::ERR_ABORTED`错误
   - 可能需要特定的User-Agent或Cookie

2. **解决方案**
   - 采集器已配置标准浏览器User-Agent
   - 如仍无法访问，可能需要：
     - 使用代理服务器
     - 添加浏览器Cookie模拟真实用户
     - 调整请求频率和间隔

3. **当前状态**
   - 采集器代码结构完整，通过静态验证
   - 数据库表和配置注册成功
   - 实际运行效果取决于网站访问权限

### 内容提取策略

- **列表页**: 提供标题、分类、日期、摘要（约150字）
- **详情页**: 包含完整文章内容（4000-5000字符）
- **提取逻辑**:
  - 使用语义标签 `article p`, `main p`, `.content-wrapper p`
  - 过滤非正文内容（分享按钮、导航链接、短作者信息）
  - 内容拼接使用双换行符分隔段落

### 翻译策略

- **触发条件**: language='en'（外文）
- **翻译上下文**: "AISI AI安全研究文章摘要"
- **完整文本翻译**: 不截断，传递完整摘要给translator
- **降级处理**: 翻译失败时返回前500字+降级标记

## 监控与维护

### 日志关键字

```
【AISI】采集器初始化成功
【AISI】开始访问 N 篇文章的详情页
【AISI】采集到 N 篇新文章
【AISI】所有文章已存在，无新数据
```

### 常见问题排查

1. **采集无数据**
   - 检查网站是否可访问（curl测试）
   - 查看日志中的错误信息
   - 验证选择器是否仍然有效

2. **翻译失败**
   - 检查LLM服务是否正常
   - 查看translator日志中的错误
   - 数据库summary字段包含"[AI翻译暂不可用]"

3. **重复数据**
   - UNIQUE约束应自动防止
   - 检查url字段是否正确提取
   - 验证去重逻辑是否执行

## 参照标准

本采集器严格遵循CIGI采集器的Golden Example架构：

- ✓ 预翻译模式（在数据库session外执行翻译）
- ✓ 三阶段分离（采集/处理/存储）
- ✓ 完整文本传递给translator（不截断）
- ✓ 智能去重（查询最新URL，遇到立即停止）
- ✓ 详情页访问延迟（1.5秒防反爬虫）

## 版本历史

- **v1.0.0** (2025-11-12)
  - 初始版本
  - 实现基础采集功能
  - 支持自动翻译
  - 完成数据库注册
