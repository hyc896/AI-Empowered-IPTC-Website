<!--
  文本预览组件
  显示提取的 PDF 文本内容
-->
<template>
  <el-card class="preview-card">
    <template #header>
      <div class="card-header">
        <span>文本预览</span>
        <el-tag v-if="charCount > 0" type="info">
          {{ charCount }} 字符
        </el-tag>
      </div>
    </template>

    <div v-if="text" class="text-content">
      <el-scrollbar height="400px">
        <pre>{{ text }}</pre>
      </el-scrollbar>
    </div>

    <el-empty v-else description="暂无文本内容" />
  </el-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  text: string
  charCount?: number
}>()

const charCount = computed(() => props.charCount || props.text.length)
</script>

<style scoped>
.preview-card {
  height: 100%;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.text-content pre {
  white-space: pre-wrap;
  word-wrap: break-word;
  font-family: 'Courier New', monospace;
  font-size: 14px;
  line-height: 1.6;
  margin: 0;
  padding: 10px;
}
</style>
