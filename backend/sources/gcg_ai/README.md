# Global Center on AI Governance (GCG) 采集器

## 消息源信息

- **机构名称**: Global Center on AI Governance (GCG)
- **URL**: https://www.globalcenter.ai/research
- **国家/地区**: 南非/非洲
- **内容类型**: AI治理政策研究、报告、分析文章
- **更新频率**: 月度
- **语言**: 英文
- **相关性**: 高（AI治理、政策制定、非洲视角）

## 数据库表结构

表名：`mp_gcg_ai_messages`

### 核心字段
- `id`: UUID主键
- `source_id`: 外键到mp_message_sources
- `external_id`: 从URL提取的slug（如"toward-an-african-agenda-for-ai-safety"）
- `title`: 文章标题
- `content`: 从详情页提取的简介内容
- `summary`: 中文翻译后的摘要
- `provider`: 作者（多个用逗号分隔）
- `published_at`: 发布时间
- `crawled_at`: 抓取时间
- `url`: 原文链接（用于去重）

### 扩展字段
- `region`: 地区（默认"ZA"=South Africa/Africa）
- `category`: 出版物类型（Policy Brief/Report/Article/Analysis/Toolkit等）
- `language`: 语言（默认"en"）
- `tags`: 标签列表（JSON数组）
- `pdf_url`: PDF下载链接
- `metadata`: 其他元数据（JSON对象）

## 采集策略

### 内容完整性策略

**列表页 + 详情页模式**

1. **列表页**：https://www.globalcenter.ai/research
   - 提取：标题、URL、日期、类型、标签
   - 内容：仅有简要信息

2. **详情页**：每篇文章的独立页面
   - 提取：完整的文章简介（约150-200字）
   - 注意：完整内容在PDF中，详情页只是landing page

### 智能持续加载

采集器使用统一的持续加载逻辑：

1. **启动时查询**：获取数据库中最新文章的URL
2. **持续加载**：从列表页开始加载，直到遇到已存在URL
3. **停止条件**：
   - 遇到数据库中已存在的记录
   - 连续三次操作未发现新内容
   - 页面提示已到达末尾
   - 达到安全上限（1000条记录）

### 去重机制

- **主键去重**：url字段设置为UNIQUE约束
- **采集前过滤**：查询最新URL，遇到已存在记录立即停止
- **数据库层防护**：IntegrityError捕获，重复URL跳过

### 翻译策略

- **判断依据**：language='en'，自动触发翻译
- **翻译范围**：全文翻译summary字段（不截断）
- **降级策略**：翻译失败时返回截断原文 + "[AI翻译暂不可用]"
- **预翻译模式**：在数据库session外完成所有翻译，避免连接阻塞

## 采集器配置

```json
{
  "url": "https://www.globalcenter.ai/research",
  "mysql_table": "mp_gcg_ai_messages",
  "chroma_collection": "gcg_ai_research",
  "interval": 604800,
  "region": "ZA",
  "language": "en",
  "collector_module": "backend.sources.gcg_ai.collector",
  "collector_class": "GCGAICollector"
}
```

## 已知问题

### Puppeteer访问限制

该网站可能有反爬虫防护机制，Puppeteer直接访问时可能遇到：
- `ERR_ABORTED` 错误
- 页面加载超时
- 需要JavaScript渲染

**解决方案**：
1. 增加重试机制（已实现，最多3次重试）
2. 设置User-Agent和其他HTTP头（已实现）
3. 等待页面完全加载（networkidle状态）
4. 如持续失败，可考虑使用API或RSS feed（如果有）

### HTML结构不确定性

由于无法直接访问页面分析HTML，采集器实现了多种备用选择器：
- `article`标签
- `[class*="publication"]`、`[class*="research"]`等class选择器
- 备用方案：提取所有`/research/`路径的链接

**实际部署时可能需要调整选择器**

## 测试说明

### 手动测试

```bash
cd D:\TechWork\message_platform
python backend/sources/gcg_ai/test_collector.py
```

### 预期行为

第一次运行：
- 采集到约50篇文章（截至2025年11月）
- 每篇文章访问详情页提取简介
- 外文summary自动翻译成中文

第二次运行：
- 遇到最新URL立即停止
- 数据库记录数不变（去重生效）

### 常见问题排查

1. **采集数量为0**
   - 检查网站是否可访问
   - 查看日志中的选择器匹配结果
   - 可能需要调整选择器

2. **翻译失败**
   - 检查LLM服务是否可用
   - 查看是否有"[AI翻译暂不可用]"标记
   - 可使用批量翻译脚本重新翻译

3. **重复记录**
   - 检查url字段是否正确设置
   - 查看IntegrityError日志
   - 确认数据库UNIQUE约束生效

## 数据样本

### 示例记录

```json
{
  "external_id": "toward-an-african-agenda-for-ai-safety",
  "title": "Toward an African Agenda for AI Safety",
  "content": "Traditional AI safety discussions often overlook Africa's unique context. This policy brief examines...",
  "summary": "传统的AI安全讨论往往忽视非洲的独特背景。本政策简报审查了...",
  "provider": "Samuel Segun, Rachel Adams, Ana Florido, Leah Junck",
  "published_at": "2025-09-02",
  "url": "https://www.globalcenter.ai/research/toward-an-african-agenda-for-ai-safety",
  "region": "ZA",
  "category": "Policy Brief",
  "language": "en",
  "tags": ["AI Safety", "Peace and Security"],
  "pdf_url": null
}
```

## 维护说明

### 定期检查事项

1. **网站结构变化**：每季度检查一次HTML结构
2. **翻译质量**：抽查10-20条记录的summary字段
3. **去重效果**：监控数据库是否有重复URL
4. **采集频率**：根据网站更新频率调整interval

### 更新选择器

如果网站结构变化，需要更新`collector.py`中的选择器：
- `_scrape_articles_list()`方法中的容器选择器
- `_extract_article_from_container()`方法中的字段选择器
- `_fetch_article_content()`方法中的内容选择器

## 参照标准

本采集器实现遵循CIGI采集器的设计模式（Golden Example）：
- 预翻译模式（session外完成翻译）
- 列表页+详情页的两阶段采集
- 智能持续加载和去重机制
- 全文翻译策略（不限制长度）
