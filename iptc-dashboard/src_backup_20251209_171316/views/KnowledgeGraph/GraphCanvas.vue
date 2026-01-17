<template>
  <div ref="containerRef" class="graph-canvas">
    <el-skeleton v-if="loading" :rows="10" animated />
    <el-empty v-else-if="!graphData || graphData.nodes.length === 0" description="暂无图谱数据" />
    <div v-else ref="graphRef" class="graph-content"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, nextTick } from 'vue'
import G6 from '@antv/g6'
import type { GraphData, GraphNode } from '@/types/graph'

const props = defineProps<{
  graphData: GraphData
  loading: boolean
}>()

const emit = defineEmits<{
  'node-click': [node: GraphNode]
}>()

const containerRef = ref<HTMLElement>()
const graphRef = ref<HTMLElement>()
let graph: any = null

const initGraph = async () => {
  await nextTick()

  if (!graphRef.value || !props.graphData.nodes.length) return

  const container = graphRef.value
  const width = container.offsetWidth
  const height = container.offsetHeight

  if (graph) {
    graph.destroy()
  }

  graph = new G6.Graph({
    container: graphRef.value,
    width,
    height,
    layout: {
      type: 'force2',
      preventOverlap: true,
      nodeSpacing: 120,
      linkDistance: 200
    },
    defaultNode: {
      type: 'circle',
      size: 80,
      style: {
        fill: '#5B8FF9',
        stroke: '#fff',
        lineWidth: 3,
        shadowColor: 'rgba(0,0,0,0.2)',
        shadowBlur: 20
      },
      labelCfg: {
        position: 'bottom',
        offset: 10,
        style: {
          fontSize: 14,
          fontWeight: 'bold',
          fill: '#333'
        }
      }
    },
    nodeStateStyles: {
      hover: {
        fill: '#FF9845',
        lineWidth: 4
      },
      active: {
        fill: '#FF9845',
        stroke: '#ff6b00'
      }
    },
    defaultEdge: {
      type: 'cubic-horizontal',
      style: {
        stroke: '#999',
        lineWidth: 2,
        opacity: 0.6,
        endArrow: {
          path: 'M 0,0 L 8,4 L 8,-4 Z',
          fill: '#999'
        }
      }
    },
    modes: {
      default: ['drag-canvas', 'zoom-canvas', 'drag-node', 'activate-relations']
    }
  })

  const formattedData = {
    nodes: props.graphData.nodes.map(node => ({
      id: node.id,
      label: node.label,
      style: {
        fill: node.type === 'knowledge_point' ? '#5B8FF9' : '#FF9845'
      }
    })),
    edges: props.graphData.edges.map(edge => ({
      source: edge.source,
      target: edge.target
    }))
  }

  graph.data(formattedData)
  graph.render()

  graph.on('node:click', (evt: any) => {
    const { item } = evt
    const nodeModel = item.getModel()
    const node = props.graphData.nodes.find(n => n.id === nodeModel.id)
    if (node) {
      emit('node-click', node)
    }
  })
}

watch(() => props.graphData, () => {
  if (!props.loading) {
    initGraph()
  }
}, { deep: true })

onMounted(() => {
  if (!props.loading && props.graphData.nodes.length > 0) {
    initGraph()
  }
})
</script>

<style scoped lang="scss">
.graph-canvas {
  width: 100%;
  height: 100%;
  position: relative;

  .graph-content {
    width: 100%;
    height: 100%;
  }
}
</style>
