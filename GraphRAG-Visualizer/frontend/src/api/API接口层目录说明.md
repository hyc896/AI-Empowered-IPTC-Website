# API 接口层目录说明

## 目录作用

api 目录包含所有与后端 API 交互的接口定义，负责封装 HTTP 请求逻辑。

## 文件列表

### 核心文件

- `index.ts` - Axios 实例配置和通用 API 配置
  - 创建 axios 实例
  - 配置基础 URL（从环境变量读取）
  - 配置请求超时时间
  - 配置请求和响应拦截器
  - 导出配置好的 axios 实例

- `upload.ts` - 文件上传相关接口
  - `uploadFile()` - 上传 PDF/TXT 文件
  - 支持文件、页面范围、自定义名称参数
  - 返回文件 ID 和处理结果

- `graph.ts` - 图谱数据查询接口
  - `getCosmaData()` - 获取 Cosma 格式的图谱数据
  - `deleteGraph()` - 删除指定图谱
  - `renameGraph()` - 重命名图谱
  - `getGraphList()` - 获取图谱列表

## 技术说明

### Axios 配置

- 基础 URL 从环境变量 `VITE_API_BASE_URL` 读取
- 默认超时时间 30 秒
- 自动添加 Content-Type 请求头
- 统一的错误处理机制

### 请求拦截器

- 在请求发送前添加通用配置
- 可添加认证 token（待实现）
- 记录请求日志（开发环境）

### 响应拦截器

- 统一处理响应数据
- 捕获并处理 HTTP 错误
- 显示错误提示信息

## 使用示例

### 上传文件

```typescript
import { uploadFile } from '@/api/upload'

const file = new File(['content'], 'test.txt')
const result = await uploadFile(file, 1, 10, '我的文档')
console.log(result.file_id)
```

### 获取图谱数据

```typescript
import { getCosmaData } from '@/api/graph'

const data = await getCosmaData('file-id-123')
console.log(data.nodes, data.links)
```

## 扩展方式

### 添加新的 API 接口

1. 在对应的文件中添加新函数
2. 使用导入的 api 实例发起请求
3. 定义返回类型（TypeScript）
4. 导出函数供组件使用

示例：

```typescript
import api from './index'

export const fetchUserInfo = async (userId: string) => {
  const response = await api.get(`/api/users/${userId}`)
  return response.data
}
```

## 注意事项

### 错误处理

- 所有 API 调用都应该使用 try-catch 捕获错误
- 网络错误会自动显示提示信息
- 业务错误需要在组件中处理

### 类型安全

- 为所有 API 函数定义返回类型
- 使用 TypeScript 接口定义请求和响应数据结构
- 避免使用 any 类型

### 性能优化

- 避免重复请求相同的数据
- 考虑使用请求缓存
- 大文件上传使用分片上传（待实现）
