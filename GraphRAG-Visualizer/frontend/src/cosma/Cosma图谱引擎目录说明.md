# Cosma 图谱引擎目录说明

## 目录作用

cosma 目录包含 Cosma 图谱可视化引擎的核心代码，负责图谱的渲染、交互和布局。

## 文件列表

### 核心文件

- `graph.ts` - Cosma 图谱渲染引擎
  - 基于 D3.js 实现力导向图布局
  - 使用 Graphology 管理图数据结构
  - 实现节点和边的渲染
  - 提供缩放、拖拽、搜索等交互功能
  - 支持自定义样式和主题

## 技术说明

### 核心技术

- **D3.js**: 数据驱动的文档操作库，用于 SVG 渲染
- **Graphology**: 强大的图数据结构库
- **力导向布局**: 使用 d3-force 实现节点自动布局
- **SVG 渲染**: 使用 SVG 元素渲染节点和边

### 主要功能

1. **图谱渲染**
   - 节点渲染（圆形、标签）
   - 边渲染（线条、箭头）
   - 颜色和样式管理

2. **交互功能**
   - 节点拖拽
   - 画布缩放和平移
   - 节点点击和悬停
   - 搜索高亮

3. **布局算法**
   - 力导向布局
   - 碰撞检测
   - 中心力和链接力
   - 多体力（节点排斥）

## 使用示例

### 初始化图谱

```typescript
import { Graph } from '@/cosma/graph'

const container = document.getElementById('graph-container')
const graph = new Graph(container, {
  nodes: [...],
  links: [...]
})
```

### 搜索节点

```typescript
graph.search('关键词')
```

### 更新图谱数据

```typescript
graph.updateData({
  nodes: [...],
  links: [...]
})
```

## 扩展方式

### 自定义节点样式

可以通过修改 `graph.ts` 中的节点渲染逻辑来自定义样式：

```typescript
// 修改节点颜色
node.attr('fill', (d) => getNodeColor(d.type))

// 修改节点大小
node.attr('r', (d) => getNodeSize(d.weight))
```

### 添加新的交互功能

在 `graph.ts` 中添加事件监听器：

```typescript
node.on('dblclick', (event, d) => {
  // 双击节点的处理逻辑
})
```

## 注意事项

### 性能优化

- 大规模图谱（>1000节点）考虑使用 Canvas 渲染
- 使用 requestAnimationFrame 优化动画性能
- 避免频繁的 DOM 操作
- 合理设置力导向模拟的迭代次数

### 内存管理

- 销毁图谱实例时清理事件监听器
- 及时释放不再使用的 D3 选择集
- 避免内存泄漏

### 浏览器兼容性

- 确保 SVG 功能在目标浏览器中可用
- 测试不同浏览器的渲染性能
- 考虑移动端的触摸事件支持
