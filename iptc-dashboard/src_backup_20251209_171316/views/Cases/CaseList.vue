<template>
  <div class="case-list">
    <!-- 骨架屏加载状态 -->
    <div v-if="loading" class="skeleton-grid">
      <SkeletonCard v-for="i in pageSize" :key="i" />
    </div>

    <!-- 空状态 -->
    <EmptyState
      v-else-if="!loading && cases.length === 0"
      title="暂无案例"
      message="未找到符合条件的案例，请尝试调整筛选条件"
      :icon="Document"
    >
      <template #action>
        <el-button type="primary" @click="handleReset">
          重置筛选
        </el-button>
      </template>
    </EmptyState>

    <!-- 案例网格 -->
    <div v-else class="cases-grid">
      <transition-group name="list">
        <CaseCard
          v-for="caseItem in cases"
          :key="caseItem.id"
          :case-item="caseItem"
          @click="$emit('case-click', caseItem)"
          @detail="$emit('case-click', caseItem)"
        />
      </transition-group>
    </div>

    <!-- 分页 -->
    <div v-if="!loading && cases.length > 0" class="pagination-wrapper">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="currentPageSize"
        :total="total"
        :page-sizes="[12, 24, 36, 48]"
        layout="total, sizes, prev, pager, next, jumper"
        background
        @current-change="handlePageChange"
        @size-change="handleSizeChange"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { Document } from '@element-plus/icons-vue'
import CaseCard from '@/components/case/CaseCard.vue'
import SkeletonCard from '@/components/common/SkeletonCard.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import type { CaseItem } from '@/types/case'

const props = defineProps<{
  cases: CaseItem[]
  loading: boolean
  total: number
  page: number
  pageSize: number
}>()

const emit = defineEmits<{
  'case-click': [caseItem: CaseItem]
  'page-change': [page: number]
  'size-change': [size: number]
  reset: []
}>()

const currentPage = ref(props.page)
const currentPageSize = ref(props.pageSize)

watch(() => props.page, (newPage) => {
  currentPage.value = newPage
})

watch(() => props.pageSize, (newSize) => {
  currentPageSize.value = newSize
})

const handlePageChange = (page: number) => {
  emit('page-change', page)
  // 滚动到顶部
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

const handleSizeChange = (size: number) => {
  emit('size-change', size)
}

const handleReset = () => {
  emit('reset')
}
</script>

<style scoped lang="scss">
.case-list {
  .skeleton-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
    gap: 24px;
    margin-bottom: 32px;
  }

  .cases-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
    gap: 24px;
    margin-bottom: 32px;

    @media (max-width: 1200px) {
      grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    }

    @media (max-width: 768px) {
      grid-template-columns: 1fr;
    }
  }

  .pagination-wrapper {
    display: flex;
    justify-content: center;
    padding: 32px 0;
  }

  // 列表过渡动画
  .list-enter-active {
    transition: all 0.5s ease;
  }

  .list-leave-active {
    transition: all 0.3s ease;
  }

  .list-enter-from {
    opacity: 0;
    transform: translateY(30px);
  }

  .list-leave-to {
    opacity: 0;
    transform: translateY(-30px);
  }

  .list-move {
    transition: transform 0.5s ease;
  }
}
</style>
