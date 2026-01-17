<template>
  <div class="search-bar">
    <el-input
      v-model="keyword"
      placeholder="搜索案例..."
      size="large"
      clearable
      @keyup.enter="handleSearch"
    >
      <template #prefix>
        <el-icon><Search /></el-icon>
      </template>
      <template #append>
        <el-button @click="handleSearch">
          <el-icon><Search /></el-icon>
          搜索
        </el-button>
      </template>
    </el-input>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Search } from '@element-plus/icons-vue'

const keyword = ref('')

const emit = defineEmits<{
  search: [keyword: string]
}>()

const handleSearch = () => {
  emit('search', keyword.value)
}
</script>

<style scoped lang="scss">
.search-bar {
  width: 100%;
  max-width: 600px;
}
</style>
