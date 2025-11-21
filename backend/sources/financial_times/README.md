# Financial Times Technology 采集器

## 消息源信息

- **名称**: Financial Times Technology
- **英文名**: Financial Times Technology
- **类型**: RSS Feed
- **URL**: https://www.ft.com/technology?format=rss
- **地区**: 英国
- **语言**: 英语
- **更新频率**: 每小时检查一次（Cron: `0 */1 * * *`）
- **数据量**: 每次约25条记录

## 数据源特点

1. **权威性**: 英国金融时报是全球顶级财经媒体，科技频道聚焦商业科技趋势
2. **付费墙**: FT是付费墙媒体，RSS Feed仅包含文章摘要（45-120字符）
3. **内容质量**: 高质量深度报道，聚焦科技产业、AI投资、企业战略等话题
4. **更新频率**: 每天约10-15篇新文章

## 架构设计

### 采集模式

**纯RSS模式**（不需要访问详情页）：
- RSS Feed已提供足够信息（标题、摘要、URL、发布时间）
- 摘要长度较短但信息密度高
- 符合2025统一字段标准

### 三阶段架构

1. **Scraping阶段**: 解析RSS Feed，提取原始数据
2. **Processing阶段**:
   - 翻译摘要（英文→中文）
   - 字段增强（region, industry_tags, ai_tag）
   - **在数据库会话外完成**，避免阻塞连接池
3. **Storing阶段**:
   - MySQL存储（mp_financial_times_messages表）
   - ChromaDB向量化（financial_times_tech集合）

### 去重策略

**滑动验证去重**：
- 启动时查询最新URL
- 采集前逐条检查
- 遇到已存在URL立即停止
- 数据库UNIQUE约束作为二次防护

## 字段映射

### RSS字段 → 数据库字段

| RSS字段 | 数据库字段 | 说明 |
|---------|-----------|------|
| id/guid | external_id | 外部唯一标识 |
| title | title | 标题 |
| description/summary | content | 正文内容（摘要） |
| description/summary | summary | 中文摘要（翻译后） |
| author | provider | 作者 |
| link | url | 原文链接（用于去重） |
| published | published_at | 发布时间 |
| - | crawled_at | 抓取时间（自动） |
| - | region | 地区（字段增强服务） |
| - | industry_tags | 行业标签（字段增强服务） |
| - | ai_tag | AI分类标签（字段增强服务） |

## 数据库表结构

```sql
CREATE TABLE mp_financial_times_messages (
    id VARCHAR(36) PRIMARY KEY COMMENT '消息ID（UUID）',
    source_id VARCHAR(36) NOT NULL COMMENT '来源ID',
    external_id VARCHAR(200) COMMENT '外部唯一标识（RSS的guid字段）',
    title VARCHAR(500) NOT NULL COMMENT '标题（RSS的title字段）',
    content TEXT NOT NULL COMMENT '正文内容（RSS的description字段）',
    summary TEXT COMMENT '中文摘要（翻译后）',
    provider VARCHAR(500) COMMENT '作者（RSS的author字段）',
    published_at DATETIME COMMENT '发布时间（RSS的pubDate字段）',
    crawled_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '抓取时间',
    url VARCHAR(500) NOT NULL UNIQUE COMMENT '原文链接（RSS的link字段，用于去重）',

    region VARCHAR(200) COMMENT '地区（中文格式，从文章内容提取）',
    industry_tags TEXT COMMENT '行业标签（逗号分隔，最多3个，涉及AI必须包含"人工智能"标签）',
    ai_tag VARCHAR(50) COMMENT 'AI分类标签（AI科研信息/AI产业信息/AI治理信息）',

    category VARCHAR(100) COMMENT '文章分类（RSS的category字段）',
    language VARCHAR(10) DEFAULT 'en' COMMENT '语言',
    media_content VARCHAR(500) COMMENT '媒体内容URL（RSS的media:content字段）',
    tags JSON COMMENT '标签列表（JSON数组）',
    metadata JSON COMMENT '其他元数据（JSON对象）',

    FOREIGN KEY (source_id) REFERENCES mp_message_sources(id) ON DELETE CASCADE,
    INDEX idx_source_id (source_id),
    INDEX idx_published_at (published_at),
    INDEX idx_crawled_at (crawled_at),
    INDEX idx_source_published (source_id, published_at),
    INDEX idx_url (url),
    INDEX idx_external_id (external_id)
);
```

## 测试结果

### RSS Feed测试

```
Feed标题: Technology
Feed链接: https://www.ft.com/stream/e58e66fe-7cc6-4382-b781-1161bae8b905
HTTP状态: 200
条目数量: 25条
```

### 首次运行测试

```
[成功] 获取到 25 条记录
[成功存储] 5条记录
数据库总记录数: 5
```

### 去重机制测试（第二次运行）

```
最新URL: https://www.ft.com/content/8514e0a3-8ff5-4454-878e-b31e0a86adcc
[停止] 遇到已存在URL
[成功存储] 0条记录
数据库总记录数: 5（未增加）
```

**结论**: 去重机制正常工作，第二次运行未产生重复数据。

### 样本数据

| 标题 | 内容长度 | 发布时间 | 地区 |
|------|---------|---------|------|
| Axes of Evil: McKinsey squares the circle | 45字符 | 2025-11-18 17:34:07 | 英国 |
| Fund managers warn AI investment boom has gone too far | 111字符 | 2025-11-18 17:12:37 | 英国 |
| Microsoft and Nvidia to invest up to $15bn in OpenAI rival Anthropic | 112字符 | 2025-11-18 16:44:27 | 英国 |

## 注册状态

- **消息源ID**: `8d4bdf4e-c4a2-11f0-b75e-08bfb82ee112`
- **状态**: `is_active=1`（已启用）
- **Category**: `news`（资讯）
- **MySQL表**: `mp_financial_times_messages`
- **ChromaDB集合**: `financial_times_tech`
- **采集器模块**: `backend.sources.financial_times.collector`

## 运行方式

### 手动测试

```bash
# RSS Feed测试
python backend/sources/financial_times/test_rss.py

# 简单功能测试（不依赖LLM）
python backend/sources/financial_times/simple_test.py

# 完整采集器测试（需要LLM服务）
python backend/sources/financial_times/test_collector.py
```

### 自动采集

采集器已注册到AutoCollector服务，每小时自动运行一次。

## 技术要点

### 遵循的设计原则

1. **Fail Fast原则**: 配置验证、启动检查
2. **三阶段分离**: Scraping → Processing → Storing
3. **异步IO外置**: 翻译和字段增强在数据库会话外执行
4. **滑动验证去重**: 遇到已存在记录立即停止
5. **统一字段标准**: 完全遵循2025年统一字段规范

### 参照标准

- **Golden Example**: backend/sources/venturebeat/collector.py（预处理模式）
- **RSS采集**: backend/sources/wired/collector.py, backend/sources/cnbc/collector.py

## 注意事项

1. **付费墙限制**: RSS仅包含摘要，不含全文
2. **内容长度**: 摘要通常45-120字符，信息密度高
3. **作者信息**: 部分文章无作者字段（显示为N/A）
4. **翻译降级**: 翻译失败时自动使用原文
5. **字段增强**: 失败时使用默认值（region='英国'）

## 更新日志

- **2025-11-18**: 初始版本创建
  - 完成RSS采集器开发
  - ORM实体定义（FinancialTimesMessage）
  - 数据库表创建和注册
  - 测试验证通过
