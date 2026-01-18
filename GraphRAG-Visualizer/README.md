# GraphRAG Visualizer

基于 GraphRAG 工具包的 PDF 文本实体提取和知识图谱可视化应用。

## 项目概述

GraphRAG Visualizer 是一个 Web 应用，可以：
- 上传 PDF 文件并提取文本内容
- 使用 AI 自动提取实体和关系
- 在 Neo4j 中构建知识图谱
- 使用 ECharts 可视化展示图谱

## 核心功能

### ✅ 已实现（后端）

- **PDF 文件上传**：支持拖拽上传 PDF 文件
- **分页处理**：支持指定页面范围提取（如 1-20 页）
- **实体提取**：自动识别 8 种实体类型（公司、人物、技术等）
- **关系识别**：自动识别 7 种关系类型（任职、投资、开发等）
- **图谱构建**：自动构建知识图谱并存储到 Neo4j
- **图谱查询**：提供 ECharts 格式的可视化数据

### 🚧 待实现（前端）

- 文件上传界面
- 文本预览组件
- 实体列表展示
- 图谱可视化渲染
- 历史记录功能
- 导出功能

## 技术架构

### 后端
- **FastAPI**: Python 异步 Web 框架
- **GraphRAG**: 知识图谱构建工具包
- **Neo4j**: 图数据库
- **pdfplumber**: PDF 文本提取

### 前端（待实现）
- **Vue 3**: 前端框架
- **Element Plus**: UI 组件库
- **ECharts**: 图谱可视化
- **TypeScript**: 类型安全

## 快速开始

### 前置要求

1. Python 3.8+
2. Node.js 16+
3. Neo4j 数据库
4. OpenAI API Key（用于实体提取）

### 1. 启动 Neo4j

确保 Neo4j 数据库正在运行：

```bash
# 使用 Docker 启动 Neo4j
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:latest
```

### 2. 配置 GraphRAG

编辑 `GraphRAG/config/default_config.yaml`：

```yaml
neo4j:
  uri: bolt://localhost:7687
  user: neo4j
  password: your_password

llm:
  provider: openai
  model: gpt-4
  api_key: your_api_key
```

### 3. 启动后端服务

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

后端服务将在 http://localhost:8000 启动。

### 4. 测试 API

访问 http://localhost:8000/docs 查看 API 文档并测试接口。

## 项目结构

```
GraphRAG-Visualizer/
├── backend/                 # 后端服务（已完成）
│   ├── app/
│   │   ├── main.py         # FastAPI 主应用
│   │   ├── config.py       # 配置管理
│   │   ├── routers/        # API 路由
│   │   ├── services/       # 业务逻辑
│   │   └── models/         # 数据模型
│   ├── requirements.txt
│   └── README.md
│
├── frontend/               # 前端应用（待实现）
│   └── (Vue 3 项目)
│
├── GraphRAG/              # GraphRAG 工具包（已存在）
└── README.md              # 本文件
```

## 使用示例

### 1. 上传 PDF 文件

```bash
curl -X POST "http://localhost:8000/api/upload" \
  -F "file=@example.pdf" \
  -F "page_start=1" \
  -F "page_end=20"
```

### 2. 提取实体

```bash
curl -X POST "http://localhost:8000/api/extract" \
  -H "Content-Type: application/json" \
  -d '{
    "file_id": "uuid",
    "text": "OpenAI发布了GPT-4...",
    "language": "zh"
  }'
```

### 3. 获取图谱数据

```bash
curl "http://localhost:8000/api/graph/visualize/uuid?page_range=1-20"
```

## 开发计划

- [x] 后端基础架构
- [x] PDF 文件上传和文本提取
- [x] 实体提取和图谱构建
- [x] 图谱查询接口
- [ ] 前端 Vue 3 项目搭建
- [ ] 文件上传组件
- [ ] 图谱可视化组件
- [ ] 历史记录功能
- [ ] 导出功能

## 贡献指南

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License
