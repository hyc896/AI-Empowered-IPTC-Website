# GraphRAG Visualizer Frontend

基于 Vue 3 + TypeScript + AntV G6 的知识图谱可视化前端应用。

## 技术栈

- **Vue 3** - 渐进式 JavaScript 框架
- **TypeScript** - 类型安全的 JavaScript 超集
- **Vite** - 下一代前端构建工具
- **Element Plus** - Vue 3 UI 组件库
- **AntV G6** - 图可视化引擎
- **Axios** - HTTP 客户端
- **Vue Router** - 官方路由管理器

## 功能特性

- ✅ PDF 文件上传和页面范围选择
- ✅ 实体和关系自动提取
- ✅ 知识图谱可视化（基于 G6）
- ✅ 实体列表展示
- ✅ 图谱交互操作（缩放、拖拽、搜索）
- ✅ 响应式布局设计

## 快速开始

### 前置要求

- Node.js 16+
- npm 或 yarn

### 安装依赖

```bash
cd frontend-new
npm install
```

### 开发模式

```bash
npm run dev
```

应用将在 http://localhost:5173 启动。

### 构建生产版本

```bash
npm run build
```

构建产物将输出到 `dist` 目录。

### 预览生产构建

```bash
npm run preview
```

## 项目结构

```
frontend-new/
├── src/
│   ├── api/              # API 服务层
│   │   ├── index.ts      # Axios 实例配置
│   │   ├── upload.ts     # 文件上传 API
│   │   ├── extract.ts    # 实体提取 API
│   │   └── graph.ts      # 图谱查询 API
│   ├── components/       # 组件目录
│   │   ├── Layout/       # 布局组件
│   │   ├── Upload/       # 上传组件
│   │   ├── Graph/        # 图谱组件
│   │   └── Entity/       # 实体组件
│   ├── views/            # 页面组件
│   │   └── Home.vue      # 主页面
│   ├── router/           # 路由配置
│   ├── types/            # TypeScript 类型定义
│   ├── App.vue           # 根组件
│   └── main.ts           # 应用入口
├── index.html            # HTML 入口
├── vite.config.ts        # Vite 配置
├── tsconfig.json         # TypeScript 配置
└── package.json          # 项目依赖
```

## 配置说明

### 环境变量

复制 `.env.example` 为 `.env` 并配置：

```bash
# 后端 API 地址
VITE_API_BASE_URL=http://localhost:8000
```

### 代理配置

开发环境下，Vite 会自动将 `/api` 请求代理到后端服务器（配置在 `vite.config.ts`）。

## 核心组件说明

### MainLayout

主布局组件，提供顶部导航栏和内容区域。

### UploadDialog

文件上传对话框，支持：

- PDF 文件拖拽上传
- 页面范围选择
- 上传进度显示

### GraphViewer

G6 图谱可视化组件，支持：

- 力导向布局
- 节点拖拽
- 画布缩放
- 适应画布
- 实体类型颜色区分

### EntityList

实体和关系列表展示组件，支持：

- 实体列表（带类型标签）
- 关系列表
- 统计信息

## API 接口

### 文件上传

```typescript
uploadPDF(file: File, pageStart: number, pageEnd: number)
```

### 实体提取

```typescript
extractEntities(data: ExtractRequest)
```

### 图谱查询

```typescript
getGraphData(fileId: string, pageRange?: string)
```

## 开发指南

### 添加新组件

1. 在 `src/components/` 下创建组件目录
2. 创建 `.vue` 文件
3. 在需要的地方导入使用

### 添加新 API

1. 在 `src/api/` 下创建对应的 API 文件
2. 定义 API 函数
3. 在 `src/types/` 中定义类型

## 注意事项

- 使用 `toRaw()` 处理 Vue 响应式数据后再传递给 G6
- G6 实例需要在组件卸载时销毁
- 图谱数据较大时注意性能优化

## 许可证

MIT License
