# FARI - AI for the Common Good Institute 采集器

## 机构信息

- **机构名称**: FARI - AI for the Common Good Institute
- **国家/地区**: 比利时 (Belgium, BE)
- **类别**: 智库 (think_tank)
- **官网**: https://www.fari.brussels/
- **使命**: AI for the Common Good（AI公益）

## 采集目标

FARI采集器采集两个主要内容板块：

### 1. 新闻与媒体 (News & Media)
- **URL**: https://www.fari.brussels/news-and-media/news
- **内容类型**: 机构新闻、研究发布、项目更新、政策评论
- **更新频率**: 约48条新闻（分4页），持续更新
- **内容示例**:
  - "Elevating AI Oversight: The Crucial Role of Regulatory..."
  - "Ana Pop Stefanija: A citizen jury for socially acceptable AI..."
  - "FARI's contributions to shaping AI's Future at the European AI Week 2025"

### 2. 研究出版物 (Publications)
- **URL**: https://www.fari.brussels/research-and-innovation/publications
- **内容类型**: 学术报告、期刊论文、会议论文、学位论文
- **更新频率**: 约36条出版物（分6页），最新至2025年7-9月
- **出版物类型**:
  - Report（研究报告）
  - Journal Article（期刊论文）
  - Conference Proceeding（会议论文）
  - Thesis（学位论文）
- **内容示例**:
  - "From Blueprint to Reality: Implementing AI Regulatory Sandboxes under the AI Act"
  - "Redefining Global AI Governance Together"
  - "Engineering the Law-Machine Learning Translation Problem"

## 采集策略

### 内容完整性分析
- **列表页**: 无日期显示，只有标题和缩略图
- **详情页**: 包含完整的发布日期、作者、正文、PDF链接等
- **采集模式**: 列表页 + 详情页（Advanced Mode）

### 采集流程
1. 并发爬取新闻列表页和出版物列表页
2. 从列表页提取所有项目的URL和标题
3. 查询数据库获取最新URL，遇到已存在记录立即停止
4. 逐个访问详情页获取：
   - 发布日期（从Schema.org metadata提取）
   - 作者信息（从byline或Schema.org提取）
   - 完整正文（从article/main标签提取段落）
   - PDF下载链接（出版物）
   - 主题标签（出版物）
5. 翻译外文摘要为中文
6. 存储到MySQL和ChromaDB

### 去重策略
- **唯一ID字段**: `url`（UNIQUE约束）
- **去重检查时机**: 列表页爬取时，遇到最新URL立即停止
- **降级保护**: IntegrityError捕获，防止重复插入

### 翻译策略
- **语言**: 英语 (en)
- **需要翻译**: 是（外文消息源）
- **翻译内容**: Summary字段（摘要）
- **翻译方式**: 使用全局Translator实例，全文翻译（不限制长度）
- **降级策略**: 翻译失败时返回截断原文 + "[AI翻译暂不可用]"标记

## 数据库表结构

### 表名: `mp_fari_messages`

#### 核心必备字段（遵循2025统一标准）
| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | VARCHAR(36) | PRIMARY KEY | UUID主键 |
| source_id | VARCHAR(36) | FOREIGN KEY, NOT NULL | 消息源ID |
| external_id | VARCHAR(200) | INDEX | URL路径slug |
| title | VARCHAR(500) | NOT NULL | 标题 |
| content | TEXT | NOT NULL | 正文内容（从详情页提取） |
| summary | TEXT | NULL | 中文摘要（翻译后） |
| provider | VARCHAR(500) | NULL | 作者（逗号分隔） |
| published_at | DATETIME | INDEX | 发布时间 |
| crawled_at | DATETIME | NOT NULL, INDEX | 抓取时间 |
| url | VARCHAR(500) | UNIQUE, NOT NULL | 原文链接（去重） |

#### 扩展字段
| 字段名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| region | VARCHAR(50) | 'BE' | 地区（比利时） |
| content_type | VARCHAR(100) | NULL | 内容类型（News/Report/Journal Article等） |
| language | VARCHAR(10) | 'en' | 语言 |
| tags | JSON | NULL | 主题标签（如Sustainable AI、Data & Robotics） |
| pdf_url | VARCHAR(500) | NULL | PDF下载链接（出版物） |
| metadata | JSON | NULL | 其他元数据 |

#### 索引
- `idx_source_id`: source_id
- `idx_published_at`: published_at
- `idx_crawled_at`: crawled_at
- `idx_source_published`: (source_id, published_at) 联合索引
- `idx_url`: url (UNIQUE)
- `idx_external_id`: external_id
- `idx_content_type`: content_type

## 配置说明

### 消息源配置 (mp_message_sources.config)
```json
{
  "mysql_table": "mp_fari_messages",
  "chroma_collection": "fari",
  "collector_module": "backend.sources.fari.collector",
  "collector_class": "FARICollector",
  "news_url": "https://www.fari.brussels/news-and-media/news",
  "publications_url": "https://www.fari.brussels/research-and-innovation/publications",
  "region": "BE",
  "language": "en",
  "interval": 86400
}
```

### 采集间隔
- **默认**: 86400秒（24小时）
- **Cron表达式**: `0 0 2 * * ?`（每天凌晨2点）

## 技术细节

### DOM选择器（基于WebFetch分析）

#### 新闻列表页
- **列表项**: `a[href*='news-and-media-article']`
- **特点**: 网格布局，动态CSS类名（.css-xxxxx）
- **提取**: URL、标题（从链接文本或父元素）

#### 出版物列表页
- **列表项**: `a[href*='/publication/']`
- **特点**: 卡片布局，带类型标签
- **提取**: URL、标题、类型标签

#### 详情页通用结构
- **日期**: `meta[property="article:published_time"]` 或 `time[datetime]`
- **作者**: `[class*="author"], [class*="byline"], [rel="author"]`
- **正文**: `article p, .content-wrapper p, .entry-content p, main p`
- **PDF**: `a[href*=".pdf"], a:has-text("Download")`
- **标签**: `[class*="tag"], [class*="topic"], .chip`

### 错误处理

#### 网络请求
- **最大重试**: 3次
- **重试间隔**: 5秒
- **超时设置**:
  - 列表页: 60秒
  - 详情页: 30秒

#### 详情页失败降级
- 详情页访问失败时，使用列表页的标题作为content
- 日期设置为当前时间
- 作者为None

#### 数据库异常
- `IntegrityError (Duplicate entry)`: 捕获并记录DEBUG日志
- 其他错误: 记录ERROR日志并跳过该条记录

## 注意事项与限制

### 1. 网站反爬虫措施
- FARI网站在Puppeteer MCP工具访问时返回ERR_ABORTED错误
- 可能有反爬虫检测或需要特定的User-Agent
- 采集器使用标准Chrome User-Agent和多项反检测措施

### 2. 动态CSS类名
- 网站使用`.css-xxxxx`样式，可能在更新时变化
- 采集器优先使用语义化标签（article、main）作为选择器
- 建议定期检查选择器有效性

### 3. 分页机制
- 当前版本只采集第一页（约12条新闻/6条出版物）
- 分页通过"Page X of Y"提示识别
- 后续可增强：循环点击"Next"按钮加载更多页

### 4. 多语言支持
- 网站支持英语、荷兰语、法语
- 当前采集器只采集英语版本（默认语言）
- URL路径中无语言标识，直接访问默认为英语

### 5. 内容长度
- 部分新闻正文较短（<500字）
- 学术报告正文可能很长（>5000字）
- Summary翻译不限制长度，信任Translator内部处理

## 文件清单

```
backend/sources/fari/
├── __init__.py           # 模块导出
├── collector.py          # 采集器主代码（约850行）
├── register.sql          # 数据库注册脚本
├── test_collector.py     # 测试脚本
└── README.md            # 本文档
```

## 测试与验证

### 1. 手动测试
```bash
cd backend/sources/fari
python test_collector.py
```

### 2. 检查数据库
```sql
-- 查看采集记录数量
SELECT content_type, COUNT(*) as count
FROM mp_fari_messages
GROUP BY content_type;

-- 查看最新记录
SELECT title, published_at, content_type, url
FROM mp_fari_messages
ORDER BY published_at DESC
LIMIT 10;

-- 验证翻译质量
SELECT title, LEFT(summary, 100) as summary_preview
FROM mp_fari_messages
WHERE summary IS NOT NULL
LIMIT 5;
```

### 3. 验证去重
运行两次测试脚本，第二次应该显示：
```
【FARI】所有内容已存在，无新数据
```

## 集成到AutoCollector

采集器已完全遵循项目规范，自动集成到AutoCollector系统：

1. ✅ ORM类注册到Registry
2. ✅ 消息源配置包含`collector_module`字段
3. ✅ 启动验证自动检查配置一致性
4. ✅ PersonalAgent自动同步消息源工具描述

无需手动修改任何集成代码。

## 已知问题与改进方向

### 短期改进（可选）
1. **分页支持**: 实现多页采集，突破第一页限制
2. **选择器优化**: 添加更多备用选择器，提高鲁棒性
3. **日期解析增强**: 支持更多日期格式（如"JUL 2025"）

### 长期改进（可选）
1. **增量采集优化**: 记录last_crawled_at，仅采集新内容
2. **PDF内容提取**: 下载PDF并提取全文（用于学术报告）
3. **多语言采集**: 支持采集荷兰语和法语版本

## 许可与维护

- **创建日期**: 2025-11-12
- **版本**: 1.0.0
- **维护状态**: 活跃
- **兼容性**: Python 3.8+, Playwright, SQLAlchemy 2.0+
