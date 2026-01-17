<template>
  <div class="graph-view">
    <div class="graph-container">
      <!-- 控制面板 -->
      <div class="control-panel">
        <h3 class="panel-title">控制面板</h3>

        <!-- 工具栏 -->
        <div class="toolbar">
          <base-button size="small" @click="fitView">
            适应画布
          </base-button>
          <base-button size="small" @click="resetZoom">
            重置缩放
          </base-button>
          <base-button size="small" @click="exportImage">
            导出图片
          </base-button>
        </div>

        <!-- 布局切换 -->
        <div class="layout-switch">
          <h4 class="section-title">布局方式</h4>
          <select v-model="layoutType" @change="handleLayoutChange" class="layout-select">
            <option value="force">力导向布局</option>
            <option value="circular">环形布局</option>
            <option value="radial">辐射布局</option>
            <option value="dagre">层次布局</option>
          </select>
        </div>

        <!-- 节点筛选 -->
        <div class="node-filter">
          <h4 class="section-title">节点筛选</h4>
          <div class="filter-buttons">
            <base-button
              size="small"
              :type="graphStore.filterNodeType === 'all' ? 'primary' : 'outline'"
              @click="filterNodes('all')"
            >
              全部
            </base-button>
            <base-button
              size="small"
              :type="graphStore.filterNodeType === 'case' ? 'primary' : 'outline'"
              @click="filterNodes('case')"
            >
              案例
            </base-button>
            <base-button
              size="small"
              :type="graphStore.filterNodeType === 'knowledge' ? 'primary' : 'outline'"
              @click="filterNodes('knowledge')"
            >
              知识点
            </base-button>
          </div>
        </div>

        <!-- 节点详情 -->
        <div v-if="graphStore.selectedNode" class="node-detail">
          <h4 class="section-title">节点详情</h4>
          <div class="detail-content">
            <base-tag :type="graphStore.selectedNode.type === 'case' ? 'secondary' : 'accent'">
              {{ graphStore.selectedNode.type === 'case' ? '案例' : '知识点' }}
            </base-tag>
            <h5 class="node-title">{{ graphStore.selectedNode.label }}</h5>
            <p v-if="graphStore.selectedNode.data" class="node-description">
              {{ getNodeDescription(graphStore.selectedNode) }}
            </p>
            <base-button
              v-if="graphStore.selectedNode.type === 'case'"
              size="small"
              @click="navigateToCase(graphStore.selectedNode.id)"
            >
              查看详情
            </base-button>
          </div>
        </div>

        <!-- 图谱统计 -->
        <div class="graph-stats">
          <h4 class="section-title">图谱统计</h4>
          <div class="stats-grid">
            <div class="stat-item">
              <span class="stat-label">节点总数</span>
              <span class="stat-value">{{ graphStore.nodeCount }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">连接数</span>
              <span class="stat-value">{{ graphStore.edgeCount }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">案例节点</span>
              <span class="stat-value">{{ graphStore.caseNodeCount }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">知识点节点</span>
              <span class="stat-value">{{ graphStore.knowledgeNodeCount }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 图谱画布 -->
      <div class="graph-canvas-wrapper">
        <div v-if="graphStore.loading" class="loading-overlay">
          <div class="loading-spinner"></div>
          <p>加载图谱数据中...</p>
        </div>
        <div ref="graphContainer" class="graph-canvas"></div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, computed } from 'vue';
import { useRouter } from 'vue-router';
import { useGraphStore } from '@/stores';
import { useGraph } from '@/composables';
import type { GraphNode, GraphLayoutConfig } from '@/types';
import BaseButton from '@/components/ui/BaseButton.vue';
import BaseTag from '@/components/ui/BaseTag.vue';

const router = useRouter();
const graphStore = useGraphStore();
const graphContainer = ref<HTMLElement | null>(null);

const layoutType = ref<'force' | 'circular' | 'radial' | 'dagre'>('force');

// 初始化图谱
const {
  fitView: graphFitView,
  resetZoom: graphResetZoom,
  exportImage: graphExportImage,
  updateLayout,
  updateData,
} = useGraph({
  container: graphContainer,
  data: computed(() => graphStore.filteredGraphData),
  layoutConfig: computed(() => graphStore.layoutConfig),
  onNodeClick: (node: GraphNode) => {
    graphStore.selectNode(node);
  },
});

onMounted(async () => {
  await graphStore.fetchGraphData();
});

// 监听图谱数据变化
watch(
  () => graphStore.filteredGraphData,
  (newData) => {
    if (newData.nodes.length > 0) {
      updateData(newData);
    }
  }
);

const handleLayoutChange = () => {
  const newConfig: GraphLayoutConfig = {
    type: layoutType.value,
    preventOverlap: true,
    nodeSpacing: 50,
    linkDistance: 150,
  };
  graphStore.updateLayoutConfig(newConfig);
  updateLayout(newConfig);
};

const filterNodes = (type: 'all' | 'case' | 'knowledge') => {
  graphStore.updateNodeFilter(type);
};

const fitView = () => {
  graphFitView();
};

const resetZoom = () => {
  graphResetZoom();
};

const exportImage = () => {
  graphExportImage('knowledge-graph');
};

const getNodeDescription = (node: GraphNode): string => {
  if (!node.data) return '';
  if (node.type === 'case') {
    return (node.data as any).summary || '';
  } else {
    return (node.data as any).description || '';
  }
};

const navigateToCase = (caseId: string) => {
  router.push(`/cases/${caseId}`);
};
</script>

<style scoped>
.graph-view {
  height: calc(100vh - var(--header-height));
  overflow: hidden;
}

.graph-container {
  display: flex;
  height: 100%;
}

.control-panel {
  width: 300px;
  background: var(--bg-primary);
  border-right: 1px solid var(--border-color);
  padding: var(--spacing-xl);
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xl);
}

.panel-title {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-bold);
  color: var(--text-primary);
}

.section-title {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
  margin-bottom: var(--spacing-md);
}

.toolbar {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.layout-select {
  width: 100%;
  padding: var(--spacing-sm) var(--spacing-md);
  border: 2px solid var(--border-color);
  border-radius: var(--border-radius-md);
  font-size: var(--font-size-sm);
  cursor: pointer;
  transition: border-color var(--transition-fast);
}

.layout-select:focus {
  outline: none;
  border-color: var(--color-primary);
}

.filter-buttons {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.node-detail {
  padding: var(--spacing-lg);
  background: var(--bg-secondary);
  border-radius: var(--border-radius-md);
  border-left: 4px solid var(--color-primary);
}

.detail-content {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.node-title {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
}

.node-description {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  line-height: var(--line-height-relaxed);
}

.graph-stats {
  padding: var(--spacing-lg);
  background: linear-gradient(135deg, rgba(208, 48, 80, 0.05) 0%, rgba(196, 30, 58, 0.05) 100%);
  border-radius: var(--border-radius-md);
  border: 1px solid rgba(208, 48, 80, 0.1);
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--spacing-md);
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.stat-label {
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
}

.stat-value {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-primary);
}

.graph-canvas-wrapper {
  flex: 1;
  position: relative;
  background: #2c3e50;
}

.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-lg);
  background: rgba(255, 255, 255, 0.9);
  z-index: 10;
}

.graph-canvas {
  width: 100%;
  height: 100%;
}

@media (max-width: 768px) {
  .graph-container {
    flex-direction: column;
  }

  .control-panel {
    width: 100%;
    max-height: 300px;
    border-right: none;
    border-bottom: 1px solid var(--border-color);
  }
}
</style>
