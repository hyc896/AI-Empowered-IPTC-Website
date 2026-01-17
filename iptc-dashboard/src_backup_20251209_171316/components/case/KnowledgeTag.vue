<template>
  <el-tag :type="tagType" :effect="effect" class="knowledge-tag">
    {{ name }}
  </el-tag>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  name: string
  type?: 'primary' | 'success' | 'info' | 'warning' | 'danger'
  effect?: 'dark' | 'light' | 'plain'
}>(), {
  type: 'primary',
  effect: 'light'
})

const tagType = computed(() => props.type)
</script>

<style scoped lang="scss">
.knowledge-tag {
  font-size: 13px;
  padding: 4px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    transform: scale(1.05);
  }
}
</style>
