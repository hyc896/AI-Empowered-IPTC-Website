<template>
  <el-dialog
    v-model="visible"
    title="案例详情"
    :width="dialogWidth"
    :before-close="handleClose"
    append-to-body
  >
    <div v-if="caseItem" class="case-detail">
      <div class="detail-header">
        <h2 class="detail-title">{{ caseItem.title }}</h2>
        <div class="detail-meta">
          <span class="meta-item">
            <el-icon><Clock /></el-icon>
            {{ formatDate(caseItem.published_at) }}
          </span>
          <span class="meta-item">
            <el-icon><Link /></el-icon>
            <a :href="caseItem.source_url" target="_blank">原文链接</a>
          </span>
        </div>
      </div>

      <el-divider />

      <div class="detail-body">
        <MarkdownRenderer :content="caseItem.content" />
      </div>

      <div v-if="caseItem.related_knowledge_points.length > 0" class="detail-sidebar">
        <h4 class="sidebar-title">关联知识点</h4>
        <div class="knowledge-points">
          <KnowledgeTag
            v-for="kp in caseItem.related_knowledge_points"
            :key="kp.id"
            :name="kp.name"
            @click="handleKnowledgePointClick(kp)"
          />
        </div>
      </div>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Clock, Link } from '@element-plus/icons-vue'
import MarkdownRenderer from '@/components/common/MarkdownRenderer.vue'
import KnowledgeTag from '@/components/case/KnowledgeTag.vue'
import { formatDate } from '@/utils/date'
import type { CaseItem } from '@/types/case'

const props = defineProps<{
  visible: boolean
  caseItem: CaseItem | null
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
}>()

const visible = computed({
  get: () => props.visible,
  set: (value) => emit('update:visible', value)
})

const dialogWidth = computed(() => {
  return window.innerWidth > 1400 ? '80%' : '95%'
})

const handleClose = () => {
  visible.value = false
}

const handleKnowledgePointClick = (kp: any) => {
  console.log('Knowledge point clicked:', kp)
}
</script>

<style scoped lang="scss">
.case-detail {
  .detail-header {
    .detail-title {
      font-size: 32px;
      font-weight: 600;
      color: #1f2937;
      margin: 0 0 16px;
      line-height: 1.3;
    }

    .detail-meta {
      display: flex;
      gap: 24px;
      color: #6b7280;
      font-size: 14px;

      .meta-item {
        display: flex;
        align-items: center;
        gap: 6px;

        a {
          color: #3b82f6;
          text-decoration: none;

          &:hover {
            text-decoration: underline;
          }
        }
      }
    }
  }

  .detail-body {
    padding: 24px 0;
    line-height: 1.8;
  }

  .detail-sidebar {
    margin-top: 32px;
    padding: 20px;
    background: #f9fafb;
    border-radius: 12px;

    .sidebar-title {
      font-size: 18px;
      font-weight: 600;
      margin: 0 0 16px;
      color: #1f2937;
    }

    .knowledge-points {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
    }
  }
}
</style>
