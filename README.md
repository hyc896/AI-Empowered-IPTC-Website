# Message Platform

个人Agent系统的独立消息采集与检索平台，提供统一的消息源管理和检索服务。

## 核心功能

- **多源消息采集**: 同花顺、36氪、arXiv、Partnership on AI等多种消息源
- **智能检索**: MySQL+ChromaDB混合检索，支持关键词和语义搜索
- **RESTful API**: 标准化的HTTP API接口，易于集成
- **向量存储**: 基于ChromaDB的语义向量检索
- **消息源动态配置**: 数据库驱动的消息源管理

## 技术栈

- **后端框架**: FastAPI
- **数据库**: MySQL 8.0+ (关系数据库) + ChromaDB (向量数据库)
- **ORM**: SQLAlchemy
- **爬虫**: Playwright, httpx
- **前端Dashboard**: Vue 3 + Element Plus (位于global-news-dashboard目录)

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置数据库

```bash
mysql -u root -p -e "CREATE DATABASE message_platform CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

### 3. 配置文件

编辑 `config.yaml` 文件，配置数据库连接和LLM服务：

```yaml
database:
  mysql:
    host: "localhost"
    port: 3306
    user: "root"
    password: "your_password"
    database: "message_platform"

llm:
  embedding:
    base_url: "http://localhost:11434"
    api_key: "your_api_key"
    model: "nomic-embed-text"

web:
  host: "0.0.0.0"
  port: 11528
```

### 4. 启动服务

```bash
python backend/main.py
```

### 5. 访问服务

- **API文档**: http://localhost:11528/docs
- **健康检查**: http://localhost:11528/health
- **前端Dashboard**: 进入 `global-news-dashboard` 目录，运行 `npm install; npm run dev`

## 项目结构

```
message_platform/
├── backend/                        # 后端代码
│   ├── api/                        # API路由层
│   │   ├── search_routes.py       # 检索API
│   │   ├── source_routes.py       # 消息源管理API
│   │   ├── collector_routes.py    # 采集器控制API
│   │   └── stats_routes.py        # 统计API
│   ├── services/                   # 核心服务层
│   │   ├── collector_service.py   # 采集器服务
│   │   ├── search_service.py      # 检索服务
│   │   └── message/vector_sync.py # 向量同步服务
│   ├── sources/                    # 消息源插件
│   │   ├── tonghuashun/           # 同花顺采集器
│   │   ├── kr36/                  # 36氪采集器
│   │   ├── arxiv/                 # arXiv采集器
│   │   └── partnership_ai/        # Partnership on AI采集器
│   ├── database/                   # 数据库层
│   │   ├── entities.py            # ORM实体定义
│   │   ├── connection.py          # 数据库连接管理
│   │   ├── orm_registry.py        # ORM自动注册系统
│   │   └── startup_validator.py   # 启动配置验证
│   ├── storage/                    # 存储层
│   │   └── chromadb_storage.py    # ChromaDB存储
│   ├── llm/                        # LLM客户端
│   ├── config/                     # 配置管理
│   └── main.py                     # 应用入口
├── global-news-dashboard/          # 前端Dashboard (Vue 3)
│   ├── src/
│   ├── package.json
│   └── README.md
├── data/                           # 运行时数据
│   └── chromadb_mp/               # ChromaDB数据存储
├── logs/                           # 日志文件
├── config.yaml                     # 主配置文件
├── requirements.txt                # Python依赖
├── CLAUDE.md                       # 开发指导文档
├── 项目架构.md                     # 详细技术文档
└── README.md                       # 本文档
```

## 核心API接口

### 消息检索

```http
POST /api/v1/search/messages
Content-Type: application/json

{
    "source_type": "news",
    "query": "人工智能",
    "time_range": {"hours": 24},
    "limit": 20
}
```

### 消息源管理

- `GET /api/v1/sources` - 获取消息源列表
- `POST /api/v1/sources` - 创建新消息源
- `PUT /api/v1/sources/{source_id}` - 更新消息源
- `DELETE /api/v1/sources/{source_id}` - 删除消息源
- `POST /api/v1/sources/{source_id}/activate` - 启用消息源
- `POST /api/v1/sources/{source_id}/deactivate` - 禁用消息源

### 采集器控制

- `GET /api/v1/collectors/status` - 获取采集器状态
- `POST /api/v1/collectors/{source_name}/start` - 启动采集器
- `POST /api/v1/collectors/{source_name}/stop` - 停止采集器
- `POST /api/v1/collectors/{source_name}/trigger` - 手动触发采集

### 统计信息

- `GET /api/v1/stats/overview` - 获取系统统计概览
- `GET /api/v1/stats/sources` - 获取各消息源统计

完整API文档请访问：http://localhost:11528/docs

## 与PersonalAgent集成

消息平台通过HTTP API与PersonalAgent项目集成。PersonalAgent中的`message_platform_client.py`封装了所有API调用，并提供健康检查、重试机制等功能。

消息源配置存储在数据库中，PersonalAgent启动时会自动同步消息源信息，无需修改代码即可支持新消息源。

## 扩展消息源

1. 在 `backend/sources/` 创建新的消息源目录
2. 实现采集器类，包含 `__init__` 和 `collect` 方法
3. 在 `CollectorService.COLLECTOR_REGISTRY` 注册采集器
4. 在数据库 `mp_message_sources` 表注册消息源配置
5. PersonalAgent将自动同步新消息源

详细开发指导请参考 `CLAUDE.md` 和 `项目架构.md`

## 文档说明

- **README.md** (本文档): 快速开始指南
- **项目架构.md**: 详细技术文档，包含数据库设计、数据流向、消息源详情等
- **CLAUDE.md**: 开发指导文档，包含架构设计原则、编码规范、最佳实践等

## 许可证

MIT License
