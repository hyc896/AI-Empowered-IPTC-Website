<!--
  G6 图谱可视化组件
  使用 AntV G6 渲染知识图谱
-->
<template>
  <div class="graph-viewer">
    <div class="graph-toolbar">
      <el-space>
        <el-button @click="handleZoomIn">
          <el-icon><ZoomIn /></el-icon>
          放大
        </el-button>
        <el-button @click="handleZoomOut">
          <el-icon><ZoomOut /></el-icon>
          缩小
        </el-button>
        <el-button @click="handleFitView">
          <el-icon><FullScreen /></el-icon>
          适应画布
        </el-button>
        <el-button @click="handleRefresh">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </el-space>
    </div>
    <div ref="containerRef" class="graph-container"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, toRaw } from 'vue'
import { Graph } from '@antv/g6'
import { ZoomIn, ZoomOut, FullScreen, Refresh } from '@element-plus/icons-vue'
import type { G6GraphData } from '@/types/graph'

const props = defineProps<{
  data: G6GraphData
}>()

const containerRef = ref<HTMLDivElement>()
let graph: Graph | null = null

// 实体类型颜色映射
const entityColors: Record<string, string> = {
  Company: '#5B8FF9',
  Person: '#5AD8A6',
  Technology: '#5D7092',
  Product: '#F6BD16',
  Organization: '#6F5EF9',
  Event: '#6DC8EC',
  Concept: '#945FB9',
  Location: '#FF9845'
}

onMounted(() => {
  initGraph()
})

onUnmounted(() => {
  if (graph) {
    graph.destroy()
  }
})

watch(() => props.data, (newData) => {
  if (graph && newData) {
    updateGraph(newData)
  }
}, { deep: true })

const initGraph = () => {
  if (!containerRef.value) return

  graph = new Graph({
    container: containerRef.value,
    width: containerRef.value.offsetWidth,
    height: containerRef.value.offsetHeight,
    layout: {
      type: 'force',
      preventOverlap: true,
      nodeSpacing: 50
    },
    modes: {
      default: ['drag-canvas', 'zoom-canvas', 'drag-node']
    },
    node: {
      style: {
        size: 40,
        lineWidth: 2,
        fill: '#5B8FF9',
        stroke: '#fff'
      },
      labelText: (d: any) => d.id,
      labelFontSize: 12,
      labelFill: '#000'
    },
    edge: {
      style: {
        stroke: '#e2e2e2',
        lineWidth: 2
      },
      labelText: (d: any) => d.label,
      labelFontSize: 10,
      labelFill: '#666'
    }
  })

  if (props.data) {
    updateGraph(props.data)
  }
}

const updateGraph = async (data: G6GraphData) => {
  if (!graph) return

  const processedData = {
    nodes: data.nodes.map(node => ({
      id: node.id,
      data: {
        ...node,
        fill: entityColors[node.type] || '#5B8FF9'
      }
    })),
    edges: data.edges.map(edge => ({
      id: `${edge.source}-${edge.target}`,
      source: edge.source,
      target: edge.target,
      data: edge
    }))
  }

  graph.setData(toRaw(processedData))
  await graph.render()
  graph.fitView()
}

const handleZoomIn = () => {
  graph?.zoom(1.2)
}

const handleZoomOut = () => {
  graph?.zoom(0.8)
}

const handleFitView = () => {
  graph?.fitView()
}

const handleRefresh = () => {
  if (props.data) {
    updateGraph(props.data)
  }
}
</script>

<style scoped>
.graph-viewer {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.graph-toolbar {
  padding: 12px;
  border-bottom: 1px solid #e8e8e8;
}

.graph-container {
  flex: 1;
  position: relative;
}
</style>
