# Global News Dashboard

基于message_platform的国际新闻消息大屏前端项目。

## 技术栈

- Vue 3
- TypeScript
- Vite
- Element Plus
- Pinia
- Vue Router
- Axios
- Markdown-it
- Highlight.js
- SCSS

## 项目结构

```
global-news-dashboard/
├── src/
│   ├── api/                 # API接口层
│   │   ├── index.ts        # Axios实例配置
│   │   └── message.ts      # 消息相关API
│   ├── assets/             # 静态资源
│   │   └── styles/         # 全局样式
│   ├── components/         # 组件
│   │   └── common/         # 通用组件
│   │       ├── ExternalMessageCard.vue
│   │       ├── MessageSourceCard.vue
│   │       └── MarkdownRenderer.vue
│   ├── plugins/            # 插件
│   │   └── message-sources.ts
│   ├── router/             # 路由配置
│   │   └── index.ts
│   ├── stores/             # Pinia状态管理
│   │   ├── index.ts
│   │   └── message.ts
│   ├── types/              # TypeScript类型定义
│   │   ├── api.ts
│   │   ├── models.ts
│   │   └── store.ts
│   ├── utils/              # 工具函数
│   │   ├── constants.ts
│   │   ├── date.ts
│   │   ├── format.ts
│   │   └── markdown.ts
│   ├── views/              # 页面视图
│   │   ├── Messages/       # 消息列表页
│   │   └── MessageSources/ # 消息源管理页
│   ├── App.vue             # 根组件
│   └── main.ts             # 入口文件
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
└── README.md
```

## API配置

项目通过API连接到message_platform后端服务（端口: 11528）

API Base URL: `http://localhost:11528`

主要API端点:
- GET /api/v1/sources - 获取消息源列表
- POST /api/v1/sources - 创建消息源
- PUT /api/v1/sources/{id} - 更新消息源
- DELETE /api/v1/sources/{id} - 删除消息源
- GET /api/v1/messages - 获取消息列表
- GET /api/v1/stats/overview - 获取统计信息

## 功能模块

### 消息列表 (/messages)
- 消息筛选（按来源、关键词）
- 消息分页显示
- 消息详情查看
- 统计数据展示

### 消息源管理 (/message-sources)
- 消息源列表展示
- 新建消息源
- 编辑消息源配置
- 删除消息源
- 启用/禁用消息源

## 开发指南

### 前置要求

- Node.js 16+
- npm 或 yarn

### 安装依赖

```bash
npm install
```

### 启动开发服务器

确保message_platform后端服务运行在11528端口，然后执行:

```bash
npm run dev
```

开发服务器将在 http://localhost:5173 启动

### 构建生产版本

```bash
npm run build
```

### 预览生产构建

```bash
npm run preview
```

## 一键启动命令

```bash
cd D:\TechWork\global-news-dashboard; npm install; npm run dev
```

## 环境变量

`.env` - 默认环境变量
`.env.development` - 开发环境变量
`.env.production` - 生产环境变量

主要配置:
- `VITE_API_BASE_URL` - API基础地址（默认: http://localhost:11528）

## 注意事项

1. 确保message_platform后端服务正常运行
2. 后端服务端口为11528
3. API路径为 /api/v1/*
4. 前端开发服务器端口为5173
5. Vite已配置代理，/api请求会转发到后端服务

## 与personal_agent的关系

本项目从personal_agent项目的消息管理模块迁移而来，主要变更:
- API端点从 http://localhost:11522 改为 http://localhost:11528
- API路径从 /api/message/* 改为 /api/v1/*
- 移除了personal_agent的其他功能模块
- 简化了布局，专注于消息展示和管理

## 许可证

MIT

---

## 项目启动方式

### 前置要求

1. 确保已安装Node.js 16+和npm
2. 确保message_platform后端服务运行在11528端口

### 方式一：开发环境启动（推荐）

在项目根目录（global-news-dashboard/）下执行：

```bash
cd global-news-dashboard; npm install; npm run dev
```

启动后访问：http://localhost:5173

### 方式二：分步启动

**步骤1：安装依赖**
```bash
cd global-news-dashboard
npm install
```

**步骤2：启动开发服务器**
```bash
npm run dev
```

### 方式三：生产环境部署

**步骤1：构建生产版本**
```bash
cd global-news-dashboard
npm run build
```

**步骤2：预览构建结果**
```bash
npm run preview
```

**步骤3：部署到服务器**

将dist目录部署到Nginx/Apache等Web服务器，配置反向代理：

```nginx
location /api {
    proxy_pass http://localhost:11528;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

### 完整启动流程（前后端联合）

**终端1：启动后端服务**
```bash
cd message_platform
python backend/main.py
```

**终端2：启动前端服务**
```bash
cd message_platform/global-news-dashboard
npm run dev
```

### 启动验证

1. 后端健康检查：http://localhost:11528/health
2. 后端API文档：http://localhost:11528/docs
3. 前端访问地址：http://localhost:5173

### 常见问题

**Q1：端口被占用**
- 修改vite.config.ts中的port配置
- 或修改.env中的VITE_API_BASE_URL指向正确的后端地址

**Q2：API请求失败**
- 检查后端服务是否正常运行
- 检查.env文件中的VITE_API_BASE_URL配置
- 检查浏览器控制台网络请求

**Q3：依赖安装失败**
- 清理npm缓存：npm cache clean --force
- 删除node_modules和package-lock.json后重新安装
- 使用国内镜像：npm config set registry https://registry.npmmirror.com

### 开发工具推荐

- VS Code插件：Vue Language Features (Volar)
- VS Code插件：TypeScript Vue Plugin (Volar)
- 浏览器：Chrome + Vue DevTools扩展

### 更多信息

详细架构说明请参阅：项目架构.md
