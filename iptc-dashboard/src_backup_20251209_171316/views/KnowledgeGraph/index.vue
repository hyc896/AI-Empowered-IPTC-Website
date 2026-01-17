<template>
  <div class="knowledge-graph-page">
    <div class="page-header">
      <h2 class="page-title">知识图谱</h2>
      <GraphControls @reset="handleReset" @export="handleExport" />
    </div>

    <div class="graph-container">
      <GraphCanvas
        :graph-data="graphData"
        :loading="loading"
        @node-click="handleNodeClick"
      />

      <NodeDetailPanel
        :visible="detailVisible"
        :node="selectedNode"
        @close="detailVisible = false"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useGraphStore } from '@/stores/graph'
import { storeToRefs } from 'pinia'
import GraphControls from './GraphControls.vue'
import GraphCanvas from './GraphCanvas.vue'
import NodeDetailPanel from './NodeDetailPanel.vue'
import type { GraphNode } from '@/types/graph'

const graphStore = useGraphStore()
const { graphData, loading, selectedNode } = storeToRefs(graphStore)

const detailVisible = ref(false)

const handleNodeClick = (node: GraphNode) => {
  graphStore.selectNode(node)
  detailVisible.value = true
}

const handleReset = () => {
  console.log('Reset graph')
}

const handleExport = () => {
  console.log('Export graph as PNG')
}

onMounted(() => {
  graphStore.fetchFullGraph()
})
</script>

<style scoped lang="scss">
.knowledge-graph-page {
  height: calc(100vh - 160px);
  display: flex;
  flex-direction: column;

  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;

    .page-title {
      font-size: 28px;
      font-weight: 600;
      color: #1f2937;
      margin: 0;
    }
  }

  .graph-container {
    flex: 1;
    position: relative;
    background: #fff;
    border-radius: 12px;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
    overflow: hidden;
  }
}
</style>
