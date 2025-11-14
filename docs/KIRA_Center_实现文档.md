# KIRA Center 消息源实现文档

## 消息源信息

- **机构名称**: KIRA Center (Center for AI Risks & Impacts)
- **国家/地区**: 德国 (Germany)
- **官方网站**: https://kira.eu/
- **采集目标**: AI政策研究博客与报告
- **消息源ID**: dcf8f0b2-bf24-11f0-8cb6-00ff40160484
- **类别**: think_tank (智库)

## 架构设计

### 数据库表结构

**表名**: `mp_kira_messages`

#### 核心字段（遵循2025统一标准）

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | VARCHAR(36) | PRIMARY KEY | 消息ID（UUID） |
| source_id | VARCHAR(36) | FOREIGN KEY, NOT NULL | 来源ID（关联mp_message_sources） |
| external_id | VARCHAR(200) | INDEX | 外部唯一标识（从URL路径提取slug） |
| title | VARCHAR(500) | NOT NULL | 标题 |
| content | TEXT | NOT NULL | 正文内容（从详情页提取完整内容） |
| summary | TEXT | NULL | 中文摘要（翻译后） |
| provider | VARCHAR(500) | NULL | 作者（多个用逗号分隔） |
| published_at | DATETIME | INDEX | 发布时间 |
| crawled_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 抓取时间 |
| url | VARCHAR(500) | UNIQUE, NOT NULL | 原文链接（用于去重） |

#### 扩展字段

| 字段名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| region | VARCHAR(50) | DE | 地区（DE=Germany） |
| content_type | VARCHAR(100) | NULL | 内容类型（Blog/Report/Policy Analysis） |
| language | VARCHAR(10) | en | 语言（en/de） |
| pdf_url | VARCHAR(500) | NULL | PDF报告下载链接 |
| metadata | JSON | NULL | 其他元数据 |

#### 索引设计

- PRIMARY KEY: id
- UNIQUE INDEX: url
- INDEX: source_id
- INDEX: published_at
- INDEX: crawled_at
- INDEX: (source_id, published_at) 联合索引
- INDEX: external_id
- INDEX: content_type
- FOREIGN KEY: source_id → mp_message_sources(id) ON DELETE CASCADE

### ORM实体类

**文件**: `backend/database/entities.py`

**类名**: `KIRAMessage`

```python
class KIRAMessage(Base):
    """KIRA Center（德国AI风险与影响研究中心）博客与报告表"""
    __tablename__ = "mp_kira_messages"

    # 核心必备字段
    id = Column(String(36), primary_key=True)
    source_id = Column(String(36), ForeignKey("mp_message_sources.id", ondelete="CASCADE"))
    external_id = Column(String(200))
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    summary = Column(Text)
    provider = Column(String(500))
    published_at = Column(DateTime)
    crawled_at = Column(DateTime, default=datetime.now, nullable=False)
    url = Column(String(500), unique=True, nullable=False)

    # 扩展字段
    region = Column(String(50), default="DE")
    content_type = Column(String(100))
    language = Column(String(10), default="en")
    pdf_url = Column(String(500))
    extra_metadata = Column("metadata", JSON)

    # 关系
    source = relationship("MessageSource", back_populates="kira_messages")
```

## 采集器实现

### 采集器架构

**目录结构**:
```
backend/sources/kira/
├── __init__.py
├── collector.py
└── register.sql
```

### 采集器类

**文件**: `backend/sources/kira/collector.py`

**类名**: `KIRACollector`

#### 主要方法

1. **__init__(config)**: 初始化采集器
   - 配置ChromaDB和LLM客户端
   - 设置采集间隔、URL等参数

2. **initialize()**: 初始化Playwright浏览器
   - 启动Chromium浏览器（headless模式）
   - 创建ChromaDB collection

3. **run()**: 主循环定时采集
   - 调用_collect_once()执行单次采集
   - 间隔时间：86400秒（24小时）

4. **_collect_once()**: 单次采集流程
   - 获取最新存储的URL
   - 爬取博客列表页
   - 过滤新文章
   - 访问详情页获取完整内容
   - 提取PDF链接（如果是报告）
   - 存储到MySQL和ChromaDB

5. **_scrape_articles_list(latest_url)**: 爬取文章列表
   - 使用Playwright访问博客页面
   - 提取文章元素：article.blog-item
   - 解析标题、作者、日期、摘要
   - 遇到latest_url立即停止

6. **_fetch_article_content(article_url)**: 获取完整内容
   - 访问详情页
   - 提取正文段落：.sqs-block-content p
   - 过滤非正文内容（share、subscribe等）
   - 拼接完整文本

7. **_extract_pdf_url(article_url)**: 提取PDF链接
   - 查找PDF下载链接：a[href$='.pdf']
   - 补全相对路径

8. **_generate_summary(summary, content)**: 生成中文摘要
   - 外文内容：调用translator全文翻译
   - 中文内容：直接返回或截断到1000字
   - 降级策略：翻译失败返回截断原文+标记

9. **_store_to_mysql(items, summaries)**: 存储到MySQL
   - 预翻译模式：先翻译再存储
   - 使用ORM插入记录
   - 处理IntegrityError（URL重复）

10. **_store_to_chroma(items, summaries)**: 存储到ChromaDB
    - 生成embedding向量
    - 使用URL作为chroma_id
    - upsert操作防止重复

### 去重策略

**唯一标识字段**: `url`

**去重机制**:
1. 数据库层：url字段设置UNIQUE约束
2. 采集层：查询最新存储的URL，遇到则停止采集
3. 存储层：IntegrityError捕获，记录重复日志

### 内容提取策略

**列表页提取**:
- 选择器：`article.blog-item, .blog-basic-grid article`
- 提取字段：标题、URL、日期、作者、摘要

**详情页提取**:
- 选择器：`.sqs-block-content p, article .entry-content p`
- 过滤规则：长度>20字符，排除share/subscribe等关键词
- 拼接方式：双换行符连接段落

**PDF链接提取**:
- 选择器：`a[href$='.pdf'], a[href*='/s/'][href*='.pdf']`
- 相对路径补全：https://kira.eu{pdf_url}

### 翻译策略

**语言检测**:
- 采样前200字符
- 中文字符占比>30%判定为中文

**翻译流程**:
1. 确定原始摘要来源：summary > content
2. 判断是否需要翻译：language='en' 且 非中文
3. 调用translator.translate()全文翻译（不限制长度）
4. 翻译上下文："KIRA Center AI政策研究文章"

**降级策略**:
- 翻译失败：返回原文前500字 + "[AI翻译暂不可用]"
- 无翻译器：返回原文（截断到1000字）

## 消息源配置

### 数据库配置

**表**: `mp_message_sources`

**配置记录**:
```json
{
  "id": "dcf8f0b2-bf24-11f0-8cb6-00ff40160484",
  "name": "kira",
  "adapter_name": "kira",
  "category": "think_tank",
  "display_name": "KIRA Center",
  "config": {
    "url": "https://kira.eu/blog",
    "region": "DE",
    "language": "en",
    "mysql_table": "mp_kira_messages",
    "chroma_collection": "kira",
    "interval": 86400,
    "collector_module": "backend.sources.kira.collector.KIRACollector"
  },
  "schedule": "0 2 * * *",
  "is_active": 1
}
```

### ChromaDB配置

**Collection名称**: `kira`

**向量化字段**: `title + summary`

**元数据字段**:
- source_id
- external_id
- published_at
- url
- title
- provider
- region
- content_type
- language

## 注册流程

### SQL注册脚本

**文件**: `backend/sources/kira/register.sql`

**执行命令**:
```bash
mysql -h localhost -P 3306 -u root -p123456 --default-character-set=utf8mb4 message_platform -e "source D:/TechWork/message_platform/backend/sources/kira/register.sql"
```

**注意事项**:
- 必须使用utf8mb4_unicode_ci字符集（与mp_message_sources一致）
- 外键约束：source_id → mp_message_sources(id) ON DELETE CASCADE
- COMMENT字段必须为中文，不能乱码

### 验证检查清单

- [x] mp_kira_messages表创建成功
- [x] 消息源记录注册成功（UUID: dcf8f0b2-bf24-11f0-8cb6-00ff40160484）
- [x] config.mysql_table = "mp_kira_messages"
- [x] config.chroma_collection = "kira"
- [x] is_active = 1
- [x] COMMENT字段显示正确中文（无乱码）
- [x] 外键约束创建成功
- [x] 所有索引创建成功

## 数据流程图

```
Playwright浏览器
    ↓
访问 https://kira.eu/blog
    ↓
提取文章列表 (article.blog-item)
    ↓
检查URL是否已存在 → 是 → 停止采集
    ↓ 否
访问详情页获取完整内容
    ↓
提取PDF链接（如果有）
    ↓
翻译摘要（外文→中文）
    ↓
并发存储
    ├→ MySQL (mp_kira_messages)
    └→ ChromaDB (kira collection)
```

## 关键特性

1. **智能停止采集**: 遇到已存在URL立即停止，避免重复爬取
2. **详情页内容提取**: 列表页仅提供摘要，必须访问详情页获取完整content
3. **PDF链接识别**: 自动识别并提取报告的PDF下载链接
4. **全文翻译**: 外文内容全文翻译成中文，不限制长度
5. **预翻译模式**: 在数据库会话外完成所有翻译，避免连接阻塞
6. **降级策略**: 翻译失败时返回截断原文+降级标记
7. **延迟访问**: 详情页访问间隔2秒，避免触发反爬虫

## 常见问题

### 1. 字符集不匹配错误

**错误**: `Referencing column 'source_id' and referenced column 'id' in foreign key constraint are incompatible`

**原因**: mp_message_sources表使用utf8mb4_unicode_ci，而新表使用utf8mb4_0900_ai_ci

**解决方案**: 所有字段显式指定`COLLATE utf8mb4_unicode_ci`

### 2. COMMENT字段乱码

**错误**: COMMENT显示"娑堟伅ID"而非"消息ID"

**原因**: Windows CMD默认GBK编码，SQL文件被错误读取

**解决方案**: 使用`mysql -e "source path/to/file.sql"`命令，由MySQL内部读取文件

### 3. 详情页内容提取失败

**错误**: content字段为空或很短

**原因**: Squarespace网站结构复杂，选择器不准确

**解决方案**: 使用多个备选选择器：`.sqs-block-content p, article .entry-content p, .blog-item-content-wrapper p`

### 4. 翻译超时或失败

**错误**: 大量记录summary包含"[AI翻译暂不可用]"

**原因**: LLM API超时、并发限制、网络问题

**解决方案**:
- 检查LLM客户端初始化状态
- 使用批量翻译脚本重新翻译失败记录
- 调整translator的timeout参数

## 监控指标

### 采集效率
- 单次采集耗时：约5-10分钟（取决于新文章数量）
- 详情页访问延迟：2秒/篇
- 翻译耗时：3-5秒/篇

### 数据质量
- URL去重率：应接近0%（正常运行）
- 翻译成功率：应>95%
- 完整内容获取率：应>90%

### 异常告警
- 连续3次采集无新数据：检查网站结构变化
- 翻译失败率>20%：检查LLM服务状态
- 详情页访问失败率>50%：检查反爬虫机制

## 维护建议

1. **定期检查网站结构**: KIRA使用Squarespace，可能更新模板
2. **监控翻译质量**: 定期抽查summary字段，确保翻译准确
3. **关注反爬虫机制**: 如遇限流，增加延迟时间
4. **清理历史降级数据**: 定期重新翻译失败记录
5. **备份PDF链接**: PDF链接可能失效，建议下载存档

## 相关文件

- 实体类定义: `backend/database/entities.py`
- 采集器实现: `backend/sources/kira/collector.py`
- SQL注册脚本: `backend/sources/kira/register.sql`
- 项目配置: `CLAUDE.md`
- 数据库连接: `backend/database/connection.py`
- ChromaDB存储: `backend/storage/chromadb_storage.py`
- LLM翻译器: `backend/llm/translator.py`
