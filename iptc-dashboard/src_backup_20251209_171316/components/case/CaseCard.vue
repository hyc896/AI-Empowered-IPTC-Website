<template>
  <div class="case-card" @click="handleClick">
    <div class="card-header" :style="{ background: gradientBg }">
      <el-tag class="kp-tag" effect="plain">{{ primaryKnowledgePoint }}</el-tag>
      <span class="time">{{ formattedTime }}</span>
    </div>

    <div class="card-body">
      <h3 class="title">{{ caseItem.title }}</h3>

      <p class="summary">{{ caseItem.summary }}</p>

      <div class="footer">
        <div class="tags">
          <el-tag
            v-for="tag in caseItem.tags?.slice(0, 3)"
            :key="tag"
            size="small"
            type="info"
            class="tag-item"
          >
            {{ tag }}
          </el-tag>
        </div>
        <el-button
          type="primary"
          text
          @click.stop="handleDetail"
          class="detail-btn"
        >
          查看详情
          <el-icon class="ml-1"><ArrowRight /></el-icon>
        </el-button>
      </div>
    </div>

    <!-- 悬停效果遮罩 -->
    <div class="hover-overlay"></div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ArrowRight } from '@element-plus/icons-vue'
import type { CaseItem } from '@/types/case'
import { formatRelativeTime } from '@/utils/date'

const props = defineProps<{
  caseItem: CaseItem
}>()

const emit = defineEmits<{
  click: []
  detail: []
}>()

const primaryKnowledgePoint = computed(() => {
  return props.caseItem.related_knowledge_points?.[0]?.name || '未分类'
})

const gradientBg = computed(() => {
  const colors = [
    'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
    'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
    'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
    'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
    'linear-gradient(135deg, #30cfd0 0%, #330867 100%)',
    'linear-gradient(135deg, #a8edea 0%, #fed6e3 100%)',
    'linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%)'
  ]
  const index = Math.abs(props.caseItem.id.charCodeAt(0)) % colors.length
  return colors[index]
})

const formattedTime = computed(() => {
  return formatRelativeTime(props.caseItem.published_at)
})

const handleClick = () => {
  emit('click')
}

const handleDetail = () => {
  emit('detail')
}
</script>

<style scoped lang="scss">
.case-card {
  background: #fff;
  border-radius: 16px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  position: relative;

  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: linear-gradient(135deg, rgba(59, 130, 246, 0.1) 0%, transparent 100%);
    opacity: 0;
    transition: opacity 0.4s ease;
    pointer-events: none;
  }

  &:hover {
    transform: translateY(-12px) scale(1.02);
    box-shadow: 0 20px 50px rgba(0, 0, 0, 0.15);

    &::before {
      opacity: 1;
    }

    .card-header {
      background-size: 120%;
    }

    .hover-overlay {
      opacity: 1;
    }

    .detail-btn {
      transform: translateX(5px);
    }

    .tag-item {
      transform: translateY(-2px);
    }
  }

  .card-header {
    padding: 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    background-size: 100%;
    transition: background-size 0.6s ease;
    position: relative;
    z-index: 1;

    .kp-tag {
      background: rgba(255, 255, 255, 0.95);
      border: none;
      font-weight: 500;
      backdrop-filter: blur(8px);
    }

    .time {
      color: rgba(255, 255, 255, 0.95);
      font-size: 13px;
      font-weight: 500;
      text-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
    }
  }

  .card-body {
    padding: 20px;
    position: relative;
    z-index: 1;
  }

  .title {
    margin: 0 0 16px 0;
    font-size: 20px;
    font-weight: 600;
    line-height: 1.4;
    color: #1f2937;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    transition: color 0.3s ease;
  }

  &:hover .title {
    color: #3b82f6;
  }

  .summary {
    margin: 0 0 16px 0;
    font-size: 14px;
    line-height: 1.6;
    color: #6b7280;
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  .footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 16px;

    .tags {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      flex: 1;

      .tag-item {
        transition: all 0.3s ease;
      }
    }

    .detail-btn {
      transition: all 0.3s ease;
      font-weight: 500;

      .ml-1 {
        margin-left: 4px;
      }
    }
  }

  .hover-overlay {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: linear-gradient(180deg, transparent 0%, rgba(0, 0, 0, 0.02) 100%);
    opacity: 0;
    transition: opacity 0.4s ease;
    pointer-events: none;
    z-index: 0;
  }
}
</style>
