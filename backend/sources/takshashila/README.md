# Takshashila Institution 采集器

## 机构简介

**Takshashila Institution**（塔克沙希拉研究所）是印度领先的独立公共政策智库，专注于技术政策、地缘政治、国防与安全、治理等领域的研究。

- **国家/地区**: 印度（India）
- **官网**: https://takshashila.org.in/
- **重要性**: 中
- **更新频率**: 日
- **相关性**: 中

## 数据库架构

### 消息表: `mp_takshashila_messages`

遵循2025统一字段标准：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | VARCHAR(36) | UUID主键 |
| source_id | VARCHAR(36) | 外键到mp_message_sources |
| external_id | VARCHAR(200) | URL文件名（如20251103-LEPF-Policy-Brief） |
| title | VARCHAR(500) | 标题 |
| content | TEXT | 正文内容（从详情页提取） |
| summary | TEXT | 中文摘要（翻译后） |
| provider | VARCHAR(500) | 作者列表（逗号分隔） |
| published_at | DATETIME | 发布时间 |
| crawled_at | DATETIME | 抓取时间 |
| url | VARCHAR(500) | 原文链接（UNIQUE，用于去重） |
| region | VARCHAR(50) | 地区（IN=India） |
| language | VARCHAR(10) | 语言（en） |
| publication_type | VARCHAR(100) | 出版物类型 |
| categories | JSON | 分类标签列表 |
| metadata | JSON | 其他元数据 |

### 出版物类型

Takshashila Institution发布多种类型的研究出版物：

- **Policy Brief** - 政策简报
- **Discussion Document** - 讨论文件
- **Working Paper** - 工作论文
- **Journal Article** - 期刊文章
- **Blue Paper** - 蓝皮书
- **Issue Brief** - 问题简报

## 采集器实现

### 网页结构分析

**列表页**: https://takshashila.org.in/pages/publications/

- **加载机制**: JavaScript动态渲染（List.js库）
- **分页**: 每页显示10条记录
- **列表容器**: `#listing-publications-list .list`
- **列表项**: `<li>` 元素

**HTML结构**:

```html
<div id="listing-publications-list">
  <ul class="list">
    <li>
      <h3>
        <a href="../../content/publications/20251103-LEPF-Policy-Brief.html">
          <span class="listing-title">[标题]</span>
        </a>
      </h3>
      <p class="listing-categories">
        <span class="listing-category">Geopolitics</span>
        <span class="listing-category">Public Policy</span>
      </p>
      <p class="listing-date">Nov 3, 2025</p>
      <p class="listing-author">Megha Nambiar, Kartik Singh</p>
    </li>
  </ul>
</div>
```

**详情页**: 使用Quarto生成的HTML页面

- **内容容器**: `#quarto-content`, `article`, `.entry-content`
- **段落选择器**: `#quarto-content p, article p, .entry-content p`
- **PDF下载链接**: 部分文章提供PDF下载

### 数据字段映射

| 网页字段 | 数据库字段 | 说明 |
|----------|-----------|------|
| 文件名（URL） | external_id | 如20251103-LEPF-Policy-Brief |
| listing-title | title | 文章标题 |
| quarto-content正文 | content | 完整文章内容 |
| （content翻译） | summary | 中文摘要 |
| listing-author | provider | 作者（逗号分隔） |
| listing-date | published_at | 发布时间 |
| href | url | 原文链接 |
| listing-category | categories | 分类标签（JSON数组） |
| 第一个category | publication_type | 出版物类型 |

### 采集流程

1. **获取最新记录**: 查询数据库最新的URL
2. **爬取列表页**: 使用Playwright加载JavaScript渲染的列表
3. **停止条件**: 遇到已存在URL时立即停止
4. **访问详情页**: 获取完整文章内容（8000-9000字）
5. **翻译摘要**: 使用Translator翻译成中文
6. **并发存储**: MySQL + ChromaDB

### 去重策略

- **主键**: URL字段（UNIQUE约束）
- **检查时机**: 列表页遍历时检查URL是否已存在
- **IntegrityError**: 数据库级别的最终防护

### 翻译策略

遵循智能翻译工作流（Stage 2.5）：

1. **语言检测**: 自动识别为英文内容
2. **全文翻译**: 调用`translator.translate()`，**不截断**
3. **降级策略**: 翻译失败时返回截断原文 + `[AI翻译暂不可用]`

## 当前状态

### 已完成

- [x] 数据库表结构设计和创建
- [x] ORM实体定义（TakshashilaMessage）
- [x] 消息源注册（UUID: e2fd6831-bf1c-11f0-8cb6-00ff40160484）
- [x] 采集器代码实现
- [x] 列表页提取逻辑
- [x] 详情页内容提取
- [x] 翻译功能集成
- [x] ChromaDB向量化支持

### 已知问题

**网站访问限制**:

测试采集时遇到`net::ERR_EMPTY_RESPONSE`错误，可能原因：

1. **地理位置限制**: 印度网站可能限制中国大陆IP访问
2. **反爬虫机制**: 检测到Playwright自动化工具
3. **网站临时不可用**: 服务器故障或维护

**WebFetch成功但Playwright失败**: 说明网站可访问，但对自动化工具有特殊限制。

### 解决方案

**短期方案**:

1. 使用代理服务器（印度/美国IP）
2. 增强反检测措施（stealth插件）
3. 降低请求频率，增加随机延迟

**中期方案**:

1. 监控网站访问策略变化
2. 联系Takshashila Institution申请API访问权限
3. 使用RSS Feed（如果有）

**长期方案**:

1. 建立海外采集服务器
2. 使用商业代理池服务

## 使用指南

### 数据库注册

```bash
mysql -h localhost -P 3306 -u root -p123456 --default-character-set=utf8mb4 message_platform -e "source D:/TechWork/message_platform/backend/sources/takshashila/register.sql"
```

### 测试采集器

```bash
cd D:\TechWork\message_platform
python backend/sources/takshashila/test_collector.py
```

### 查看采集结果

```sql
SELECT
    id, title, provider, published_at, publication_type, url
FROM mp_takshashila_messages
ORDER BY published_at DESC
LIMIT 10;
```

## 文件结构

```
backend/sources/takshashila/
├── __init__.py              # 模块导出
├── collector.py             # 采集器主逻辑
├── register.sql             # 数据库注册脚本
├── test_collector.py        # 测试脚本
├── debug_page.py            # 调试脚本
└── README.md                # 本文档
```

## 注意事项

1. **网站访问**: 当前从中国大陆访问受限，建议使用代理
2. **JavaScript渲染**: 必须等待List.js完成加载（5秒延迟）
3. **详情页请求**: 添加1-2秒延迟避免触发限流
4. **翻译资源**: 长文档（8000+字）翻译耗时较长
5. **ChromaDB初始化**: 测试时可能显示未初始化警告，不影响MySQL存储

## 维护记录

- **2025-11-12**: 初始实现，完成数据库注册和采集器开发
- **已知问题**: 网站访问受地理位置限制，需要代理解决
