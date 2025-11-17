# TechCrunch Tech News Collector

TechCrunch全球科技新闻与深度报道采集器

## 概述

TechCrunch是全球领先的科技新闻媒体，本采集器支持从9个不同分类同时采集最新科技新闻和深度报道。

## 采集分类

本采集器监控以下9个TechCrunch分类：

1. **AI (Artificial Intelligence)** - 人工智能
   - URL: https://techcrunch.com/category/artificial-intelligence/

2. **Security** - 网络安全
   - URL: https://techcrunch.com/category/security/

3. **Robotics** - 机器人
   - URL: https://techcrunch.com/category/robotics/

4. **Cloud Computing** - 云计算
   - URL: https://techcrunch.com/tag/cloud-computing/

5. **Hardware** - 硬件
   - URL: https://techcrunch.com/category/hardware/

6. **Enterprise** - 企业服务
   - URL: https://techcrunch.com/category/enterprise/

7. **Government & Policy** - 政府与政策
   - URL: https://techcrunch.com/category/government-policy/

8. **Privacy** - 隐私
   - URL: https://techcrunch.com/category/privacy/

9. **Biotech & Health** - 生物技术与健康
   - URL: https://techcrunch.com/category/biotech-health/

## 数据库结构

### 表名
`mp_techcrunch_messages`

### 核心字段（遵循2025统一标准）
- `id`: UUID主键
- `source_id`: 外键到mp_message_sources
- `external_id`: 从URL提取的文章唯一标识
- `title`: 文章标题
- `content`: 完整文章内容（从详情页提取）
- `summary`: 中文摘要（自动翻译）
- `provider`: 作者
- `published_at`: 发布时间
- `crawled_at`: 抓取时间
- `url`: 原文链接（用于去重）

### 扩展字段
- `region`: 地区（通过FieldEnricherService自动识别）
- `industry_tags`: 行业标签（通过FieldEnricherService自动生成，逗号分隔）
- `ai_tag`: AI分类标签（AI科研信息/AI产业信息/AI治理信息）
- `category`: TechCrunch分类（AI/Security/Robotics等）
- `language`: 语言（默认en）

## 采集策略

### 内容提取策略
- **模式**: Advanced（List + Detail Pages）
- **原因**: TechCrunch列表页仅显示标题和元数据，无摘要或内容预览
- **流程**:
  1. 抓取分类列表页，获取文章元数据（标题、URL、作者、发布时间）
  2. 访问每篇文章的详情页，提取完整内容
  3. 自动翻译成中文摘要

### 去重机制
- **唯一标识**: URL字段（UNIQUE约束）
- **停止条件**: 遇到数据库中已存在的URL立即停止当前分类的采集

### 加载机制
- **类型**: Load More按钮 + 分页链接
- **处理**: 当前版本仅抓取首页内容（每页约36篇文章）
- **未来优化**: 可扩展支持点击"Load More"或遍历分页链接

## 采集频率

- **默认间隔**: 2小时（7200秒）
- **Cron表达式**: `0 */2 * * *`（每2小时的整点执行）
- **建议**: TechCrunch更新频繁，2小时间隔可确保及时获取最新内容

## 配置说明

### 消息源配置（mp_message_sources.config字段）
```json
{
  "interval": 7200,
  "mysql_table": "mp_techcrunch_messages",
  "chroma_collection": "techcrunch_messages",
  "collector_module": "backend.sources.techcrunch.collector",
  "collector_class": "TechCrunchCollector",
  "region": "GLOBAL",
  "language": "en",
  "categories": [
    "AI",
    "Security",
    "Robotics",
    "Cloud Computing",
    "Hardware",
    "Enterprise",
    "Government & Policy",
    "Privacy",
    "Biotech & Health"
  ]
}
```

## 使用方法

### 1. 注册消息源
```bash
mysql -h localhost -P 3306 -u root -p123456 --default-character-set=utf8mb4 message_platform -e "source D:/TechWork/message_platform/backend/sources/techcrunch/register.sql"
```

### 2. 测试采集器
```bash
python test_techcrunch_collector.py
```

### 3. 查看采集结果
```sql
-- 查看总记录数
SELECT COUNT(*) FROM mp_techcrunch_messages;

-- 按分类统计
SELECT category, COUNT(*) as count
FROM mp_techcrunch_messages
GROUP BY category
ORDER BY count DESC;

-- 查看最新文章
SELECT title, category, provider, published_at, url
FROM mp_techcrunch_messages
ORDER BY published_at DESC
LIMIT 10;
```

## 技术实现

### 关键技术点
1. **Playwright**: 用于JavaScript渲染页面的抓取
2. **预翻译模式**: 在数据库session外完成翻译，避免连接池阻塞
3. **字段增强**: 使用FieldEnricherService自动识别地区和行业标签
4. **三阶段分离**: Scraping（采集）→ Processing（处理）→ Storing（存储）

### 参照标准
本采集器遵循Golden Example: `backend/sources/cigi/collector.py`的架构设计

### 选择器（CSS Selectors）
- 文章列表: `.loop-card--post-type-post`
- 文章标题: `h2 a, h3 a`
- 作者: `.loop-card__meta a, .loop-card__author`
- 发布时间: `time[datetime]`
- 文章内容: `.entry-content, .wp-block-post-content`

## 常见问题

### Q: 为什么只采集首页内容？
A: 当前版本优先保证数据质量和系统稳定性。每次采集约获取36篇文章，2小时间隔足以覆盖大部分新文章。

### Q: 如何添加新的分类？
A: 编辑`collector.py`中的`CATEGORIES`字典，添加新的分类名称和URL即可。

### Q: summary字段是如何生成的？
A: 使用Translator服务将英文content全文翻译成中文，无需手动截断。

### Q: region和industry_tags字段如何生成？
A: 采集器在存储前调用FieldEnricherService.enrich_fields()，根据标题和内容自动识别地区和行业标签。

## 未来改进方向

1. **分页支持**: 实现"Load More"按钮点击和多页遍历
2. **增量更新**: 优化已存文章的检测逻辑，减少重复访问
3. **并发优化**: 详情页访问支持并发请求，提高采集速度
4. **分类动态配置**: 支持从数据库配置中读取监控的分类列表

## 监控与日志

### 关键日志
- `【TechCrunch】采集器已启动` - 采集器成功启动
- `【TechCrunch】开始采集分类: {category}` - 开始采集某个分类
- `【{category}】找到 X 篇文章` - 列表页解析结果
- `【{category}】采集到 X 篇新文章` - 当前分类新增文章数
- `【TechCrunch】本次采集共获取 X 篇新文章` - 总计新增文章数

### 错误处理
- 网络请求失败: 自动重试3次，延迟5秒
- 详情页访问失败: 使用标题作为content，继续采集后续文章
- 翻译失败: 返回降级文本（截断原文 + 降级标记）

## 维护记录

- **2025-11-17**: 初始版本，支持9个分类采集
