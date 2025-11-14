# OBIA (Observatório Brasileiro de Inteligência Artificial) 采集器

巴西AI观测站研究出版物采集器

## 消息源信息

- **机构名称**: Brazilian AI Observatory (Observatório Brasileiro de Inteligência Artificial, OBIA)
- **URL**: https://obia.nic.br/s/publicacoes
- **国家/地区**: 巴西 (BR)
- **语言**: 葡萄牙语 (pt)
- **信息类型**: 研究出版物、报告
- **更新频率**: 月度

## 内容特点

### 出版物类型
1. **PANORAMA SETORIAL DA INTERNET** - 互联网行业全景系列
   - 聚焦AI对不同领域的影响
   - 主题包括：AI与公平正义、AI与健康、AI与教育、AI与工作等

2. **PESQUISAS TIC** - TIC研究系列
   - TIC Empresas (企业数字化调查)
   - TIC Governo Eletrônico (电子政务调查)
   - TIC Saúde (医疗卫生数字化调查)
   - TIC Educação (教育数字化调查)

### 数据字段

采集到的每条记录包含以下字段：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | UUID | 消息ID |
| source_id | UUID | 消息源ID（关联mp_message_sources） |
| external_id | varchar(200) | 外部唯一标识（从PDF URL提取data-guid） |
| title | varchar(500) | 标题 |
| content | text | 正文内容（描述信息） |
| summary | text | 摘要（中文翻译） |
| provider | varchar(500) | 作者列表（多个用逗号分隔） |
| published_at | datetime | 发布时间（从PDF URL中的时间戳提取） |
| crawled_at | datetime | 抓取时间 |
| url | varchar(500) | 原文链接（PDF直链，用于去重） |
| region | varchar(50) | 地区（BR=Brazil） |
| category | varchar(100) | 分类（PANORAMA/PESQUISAS TIC等） |
| language | varchar(10) | 语言（pt=葡萄牙语） |
| pdf_url | varchar(500) | PDF下载链接 |
| series | varchar(100) | 系列名称 |

## 反爬虫保护情况

**重要提示**: OBIA网站具有强大的反爬虫保护机制：

1. **Puppeteer被阻止**: 访问时返回 `net::ERR_ABORTED`
2. **requests被阻止**: SSL握手连接被强制重置 (`ConnectionResetError`)
3. **WebFetch可用**: 使用Claude的WebFetch工具可以成功获取内容

### 解决方案

采集器已实现，但由于反爬虫限制，需要以下任一方式运行：

#### 方案1: 使用代理服务器
在采集器中配置HTTP代理：

```python
self.session.proxies = {
    'http': 'http://your-proxy:port',
    'https': 'http://your-proxy:port'
}
```

#### 方案2: 调整请求策略
- 增加延迟时间（每次请求间隔10-30秒）
- 使用浏览器指纹库（如undetected-chromedriver）
- 添加更真实的浏览器行为模拟

#### 方案3: 手动数据导入
从OBIA网站手动下载PDF列表，使用脚本批量导入数据库

## 采集器架构

### 核心流程

```
1. 获取MySQL中最新出版物URL
   ↓
2. 使用requests爬取出版物列表页
   ↓
3. 解析HTML提取出版物数据
   - 标题
   - 分类（PANORAMA/PESQUISAS TIC）
   - 作者（从<em>标签提取）
   - PDF链接
   - 发布时间（从URL时间戳提取：YYYYMMDDhhmmss）
   ↓
4. 过滤已存在URL（遇到最新URL立即停止）
   ↓
5. 预翻译所有摘要（葡萄牙语→中文）
   ↓
6. 并发存储到MySQL + ChromaDB
```

### 关键特性

1. **智能停止机制**: 遇到数据库中已存在的URL立即停止采集
2. **预翻译模式**: 所有翻译在数据库会话之外完成，避免连接阻塞
3. **降级策略**: 翻译失败时自动使用截断原文
4. **去重保障**: URL字段UNIQUE约束 + IntegrityError捕获

### 翻译策略

- **语言检测**: 自动检测中文字符占比（>30%判定为中文）
- **全文翻译**: 不限制长度，由translator内部智能处理
- **降级标记**: 翻译失败时添加 `[AI翻译暂不可用]` 标记

## 数据库结构

### 表名
`mp_obia_messages`

### 索引
- PRIMARY KEY: `id`
- UNIQUE KEY: `url`
- INDEX: `idx_source_id`, `idx_published_at`, `idx_crawled_at`
- INDEX: `idx_source_published` (source_id, published_at)
- INDEX: `idx_external_id`, `idx_category`

### 外键
- `source_id` → `mp_message_sources(id)` ON DELETE CASCADE

## 使用方法

### 1. 数据库注册

```bash
# 切换到UTF-8编码（Windows CMD）
chcp 65001

# 执行注册脚本
mysql -h localhost -P 3306 -u root -p123456 --default-character-set=utf8mb4 message_platform < backend/sources/obia/register.sql
```

### 2. 验证注册

```bash
mysql -h localhost -P 3306 -u root -p123456 --default-character-set=utf8mb4 message_platform -e "SELECT id, name, display_name, category, is_active FROM mp_message_sources WHERE name = 'obia'"
```

### 3. 测试采集（需要解决反爬虫）

```bash
cd D:\TechWork\message_platform
python backend/sources/obia/test_collector.py
```

## 数据样例

### 出版物示例1
- **标题**: Inteligência Artificial em perspectiva
- **分类**: PANORAMA SETORIAL DA INTERNET
- **描述**: Impacto da IA nas diferentes esferas da vida cotidiana
- **作者**: Carolina Bigonha, Eduardo Magrani, Sara Rendtorff-Smith
- **发布时间**: 2018-10
- **PDF**: https://cetic.br/media/docs/publicacoes/1/Panorama_outubro_2018_online.pdf

### 出版物示例2
- **标题**: TIC Educação 2022
- **分类**: PESQUISAS TIC
- **发布时间**: 2023-11-22
- **PDF**: [cetic.br链接]

## 注意事项

1. **反爬虫限制**: 当前采集器受网站反爬虫保护影响，需要配置代理或调整策略
2. **发布时间提取**: 从PDF URL中的14位时间戳提取（YYYYMMDDhhmmss）
3. **作者提取**: 从`<em>`标签中提取，支持分号或逗号分隔的多作者
4. **系列识别**: 从标题中自动提取系列名称（Panorama Setorial/TIC Empresas等）
5. **翻译质量**: 葡萄牙语内容通过LLM翻译成中文，翻译失败时保留原文

## 未来改进

1. 实现代理池轮换机制
2. 添加Cloudflare绕过逻辑
3. 支持手动数据导入工具
4. 实现增量更新检测（基于PDF文件哈希）
5. 添加PDF文本提取功能（提供更完整的content）

## 相关文件

- `collector.py` - 采集器主文件
- `register.sql` - 数据库注册脚本
- `test_collector.py` - 测试脚本
- `__init__.py` - 模块初始化

## 联系与支持

如遇到问题或有改进建议，请查看项目主文档或提交Issue。
