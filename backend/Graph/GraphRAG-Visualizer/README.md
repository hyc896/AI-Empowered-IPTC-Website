# GraphRAG Visualizer

基于 GraphRAG 工具包的 PDF/TXT 文本实体提取和知识图谱可视化应用。

## 项目概述

GraphRAG Visualizer 是一个全栈 Web 应用，提供完整的知识图谱构建和可视化解决方案：
- 上传 PDF/TXT 文件并提取文本内容
- 使用 AI 自动提取实体和关系
- 在 Neo4j 中构建知识图谱
- 使用 Cosma 图谱引擎进行交互式可视化
- 支持实体搜索、筛选和图谱导出

## 核心功能

### ✅ 已实现功能

#### 后端服务
- **文件上传**：支持 PDF 和 TXT 文件上传，支持分页处理
- **文本提取**：使用 pdfplumber 提取 PDF 文本内容
- **实体提取**：基于 GraphRAG 自动识别实体和关系
- **图谱构建**：自动构建知识图谱并存储到 Neo4j
- **图谱查询**：提供 Cosma 格式的可视化数据
- **进度管理**：实时推送处理进度信息
- **配置管理**：支持动态配置 API 密钥和模型参数

#### 前端应用
- **文件上传界面**：拖拽上传，支持文件重命名
- **图谱可视化**：基于 Cosma 的交互式图谱展示
- **实体搜索**：支持模糊搜索和实体筛选
- **进度显示**：实时显示处理进度和状态
- **配置面板**：可视化配置 API 和模型参数
- **图谱操作**：支持删除、重命名等操作

## 技术架构

### 后端技术栈

- **FastAPI**: Python 异步 Web 框架，提供高性能 API 服务
- **GraphRAG**: 知识图谱构建工具包，负责实体提取和关系识别
- **Neo4j**: 图数据库，存储知识图谱数据
- **pdfplumber**: PDF 文本提取库
- **Pydantic**: 数据验证和配置管理
- **python-dotenv**: 环境变量管理

### 前端技术栈

- **Vue 3**: 渐进式前端框架，使用 Composition API
- **TypeScript**: 类型安全的 JavaScript 超集
- **Vite**: 现代化的前端构建工具
- **D3.js**: 数据可视化库，用于图谱渲染
- **Graphology**: 图数据结构库
- **Fuse.js**: 模糊搜索库
- **Axios**: HTTP 客户端
- **Marked**: Markdown 解析器

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

# 配置环境变量（创建 .env 文件）
# GRAPHRAG_CONFIG_PATH=../GraphRAG/config/default_config.yaml

# 启动服务
python start.py
```

后端服务将在 http://localhost:8000 启动。

### 4. 启动前端应用

```bash
cd frontend
npm install

# 配置环境变量（.env.development）
# VITE_API_BASE_URL=http://localhost:8000

# 启动开发服务器
npm run dev
```

前端应用将在 http://localhost:5173 启动。

### 5. 访问应用

打开浏览器访问 http://localhost:5173，即可使用 GraphRAG Visualizer。

## 项目结构

```text
GraphRAG-Visualizer/
├── backend/                      # 后端服务
│   ├── app/
│   │   ├── main.py              # FastAPI 主应用
│   │   ├── config.py            # 配置管理
│   │   ├── routers/             # API 路由
│   │   │   ├── upload.py        # 文件上传路由
│   │   │   ├── extract.py       # 实体提取路由
│   │   │   ├── graph.py         # 图谱查询路由
│   │   │   └── config.py        # 配置管理路由
│   │   ├── services/            # 业务逻辑
│   │   │   ├── pdf_service.py   # PDF 处理服务
│   │   │   ├── graphrag_service.py  # GraphRAG 服务
│   │   │   └── progress_manager.py  # 进度管理服务
│   │   └── models/              # 数据模型
│   │       └── schemas.py       # Pydantic 数据模型
│   ├── uploads/                 # 上传文件存储目录
│   ├── storage/                 # 数据存储目录
│   ├── requirements.txt         # Python 依赖
│   ├── start.py                 # 启动脚本
│   └── 后端目录说明.md          # 后端目录说明
│
├── frontend/                     # 前端应用
│   ├── src/
│   │   ├── App.vue              # 主应用组件
│   │   ├── main.ts              # 应用入口
│   │   ├── api/                 # API 接口
│   │   │   ├── index.ts         # API 配置
│   │   │   ├── upload.ts        # 上传接口
│   │   │   └── graph.ts         # 图谱接口
│   │   ├── components/          # Vue 组件
│   │   │   ├── CosmaViewer.vue  # Cosma 图谱查看器
│   │   │   ├── Dialog/          # 对话框组件
│   │   │   └── Progress/        # 进度组件
│   │   ├── cosma/               # Cosma 图谱引擎
│   │   │   └── graph.ts         # 图谱渲染逻辑
│   │   ├── types/               # TypeScript 类型定义
│   │   └── utils/               # 工具函数
│   ├── package.json             # 前端依赖
│   └── vite.config.ts           # Vite 配置
│
├── GraphRAG/                     # GraphRAG 工具包
│   ├── config/                  # 配置文件
│   │   └── default_config.yaml  # 默认配置
│   └── graphrag/                # GraphRAG 核心代码
│
└── README.md                     # 项目说明文档
```

## 使用指南

### Web 界面使用

1. **上传文件**
   - 点击上传区域或拖拽文件到上传区
   - 支持 PDF 和 TXT 格式
   - 可选择页面范围（仅 PDF）
   - 可自定义文件名

2. **查看图谱**
   - 上传完成后自动显示知识图谱
   - 使用鼠标拖拽移动视图
   - 滚轮缩放图谱
   - 点击节点查看详情

3. **搜索实体**
   - 使用搜索框进行模糊搜索
   - 支持实体名称和类型筛选
   - 点击搜索结果定位到节点

4. **配置设置**
   - 点击设置按钮打开配置面板
   - 配置 API 密钥和基础 URL
   - 选择 LLM 模型
   - 设置提取参数

### API 使用示例

#### 1. 上传文件

```bash
curl -X POST "http://localhost:8000/api/upload" \
  -F "file=@example.pdf" \
  -F "page_start=1" \
  -F "page_end=20" \
  -F "custom_name=我的文档"
```

#### 2. 获取图谱数据

```bash
curl "http://localhost:8000/api/graph/cosma/file_id"
```

#### 3. 删除图谱

```bash
curl -X DELETE "http://localhost:8000/api/graph/file_id"
```

#### 4. 重命名图谱

```bash
curl -X PUT "http://localhost:8000/api/graph/file_id/rename" \
  -H "Content-Type: application/json" \
  -d '{"new_name": "新名称"}'
```

## 开发计划

### 已完成功能

- [x] 后端基础架构
- [x] PDF/TXT 文件上传和文本提取
- [x] 实体提取和图谱构建
- [x] 图谱查询接口
- [x] 前端 Vue 3 项目搭建
- [x] 文件上传组件
- [x] Cosma 图谱可视化组件
- [x] 实体搜索和筛选
- [x] 进度显示功能
- [x] 配置管理面板
- [x] 图谱删除和重命名

### 待开发功能

- [ ] 图谱导出功能（JSON、PNG、SVG）
- [ ] 历史记录管理
- [ ] 多文件批量处理
- [ ] 实体编辑功能
- [ ] 关系编辑功能
- [ ] 图谱合并功能
- [ ] 用户认证系统
- [ ] 数据持久化优化

## 常见问题

### 1. Neo4j 连接失败

确保 Neo4j 数据库正在运行，并检查配置文件中的连接信息是否正确。

### 2. API 调用失败

检查 API 密钥是否正确配置，确保有足够的 API 配额。

### 3. 前端无法连接后端

检查后端服务是否正常运行，确认 CORS 配置正确。

## 贡献指南

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License
