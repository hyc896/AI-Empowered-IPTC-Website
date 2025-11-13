# 消息平台 (Message Platform)

个人Agent系统的独立消息采集与检索平台，提供统一的消息源管理和检索服务。

## 🎯 功能特性

- **多源消息采集**: 支持同花顺、36氪、arXiv等多种消息源
- **智能检索**: MySQL+ChromaDB混合检索，支持关键词和语义搜索
- **RESTful API**: 标准化的API接口，易于集成
- **实时采集**: 自动化的消息采集和更新
- **向量存储**: 基于ChromaDB的语义向量检索
- **监控告警**: 完整的健康检查和监控体系

## 📁 项目结构

```
message_platform/
├── backend/                 # 后端代码
│   ├── api/                # API路由层
│   │   ├── search_routes.py      # 检索API
│   │   ├── source_routes.py      # 消息源管理API
│   │   ├── collector_routes.py   # 采集器控制API
│   │   └── stats_routes.py        # 统计API
│   ├── services/           # 核心服务层
│   │   ├── collector_service.py   # 采集器服务
│   │   └── search_service.py      # 检索服务
│   ├── sources/            # 消息源插件
│   │   ├── tonghuashun/           # 同花顺采集器
│   │   ├── kr36/                  # 36氪采集器
│   │   └── arxiv/                 # arXiv采集器
│   ├── database/           # 数据库层
│   │   ├── entities.py             # ORM实体
│   │   └── connection.py          # 连接管理
│   └── main.py             # 应用入口
├── config/                # 配置文件
│   └── platform_config.yaml # 主配置文件
├── data/                  # 运行时数据
├── logs/                  # 日志文件
├── tests/                 # 测试文件
├── requirements.txt       # Python依赖
└── README.md             # 项目文档
```

## 🚀 快速开始

### 1. 环境准备

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置数据库

```bash
# 创建消息平台数据库
mysql -u root -p
CREATE DATABASE message_platform CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 3. 配置文件

编辑 `config/platform_config.yaml` 文件，配置数据库连接等信息：

```yaml
database:
  mysql:
    host: "localhost"
    port: 3306
    user: "root"
    password: "your_password"
    database: "message_platform"

web:
  host: "0.0.0.0"
  port: 11523
```

### 4. 启动服务

```bash
# 开发模式启动
conda activate personal_agent; python backend/main.py
cd global-news-dashboard; npm install; npm run dev

```

### 5. 验证服务

- API文档: http://localhost:11523/docs
- 健康检查: http://localhost:11523/health

## 📡 API接口

### 消息检索

```http
POST /api/v1/search
Content-Type: application/json

{
    "source_type": "news",
    "query": "财经资讯",
    "time_range": {"hours": 24},
    "limit": 20
}
```

### 消息源管理

```http
# 获取消息源列表
GET /api/v1/sources

# 创建消息源
POST /api/v1/sources

# 启动采集器
POST /api/v1/collectors/{source_name}/start

# 停止采集器
POST /api/v1/collectors/{source_name}/stop
```

### 统计信息

```http
GET /api/v1/stats
```

## 🗄️ 数据库设计

### 核心表结构

1. **mp_message_sources** - 消息源配置表
2. **mp_tonghuashun_messages** - 同花顺消息表
3. **mp_kr36_messages** - 36氪消息表
4. **mp_arxiv_messages** - arXiv论文表
5. **mp_external_messages** - 通用外部消息表

### 外键关系

```
mp_message_sources (1)
├── mp_tonghuashun_messages (N)
├── mp_kr36_messages (N)
├── mp_arxiv_messages (N)
└── mp_external_messages (N)
```

## 🔧 配置说明

### 数据库配置

```yaml
database:
  mysql:
    host: "localhost"
    port: 3306
    user: "root"
    password: "password"
    database: "message_platform"
    pool_size: 20
```

### 采集器配置

```yaml
collectors:
  tonghuashun:
    enabled: true
    interval: 15  # 采集间隔（秒）
  kr36:
    enabled: true
    interval: 30
  arxiv:
    enabled: true
    interval: 86400  # 24小时
```

### 检索配置

```yaml
retrieval:
  similarity_threshold: 0.4  # 相似度阈值
  rrf_k: 60                  # RRF融合参数
  max_results: 100           # 最大结果数
```

## 🧪 测试

```bash
# 运行测试
pytest tests/

# 运行特定测试
pytest tests/test_search_service.py

# 生成覆盖率报告
pytest --cov=backend tests/
```

## 📊 监控

### 健康检查

```bash
curl http://localhost:11523/health
```

### 指标监控

- 服务状态: `/health`
- 采集器状态: `/api/v1/collectors/status`
- 系统统计: `/api/v1/stats`

## 🔗 与Agent系统集成

消息平台通过HTTP API与PersonalAgent项目集成：

1. **Agent项目**: 通过HTTP客户端调用消息平台API
2. **消息平台**: 提供标准化的检索和管理接口
3. **数据同步**: 支持增量同步和全量同步

### 接口示例

```python
# Agent项目中的调用示例
import httpx

async def search_messages(query: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:11523/api/v1/search",
            json={
                "source_type": "news",
                "query": query,
                "limit": 20
            }
        )
        return response.json()
```

## 🚀 部署

### Docker部署（可选）

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 11523

CMD ["python", "backend/main.py"]
```

### 生产环境配置

1. 使用Gunicorn作为WSGI服务器
2. 配置Nginx反向代理
3. 设置SSL证书
4. 配置日志轮转
5. 设置监控告警

## 🤝 贡献

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📝 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 📞 联系方式

- 项目主页: [GitHub Repository]
- 问题反馈: [Issues]
- 文档: [Wiki]

## 🙏 致谢

感谢以下开源项目的支持：

- [FastAPI](https://fastapi.tiangolo.com/) - 现代化的Python Web框架
- [ChromaDB](https://www.trychroma.com/) - 开源向量数据库
- [SQLAlchemy](https://www.sqlalchemy.org/) - Python SQL工具包
- [Playwright](https://playwright.dev/) - 现代化网页爬虫框架