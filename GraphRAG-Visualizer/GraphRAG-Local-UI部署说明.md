# GraphRAG-Local-UI 部署说明

## 项目概述

本项目使用 GraphRAG-Local-UI 作为前端界面，这是一个功能完整的 GraphRAG 可视化工具，包含：
- 文件管理和上传
- 索引构建和提示调优
- 查询和聊天功能
- 2D/3D 知识图谱可视化

## 部署架构

### 服务组件

1. **GraphRAG API 服务器**
   - 端口：8012
   - 功能：提供 GraphRAG 核心功能的 REST API
   - 启动命令：`conda run -n graphrag-ui python api.py --host 0.0.0.0 --port 8012`

2. **Gradio 用户界面**
   - 端口：7860
   - 功能：交互式 Web 界面
   - 启动命令：`conda run -n graphrag-ui gradio app.py`

### 技术栈

- **Python 版本**：3.12（通过 conda 虚拟环境）
- **虚拟环境名称**：graphrag-ui
- **主要依赖**：
  - graphrag（自定义版本，支持 Python 3.13）
  - gradio 6.3.0
  - fastapi 0.128.0
  - langchain-community 0.4.1
  - plotly 6.5.2

## 部署步骤

### 1. 环境准备

创建 Python 3.12 虚拟环境：
```bash
conda create -n graphrag-ui python=3.12 -y
conda activate graphrag-ui
```

### 2. 安装依赖

安装 GraphRAG 包：
```bash
cd frontend
pip install -e ./graphrag
```

安装其他依赖：
```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

创建 `.env` 文件（已提供示例配置）：
```env
# LLM 配置
LLM_PROVIDER=openai
LLM_API_BASE=http://localhost:11434/v1
LLM_MODEL=mistral-large:123b-instruct-2407-q4_0
LLM_API_KEY=12345

# Embeddings 配置
EMBEDDINGS_PROVIDER=openai
EMBEDDINGS_API_BASE=http://localhost:11434
EMBEDDINGS_MODEL=snowflake-arctic-embed:335m
EMBEDDINGS_API_KEY=12345

# API 配置
API_URL=http://localhost:8012
API_PORT=8012
```

### 4. 启动服务

启动 API 服务器：
```bash
conda run -n graphrag-ui python api.py --host 0.0.0.0 --port 8012
```

启动 Gradio UI（新终端）：
```bash
conda run -n graphrag-ui gradio app.py
```

### 5. 访问应用

在浏览器中打开：http://localhost:7860

## 目录结构

```
GraphRAG-Visualizer/
├── frontend/                    # GraphRAG-Local-UI 项目
│   ├── graphrag/               # GraphRAG 核心包
│   ├── indexing/               # 索引数据目录
│   ├── api.py                  # API 服务器
│   ├── app.py                  # Gradio 主应用
│   ├── index_app.py            # 索引和提示调优 UI
│   ├── web.py                  # DuckDuckGo 搜索封装
│   ├── requirements.txt        # Python 依赖
│   ├── .env                    # 环境变量配置
│   └── README.md               # 项目文档
│
├── frontend.bak/               # 原 Vue 前端备份
└── backend/                    # 原后端服务（可选）
```

## 功能说明

### 主要功能

1. **文件管理**
   - 上传 PDF、TXT 等文档
   - 查看和编辑输入文件
   - 删除不需要的文件

2. **索引构建**
   - 运行 GraphRAG 索引
   - 查看索引进度和日志
   - 浏览索引输出和工件

3. **查询功能**
   - 全局查询：跨整个知识图谱搜索
   - 本地查询：针对特定实体的查询
   - 直接聊天：与知识图谱对话

4. **图谱可视化**
   - 2D/3D 交互式图谱展示
   - 节点和边的自定义样式
   - 图谱布局调整

5. **设置管理**
   - 配置 LLM 和 Embeddings 模型
   - 调整 GraphRAG 参数
   - 管理 API 密钥

## 故障排除

### 常见问题

**1. 端口被占用**

如果端口 8012 或 7860 被占用，可以修改启动命令：

```bash
# 修改 API 端口
python api.py --host 0.0.0.0 --port 8013

# 修改 Gradio 端口
gradio app.py --server-port 7861
```

**2. 依赖安装失败**

确保使用正确的 Python 版本（3.12）：

```bash
conda activate graphrag-ui
python --version  # 应显示 Python 3.12.x
```

**3. LLM 连接失败**

检查 `.env` 文件中的 LLM 配置是否正确，确保 Ollama 或其他 LLM 服务正在运行。

## 使用建议

1. **首次使用**：先上传一些测试文档，运行索引构建
2. **模型选择**：根据硬件配置选择合适的 LLM 模型
3. **数据备份**：定期备份 `indexing/` 目录中的数据
4. **性能优化**：对于大型文档集，建议分批处理

## 相关链接

- [GraphRAG-Local-UI GitHub](https://github.com/severian42/GraphRAG-Local-UI)
- [Microsoft GraphRAG](https://github.com/microsoft/graphrag)
- [Gradio 文档](https://www.gradio.app/docs)

## 更新日志

### 2026-01-18

- ✅ 成功部署 GraphRAG-Local-UI
- ✅ 修复 Pydantic v2 兼容性问题
- ✅ 配置 Python 3.12 虚拟环境
- ✅ 启动 API 服务器和 Gradio UI

