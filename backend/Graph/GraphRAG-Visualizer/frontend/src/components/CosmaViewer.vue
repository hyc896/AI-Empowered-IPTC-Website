/**
 * Cosma 可视化组件
 * 封装 Cosma 图谱渲染逻辑，提供 Vue 组件接口
 */

<template>
  <div class="cosma-viewer">
    <div ref="graphContainer" class="graph-container"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue';
import { initGraph } from '@/cosma/graph';
import { convertRecordsToGraph } from '@/utils/cosmaConverter';
import type { CosmaRecord } from '@/types/cosma';
import type { GraphInstance } from '@/cosma/graph';

const props = defineProps<{
  records: CosmaRecord[];
}>();

const emit = defineEmits<{
  nodeClick: [record: CosmaRecord];
}>();

const graphContainer = ref<HTMLElement>();
let graphInstance: GraphInstance | null = null;

onMounted(() => {
  if (graphContainer.value) {
    graphInstance = initGraph(graphContainer.value, (nodeId: string) => {
      const record = props.records.find(r => r.id === nodeId);
      if (record) {
        emit('nodeClick', record);
      }
    });
    loadData();
  }
});

watch(() => props.records, () => {
  loadData();
}, { deep: true });

function loadData() {
  if (graphInstance && props.records && props.records.length > 0) {
    const graphData = convertRecordsToGraph(props.records);
    graphInstance.loadData(graphData);
  }
}

onUnmounted(() => {
  graphInstance?.destroy();
});
</script>

<style scoped>
.cosma-viewer {
  width: 100%;
  height: 100%;
  overflow: hidden;
}

.graph-container {
  width: 100%;
  height: 100%;
  background: #fafafa;
}
</style>
