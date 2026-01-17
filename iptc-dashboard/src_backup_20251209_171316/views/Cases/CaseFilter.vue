<template>
  <div class="case-filter">
    <div class="filter-group">
      <label class="filter-label">知识点筛选</label>
      <el-select
        v-model="selectedKnowledgePoint"
        placeholder="选择知识点"
        clearable
        @change="handleFilterChange"
      >
        <el-option label="全部" value="" />
        <el-option
          v-for="kp in knowledgePoints"
          :key="kp.id"
          :label="kp.name"
          :value="kp.id"
        />
      </el-select>
    </div>

    <div class="filter-group">
      <label class="filter-label">排序方式</label>
      <el-select
        v-model="selectedSort"
        @change="handleFilterChange"
      >
        <el-option label="最新发布" value="latest" />
        <el-option label="最受欢迎" value="popular" />
      </el-select>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const selectedKnowledgePoint = ref('')
const selectedSort = ref<'latest' | 'popular'>('latest')

const knowledgePoints = ref([
  { id: '1', name: '以人民为中心' },
  { id: '2', name: '中国特色社会主义' },
  { id: '3', name: '马克思主义基本原理' },
  { id: '4', name: '改革开放' },
  { id: '5', name: '共同富裕' }
])

const emit = defineEmits<{
  filter: [filters: { knowledge_point_id: string; sort: 'latest' | 'popular' }]
}>()

const handleFilterChange = () => {
  emit('filter', {
    knowledge_point_id: selectedKnowledgePoint.value,
    sort: selectedSort.value
  })
}
</script>

<style scoped lang="scss">
.case-filter {
  display: flex;
  gap: 24px;
  padding: 20px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);

  .filter-group {
    display: flex;
    align-items: center;
    gap: 12px;

    .filter-label {
      font-size: 14px;
      font-weight: 500;
      color: #374151;
      white-space: nowrap;
    }

    .el-select {
      width: 200px;
    }
  }
}
</style>
