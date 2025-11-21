<template>
  <el-card class="message-card" @click="handleView">
    <div class="message-header">
      <h4 class="message-title">{{ message.title }}</h4>
      <div class="message-meta">
        <span v-if="message.author" class="message-author">{{ message.author }}</span>
        <span v-if="message.published_at" class="message-time">
          {{ formatDateShort(message.published_at) }}
        </span>
      </div>
    </div>
    <div class="message-body">
      <p v-if="message.summary" class="message-summary">{{ truncateText(message.summary, 150) }}</p>
      <p v-else class="message-content">{{ truncateText(message.content, 150) }}</p>
    </div>
    <div v-if="message.url" class="message-footer">
      <el-link :href="message.url" target="_blank" :icon="Link" @click.stop>
        查看原文
      </el-link>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { Link } from '@element-plus/icons-vue'
import type { Message } from '@/types/models'
import { formatDateShort } from '@/utils/date'
import { truncateText } from '@/utils/format'

const props = defineProps<{
  message: Message
}>()

const emit = defineEmits<{
  (e: 'view', message: Message): void
}>()

const handleView = () => {
  emit('view', props.message)
}
</script>

<style scoped lang="scss">
.message-card {
  cursor: pointer;
  transition: all 0.3s;

  &:hover {
    box-shadow: var(--box-shadow);
    transform: translateY(-2px);
  }

  .message-header {
    margin-bottom: 12px;

    .message-title {
      font-size: 16px;
      font-weight: 600;
      color: var(--text-primary);
      margin-bottom: 8px;
      line-height: 1.4;
    }

    .message-meta {
      display: flex;
      align-items: center;
      gap: 12px;
      font-size: 12px;
      color: var(--text-secondary);

      .message-author {
      }

      .message-time {
      }
    }
  }

  .message-body {
    margin-bottom: 12px;

    .message-summary,
    .message-content {
      font-size: 14px;
      color: var(--text-regular);
      line-height: 1.6;
    }
  }

  .message-footer {
    display: flex;
    justify-content: flex-end;
  }
}
</style>
