<template>
  <div v-if="visible" class="progress-container">
    <div class="progress-header">
      <span class="progress-title">{{ title }}</span>
      <span class="progress-percentage">{{ progress }}%</span>
    </div>

    <div class="progress-bar">
      <div
        class="progress-fill"
        :style="{ width: `${progress}%` }"
        :class="statusClass"
      ></div>
    </div>

    <div class="progress-message">{{ message }}</div>

    <div v-if="showDetails" class="progress-details">
      <span v-if="totalBlocks">块: {{ currentBlock }}/{{ totalBlocks }}</span>
      <span v-if="entitiesCount">实体: {{ entitiesCount }}</span>
      <span v-if="relationsCount">关系: {{ relationsCount }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';

interface Props {
  visible?: boolean;
  title?: string;
  progress?: number;
  status?: 'processing' | 'completed' | 'failed';
  message?: string;
  totalBlocks?: number;
  currentBlock?: number;
  entitiesCount?: number;
  relationsCount?: number;
  showDetails?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  visible: false,
  title: '处理中',
  progress: 0,
  status: 'processing',
  message: '',
  showDetails: true
});

const statusClass = computed(() => {
  return {
    'progress-processing': props.status === 'processing',
    'progress-completed': props.status === 'completed',
    'progress-failed': props.status === 'failed'
  };
});
</script>

<style scoped>
.progress-container {
  padding: 16px;
  background: #f5f5f5;
  border-radius: 8px;
  margin-bottom: 16px;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.progress-title {
  font-weight: 500;
  color: #333;
}

.progress-percentage {
  font-weight: 600;
  color: #1890ff;
}

.progress-bar {
  height: 8px;
  background: #e0e0e0;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 8px;
}

.progress-fill {
  height: 100%;
  transition: width 0.3s ease;
  border-radius: 4px;
}

.progress-processing {
  background: linear-gradient(90deg, #1890ff, #40a9ff);
}

.progress-completed {
  background: linear-gradient(90deg, #52c41a, #73d13d);
}

.progress-failed {
  background: linear-gradient(90deg, #ff4d4f, #ff7875);
}

.progress-message {
  font-size: 14px;
  color: #666;
  margin-bottom: 8px;
}

.progress-details {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: #999;
}

.progress-details span {
  display: inline-block;
}
</style>
