<template>
  <div class="empty-state">
    <div class="empty-icon" :class="{ 'is-animating': animate }">
      <el-icon :size="iconSize">
        <component :is="icon" />
      </el-icon>
    </div>
    <h3 class="empty-title">{{ title }}</h3>
    <p class="empty-message">{{ message }}</p>
    <slot name="action"></slot>
  </div>
</template>

<script setup lang="ts">
import { Document, Box, Search, Folder } from '@element-plus/icons-vue'

withDefaults(defineProps<{
  title?: string
  message?: string
  icon?: any
  iconSize?: number
  animate?: boolean
}>(), {
  title: '暂无数据',
  message: '暂时没有找到相关内容',
  icon: Document,
  iconSize: 80,
  animate: true
})
</script>

<style scoped lang="scss">
.empty-state {
  text-align: center;
  padding: 80px 20px;
  color: #9ca3af;

  .empty-icon {
    opacity: 0.3;
    margin-bottom: 24px;
    display: inline-block;

    &.is-animating {
      animation: float 3s ease-in-out infinite;
    }
  }

  .empty-title {
    font-size: 20px;
    font-weight: 500;
    color: #6b7280;
    margin: 0 0 12px 0;
  }

  .empty-message {
    font-size: 14px;
    color: #9ca3af;
    margin: 0 0 24px 0;
  }

  @keyframes float {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-10px); }
  }
}
</style>
