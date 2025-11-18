# 证券时报采集器 (Securities Times Collector)

## 概述

证券时报采集器用于采集中国证券时报网站的财经新闻内容。

**数据源**：https://www.stcn.com

**消息源ID**：cd1acf31-c48b-11f0-b75e-08bfb82ee112

## 架构特点

### 三阶段处理架构

遵循VentureBeat最佳实践：

1. **Scraping阶段**：网页抓取和原始数据提取
   - 滚动加载列表页
   - 提取文章标题、URL、摘要、发布时间等
   - 智能去重：遇到已存在URL立即停止

2. **Processing阶段**：字段增强（在数据库会话外）
   - 访问详情页获取完整content
   - 调用FieldEnricherService增强字段（region、industry_tags、ai_tag）
   - 异步并发处理，避免阻塞数据库连接

3. **Storing阶段**：数据库存储
   - MySQL存储（使用ORM）
   - ChromaDB向量化存储
   - 去重保护（UNIQUE约束）

## 字段映射

### 标准字段（2025统一规范）

| 网页字段 | 数据库字段 | 说明 |
|---------|-----------|------|
| URL中的数字ID | external_id | 如3500937 |
| 文章标题 | title | 必填 |
| 详情页正文 | content | 必填，从详情页提取 |
| 列表页摘要 | summary | 优先使用 |
| 作者byline | provider | 从"作者："后提取 |
| 发布时间 | published_at | YYYY-MM-DD HH:MM |
| 完整URL | url | 用于去重（UNIQUE） |

### 增强字段（自动生成）

- **region**：地区（中文，如"中国/广东省/深圳市"）
- **industry_tags**：行业标签（逗号分隔，最多3个）
- **ai_tag**：AI分类（AI科研信息/AI产业信息/AI治理信息）

## 配置说明

```json
{
  "interval": 86400,
  "mysql_table": "mp_securities_times_messages",
  "chroma_collection": "securities_times",
  "collector_module": "backend.sources.securities_times.collector",
  "categories": ["yw"],
  "region": "CN",
  "language": "zh"
}
```

## 数据库结构

**表名**：`mp_securities_times_messages`

**关键索引**：
- `idx_url`（UNIQUE）：用于去重
- `idx_source_id`：外键索引
- `idx_published_at`：时间查询优化
- `idx_source_published`：联合索引

**外键约束**：
- `source_id` → `mp_message_sources.id` (ON DELETE CASCADE)

## 使用方法

### 1. 注册到数据库

```powershell
Get-Content backend/sources/securities_times/register.sql -Encoding UTF8 | mysql -h localhost -P 3306 -u root -p123456 --default-character-set=utf8mb4 message_platform
```

### 2. 测试采集器

```bash
python -m backend.sources.securities_times.test_collector
```

### 3. 验证数据

```sql
-- 查看采集的消息数量
SELECT COUNT(*) FROM mp_securities_times_messages;

-- 查看最新10条消息
SELECT title, published_at, region, industry_tags
FROM mp_securities_times_messages
ORDER BY published_at DESC
LIMIT 10;

-- 验证去重机制
SELECT url, COUNT(*) as count
FROM mp_securities_times_messages
GROUP BY url
HAVING count > 1;
```

## 去重策略

### 启动时查询最新记录
```python
latest_url = await self._get_latest_stored_url()
```

### 采集前检查
遇到已存在URL立即停止：
```python
if latest_url and article_url == latest_url:
    logger.info("遇到已存储URL，停止采集")
    return articles_list
```

### 数据库二次防护
UNIQUE约束自动拒绝重复URL：
```python
except IntegrityError as e:
    if "Duplicate entry" in str(e):
        logger.debug(f"Duplicate URL: {url}")
```

## 监控指标

- **采集数量**：每次采集的新文章数
- **存储成功率**：成功存储/总采集数
- **去重命中率**：遇到重复URL停止的频率
- **详情页成功率**：详情页访问成功/总文章数

## 常见问题

### 1. 详情页访问失败

**症状**：日志显示"详情页所有重试均失败"

**解决方案**：
- 检查网络连接
- 确认网站未更改反爬虫策略
- 增加重试延迟时间

### 2. 字段增强失败

**症状**：region、industry_tags为NULL

**解决方案**：
- 确认FieldEnricherService可用
- 检查LLM服务状态
- 查看详细错误日志

### 3. 中文乱码

**症状**：COMMENT字段显示为"????"

**解决方案**：
- 已使用utf8mb4_unicode_ci编码
- 终端显示问题不影响实际存储
- 使用MySQL客户端查询可正常显示

## 技术要点

### 异步编程最佳实践
- ✅ 字段增强在数据库会话外执行
- ✅ 避免在事务内调用外部API
- ✅ 批量处理控制并发数

### Fail Fast原则
- ✅ 启动时验证配置
- ✅ 单条失败不影响批次
- ✅ 详细记录错误日志

### 关注点分离
- ✅ Scraping：网页抓取
- ✅ Processing：数据处理
- ✅ Storing：数据库存储

## 参照标准

- **最佳实践**：backend/sources/venturebeat/collector.py
- **增量优化**：backend/sources/nikkei_asia/collector.py
- **统一字段标准**：backend/database/entities.py（SecuritiesTimesMessage）

## 更新日志

### 2025-11-18
- ✅ 创建采集器
- ✅ 实现三阶段架构
- ✅ 添加字段增强功能
- ✅ 注册到message_platform
