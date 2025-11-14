<template>
  <el-card class="message-source-card">
    <template #header>
      <div class="card-header">
        <div class="header-left">
          <span class="source-name">{{ source.name }}</span>
        </div>
        <el-switch
          :model-value="source.is_active"
          @change="handleToggle"
          @click.stop
        />
      </div>
    </template>
    <div class="card-body">
      <div class="source-info">
        <div class="info-item">
          <span class="label">适配器:</span>
          <span class="value">{{ source.adapter_name }}</span>
        </div>
        <div v-if="source.schedule" class="info-item">
          <span class="label">计划:</span>
          <span class="value">{{ parseCron(source.schedule) }}</span>
        </div>
        <div v-if="source.last_crawled_at" class="info-item">
          <span class="label">最后采集:</span>
          <span class="value">{{ formatRelativeTime(source.last_crawled_at) }}</span>
        </div>
      </div>
      <div class="card-actions">
        <el-button
          :icon="Edit"
          size="small"
          @click="handleEdit"
        >
          编辑
        </el-button>
        <el-button
          :icon="Delete"
          size="small"
          type="danger"
          @click="handleDelete"
        >
          删除
        </el-button>
      </div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { Edit, Delete } from '@element-plus/icons-vue'
import { ElMessageBox } from 'element-plus'
import type { MessageSource } from '@/types/models'
import { formatRelativeTime } from '@/utils/date'
import { parseCron } from '@/utils/format'

const props = defineProps<{
  source: MessageSource
}>()

const emit = defineEmits<{
  (e: 'edit', source: MessageSource): void
  (e: 'delete', sourceId: string): void
  (e: 'toggle', sourceId: string, isActive: boolean): void
}>()

const handleEdit = () => {
  emit('edit', props.source)
}

const handleDelete = async () => {
  try {
    await ElMessageBox.confirm('确定删除该消息源吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    emit('delete', props.source.id)
  } catch (error) {
    console.log('Cancel delete')
  }
}

const handleToggle = (value: boolean) => {
  emit('toggle', props.source.id, value)
}
</script>

<style scoped lang="scss">
.message-source-card {
  .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;

    .header-left {
      display: flex;
      align-items: center;
      gap: 8px;

      .source-name {
        font-size: 16px;
        font-weight: 600;
        color: var(--text-primary);
      }
    }
  }

  .card-body {
    .source-info {
      margin-bottom: 16px;

      .info-item {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 8px;

        .label {
          font-size: 13px;
          color: var(--text-secondary);
        }

        .value {
          font-size: 13px;
          color: var(--text-regular);
        }
      }
    }

    .card-actions {
      display: flex;
      gap: 8px;
    }
  }
}
</style>
