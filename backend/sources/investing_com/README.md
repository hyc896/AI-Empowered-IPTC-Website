# Investing.com RSS采集器

## 消息源信息

- **名称**: Investing.com General News
- **类型**: news（财经快讯）
- **RSS URL**: https://www.investing.com/rss/news.rss
- **更新频率**: 30秒（interval: 30）
- **cron调度**: */1 * * * *（每分钟执行）

## 技术实现

### 依赖库

本采集器使用feedparser库解析RSS/XML格式订阅源，需要安装：

```bash
pip install feedparser
```

### 架构特点

1. **无需Playwright**：直接通过HTTP请求获取RSS，无需浏览器自动化
2. **RSS解析**：使用feedparser自动处理RSS 2.0/Atom格式
3. **字段映射**：
   - `guid` → `external_id`（RSS唯一标识符）
   - `link` → `url`（用于去重的UNIQUE字段）
   - `description` → `content` 和 `summary`
   - `pubDate` → `published_at`
4. **去重策略**：url字段UNIQUE约束 + 遇到latest_url立即停止
5. **字段增强**：调用FieldEnricherService自动添加region、industry_tags、ai_tag

### 数据流程

```
RSS订阅源
  ↓
feedparser解析
  ↓
字段映射（guid→external_id, link→url）
  ↓
去重检查（遇到latest_url停止）
  ↓
字段增强（region/industry_tags/ai_tag）
  ↓
并发存储（MySQL + ChromaDB）
```

## 数据库表结构

**表名**: `mp_investing_com_messages`

**核心字段**（遵循2025统一标准）：
- `id`: UUID主键
- `source_id`: 外键→mp_message_sources
- `external_id`: RSS guid（外部唯一标识）
- `title`: 标题
- `content`: 正文内容（description）
- `summary`: 摘要（同content）
- `provider`: 固定为"Investing.com"
- `published_at`: 发布时间（pubDate）
- `crawled_at`: 抓取时间
- `url`: 原文链接（**UNIQUE约束，用于去重**）

**新增字段**（2025年强制要求）：
- `region`: 地区（中文格式，如"美国"、"全球"等）
- `industry_tags`: 行业标签（逗号分隔，最多3个）
- `ai_tag`: AI分类标签（AI科研信息/AI产业信息/AI治理信息）

**索引**：
- `idx_source_id`, `idx_published_at`, `idx_crawled_at`
- `idx_source_published`（联合索引）
- `idx_url`（UNIQUE）, `idx_external_id`, `idx_category`, `idx_region`

## 测试验证

运行测试脚本：

```bash
cd d:\TechWork\message_platform
python test_investing_collector.py
```

测试内容：
1. 加载消息源配置
2. 初始化采集器
3. 执行单次采集
4. 验证数据库存储

预期结果：
- 首次运行：采集~10条记录
- 第二次运行：仅采集新增记录（去重验证）
- 数据库存储：所有字段正确映射，COMMENT无乱码

## 生产部署

### 注册消息源

```bash
mysql -h localhost -P 3306 -u root -p123456 --default-character-set=utf8mb4 message_platform < backend/sources/investing_com/register.sql
```

### 验证注册

```sql
-- 检查消息源
SELECT id, name, display_name, category, is_active
FROM mp_message_sources
WHERE name='investing_com_news';

-- 检查表结构
SHOW CREATE TABLE mp_investing_com_messages;

-- 检查COMMENT字段是否正确
SHOW CREATE TABLE mp_investing_com_messages\G
```

### 启动采集器

采集器会通过AutoCollector自动启动，无需手动操作。

## 常见问题

### Q: feedparser未安装

**错误**：`ImportError: feedparser库未安装`

**解决方法**：
```bash
pip install feedparser
```

### Q: 字段增强失败（region/industry_tags为None）

**原因**：独立脚本测试时LLM客户端未初始化

**说明**：这是正常现象。正式服务启动后（main.py），GlobalLLMManager会自动初始化，字段增强功能会正常工作。

### Q: COMMENT字段乱码

**原因**：SQL脚本执行时CMD编码不是UTF-8

**解决方法**：
- 使用`chcp 65001`切换CMD编码
- 或使用`mysql -e "source script.sql"`方式执行

### Q: 外键约束错误

**原因**：source_id字段字符集与mp_message_sources.id不匹配

**解决方法**：确保source_id使用`COLLATE utf8mb4_unicode_ci`

## 采集频率建议

- **测试环境**: interval=60（每分钟）
- **生产环境**: interval=30（30秒）
- **RSS特点**: Investing.com RSS更新频繁，建议30-60秒采集一次

## 数据示例

```json
{
  "title": "Samsung, Hyundai announce domestic investments after US-South Korea trade deal",
  "url": "https://www.investing.com/news/stock-market-news/samsung-hyundai-announce-domestic-investments-after-ussouth-korea-trade-deal-4361018",
  "external_id": "https://www.investing.com/news/stock-market-news/samsung-hyundai-announce-domestic-investments-after-ussouth-korea-trade-deal-4361018",
  "content": "Samsung and Hyundai announce major domestic investment plans following trade agreement.",
  "provider": "Investing.com",
  "published_at": "2025-11-16 15:54:25",
  "region": "韩国",
  "industry_tags": "汽车制造,半导体/芯片",
  "ai_tag": null
}
```

## 参照标准

本采集器实现参考了同花顺采集器（backend/sources/tonghuashun/collector.py）的架构模式：
- 预增强模式（字段增强在数据库事务外执行）
- 去重检查（遇到latest_id立即停止）
- 并发存储（MySQL和ChromaDB并行写入）
- 优雅降级（依赖库不可用时仅警告不中断）
