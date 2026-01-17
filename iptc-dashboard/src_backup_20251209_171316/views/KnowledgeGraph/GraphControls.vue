<template>
  <div class="graph-controls">
    <el-button-group>
      <el-button @click="handleReset">
        <el-icon><RefreshRight /></el-icon>
        重置视图
      </el-button>
      <el-button @click="handleExport">
        <el-icon><Download /></el-icon>
        导出PNG
      </el-button>
    </el-button-group>
  </div>
</template>

<script setup lang="ts">
import { RefreshRight, Download } from '@element-plus/icons-vue'

const emit = defineEmits<{
  reset: []
  export: []
}>()

const handleReset = () => {
  emit('reset')
}

const handleExport = () => {
  emit('export')
}
</script>

<style scoped lang="scss">
.graph-controls {
  display: flex;
  gap: 12px;
}
</style>
