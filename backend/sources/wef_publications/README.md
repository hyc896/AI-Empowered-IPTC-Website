# World Economic Forum (WEF) AI Publications Collector

世界经济论坛AI出版物采集器

## 概述

本采集器用于抓取World Economic Forum（世界经济论坛）关于人工智能的出版物，包括白皮书、研究报告、政策指南等。

## 数据源信息

- **来源名称**: World Economic Forum AI Publications
- **URL**: https://www.weforum.org/publications/
- **类型**: 新闻资讯（news）
- **地区**: GLOBAL
- **语言**: en（英文）
- **更新频率**: 每天凌晨2点（cron: 0 2 * * *）

## 数据字段

### 核心字段
- `id`: UUID主键
- `source_id`: 消息源ID
- `external_id`: 从URL提取的slug（如"artificial-intelligence-for-efficiency-sustainability-and-inclusivity-in-tradetech"）
- `title`: 出版物标题
- `content`: 出版物正文内容（从详情页提取）
- `summary`: 中文摘要（AI翻译）
- `provider`: 合作方（如"Ministry of Economy of UAE"）
- `published_at`: 发布时间
- `crawled_at`: 抓取时间
- `url`: 出版物链接（用于去重）

### 扩展字段
- `region`: 地区（GLOBAL）
- `category`: 出版物分类（如"EMERGING TECHNOLOGIES"）
- `language`: 语言（en）
- `metadata`: 其他元数据（JSON）

## 采集策略

### 内容完整性
- **列表页**: 仅包含标题、分类、发布日期
- **详情页**: 包含完整的摘要和正文内容
- **采集模式**: Advanced模式 - 列表页 + 详情页

### AI过滤
由于WEF出版物涵盖多个主题，采集器通过标题关键词过滤AI相关内容：
- artificial intelligence
- ai
- machine learning
- intelligent

### 去重机制
- 使用`url`字段进行唯一性约束
- 采集前查询最新存储的URL，遇到相同URL立即停止

### 翻译策略
- 外文内容自动翻译成中文
- 优先翻译网页提取的summary
- 翻译失败时降级为截断原文（添加[AI翻译暂不可用]标记）

## 使用方法

### 首次采集（手动运行）

```bash
cd D:\TechWork\message_platform
python backend/scripts/initial_collect_wef_publications.py
```

### 日常自动采集

采集器已注册到CollectorService，会自动按计划执行（每天凌晨2点）。

启动message_platform服务即可：
```bash
cd D:\TechWork\message_platform\backend
python main.py
```

### 验证数据

```sql
-- 查看采集的出版物数量
SELECT COUNT(*) FROM mp_wef_publication_messages;

-- 查看最新的10条出版物
SELECT title, published_at, category, url
FROM mp_wef_publication_messages
ORDER BY published_at DESC
LIMIT 10;

-- 查看分类统计
SELECT category, COUNT(*) as count
FROM mp_wef_publication_messages
GROUP BY category
ORDER BY count DESC;
```

## 技术细节

### 依赖项
- Playwright（浏览器自动化）
- SQLAlchemy（数据库ORM）
- ChromaDB（向量存储）
- LLM服务（翻译和向量化）

### 错误处理
- 网络请求：3次重试，每次延迟5秒
- 详情页访问失败：继续处理下一条，不中断整体流程
- 翻译失败：自动降级为截断原文
- 数据库重复：捕获IntegrityError，记录为DEBUG

### 性能优化
- 详情页访问间隔2秒，避免请求过快
- MySQL和ChromaDB并发存储
- 批量处理，单条失败不影响其他数据

## 注意事项

1. **网站访问限制**: WEF网站可能有访问频率限制，初次采集时注意观察日志
2. **历史数据量**: WEF有大量历史出版物，初始采集可能需要较长时间
3. **内容质量**: 部分出版物可能只有标题而无正文，content会fallback到title
4. **分类过滤**: 当前仅通过标题关键词过滤AI内容，可能遗漏部分相关出版物

## 故障排查

### 采集器未启动
检查消息源是否激活：
```sql
SELECT is_active FROM mp_message_sources WHERE name='wef_publications';
```

### 无法访问WEF网站
- 检查网络连接
- 确认网站是否可访问：https://www.weforum.org/publications/
- 查看Playwright浏览器日志

### 翻译失败率高
- 检查LLM服务是否正常
- 查看backend/llm/translator.py的日志
- 使用批量重新翻译脚本（如需创建）

### 数据重复
- 检查url字段的UNIQUE约束
- 查看IntegrityError日志
- 手动清理重复数据：
```sql
DELETE t1 FROM mp_wef_publication_messages t1
INNER JOIN mp_wef_publication_messages t2
WHERE t1.id > t2.id AND t1.url = t2.url;
```

## 维护任务

### 定期检查
- 每周检查采集日志，确认无异常
- 每月统计数据增长情况
- 定期验证翻译质量

### 数据清理
- 旧数据归档（超过1年的出版物）
- 失效链接清理
- ChromaDB向量同步验证

## 开发者信息

- 创建日期: 2025-11-11
- 维护者: Claude Code Agent
- 项目: message_platform
- 版本: 1.0.0
