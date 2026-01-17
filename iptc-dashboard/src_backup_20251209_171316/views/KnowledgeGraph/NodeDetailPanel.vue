<template>
  <el-drawer
    v-model="visible"
    title="节点详情"
    direction="rtl"
    size="300px"
  >
    <div v-if="node" class="node-detail">
      <div class="node-header">
        <el-tag :type="node.type === 'knowledge_point' ? 'primary' : 'warning'">
          {{ node.type === 'knowledge_point' ? '知识点' : '案例' }}
        </el-tag>
        <h3 class="node-label">{{ node.label }}</h3>
      </div>

      <el-divider />

      <div v-if="node.meta" class="node-meta">
        <div v-if="node.meta.chapter" class="meta-item">
          <span class="meta-label">章节</span>
          <span class="meta-value">{{ node.meta.chapter }}</span>
        </div>

        <div v-if="node.meta.summary" class="meta-item">
          <span class="meta-label">摘要</span>
          <p class="meta-value">{{ node.meta.summary }}</p>
        </div>
      </div>
    </div>
  </el-drawer>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { GraphNode } from '@/types/graph'

const props = defineProps<{
  visible: boolean
  node: GraphNode | null
}>()

const emit = defineEmits<{
  close: []
}>()

const visible = computed({
  get: () => props.visible,
  set: () => emit('close')
})
</script>

<style scoped lang="scss">
.node-detail {
  .node-header {
    .node-label {
      margin-top: 16px;
      font-size: 20px;
      font-weight: 600;
      color: #1f2937;
    }
  }

  .node-meta {
    .meta-item {
      margin-bottom: 20px;

      .meta-label {
        display: block;
        font-size: 14px;
        font-weight: 600;
        color: #6b7280;
        margin-bottom: 8px;
      }

      .meta-value {
        font-size: 14px;
        color: #1f2937;
        line-height: 1.6;
      }
    }
  }
}
</style>
