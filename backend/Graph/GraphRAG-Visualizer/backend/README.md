# GraphRAG Visualizer - 后端服务

基于 FastAPI 的 GraphRAG 可视化应用后端服务。

## 功能特性

- **PDF 文件上传**：支持 PDF 文件上传和文本提取
- **分页处理**：支持指定页面范围提取（默认 1-20 页）
- **实体提取**：使用 GraphRAG 提取实体和关系
- **图谱构建**：自动构建知识图谱并存储到 Neo4j
- **图谱查询**：提供 ECharts 格式的图谱可视化数据

## 技术栈

- **FastAPI**: 现代化的 Python Web 框架
- **pdfplumber**: PDF 文本提取
- **GraphRAG**: 知识图谱构建工具包
- **Neo4j**: 图数据库
- **Pydantic**: 数据验证

## 快速开始

### 1. 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 2. 配置环境变量

创建 `.env` 文件：

```env
# GraphRAG 配置文件路径
GRAPHRAG_CONFIG_PATH=../GraphRAG/config/default_config.yaml

# 上传目录
UPLOAD_DIR=uploads

# CORS 允许的来源
CORS_ORIGINS=["http://localhost:5173"]
```

### 3. 确保 Neo4j 运行

确保 Neo4j 数据库正在运行，并且 GraphRAG 配置文件中的连接信息正确。

### 4. 启动服务

```bash
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

服务将在 http://localhost:8000 启动。

## API 文档

启动服务后，访问以下地址查看 API 文档：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 主要 API 端点

### 1. 上传 PDF 文件

```http
POST /api/upload
Content-Type: multipart/form-data

参数:
- file: PDF 文件
- page_start: 起始页码（默认 1）
- page_end: 结束页码（默认 20）

响应:
{
  "file_id": "uuid",
  "filename": "example.pdf",
  "total_pages": 50,
  "current_range": "1-20",
  "text": "提取的文本...",
  "char_count": 5000
}
```

### 2. 提取实体和关系

```http
POST /api/extract
Content-Type: application/json

请求体:
{
  "file_id": "uuid",
  "text": "文本内容",
  "language": "zh",
  "page_range": "1-20"
}

响应:
{
  "entities": [...],
  "relations": [...],
  "stats": {
    "entities_created": 5,
    "relations_created": 3
  }
}
```

### 3. 获取图谱可视化数据

```http
GET /api/graph/visualize/{file_id}?page_range=1-20

响应:
{
  "nodes": [...],
  "links": [...],
  "categories": [...]
}
```

## 项目结构

```
backend/
├── app/
│   ├── main.py              # FastAPI 主应用
│   ├── config.py            # 配置管理
│   ├── routers/             # API 路由
│   │   ├── upload.py        # 文件上传
│   │   ├── extract.py       # 实体提取
│   │   └── graph.py         # 图谱查询
│   ├── services/            # 业务逻辑
│   │   ├── pdf_service.py   # PDF 处理
│   │   └── graphrag_service.py  # GraphRAG 封装
│   └── models/
│       └── schemas.py       # 数据模型
├── requirements.txt         # Python 依赖
└── README.md               # 本文件
```

## 开发说明

### 添加新的 API 端点

1. 在 `app/routers/` 目录下创建新的路由文件
2. 在 `app/main.py` 中注册路由
3. 在 `app/models/schemas.py` 中定义数据模型

### 错误处理

所有 API 端点都使用 HTTPException 进行错误处理，返回标准的错误响应。

## 注意事项

1. 确保 GraphRAG 配置文件路径正确
2. 确保 Neo4j 数据库正常运行
3. 上传的 PDF 文件会保存在 `uploads/` 目录
4. 建议设置文件大小限制（默认 50MB）
