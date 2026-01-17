<template>
  <div class="cases-page">
    <div class="page-header">
      <h2 class="page-title">案例库</h2>
      <div class="page-actions">
        <SearchBar @search="handleSearch" />
      </div>
    </div>

    <CaseFilter @filter="handleFilter" />

    <el-divider />

    <CaseList
      :cases="cases"
      :loading="loading"
      :total="total"
      :page="currentPage"
      :page-size="pageSize"
      @page-change="handlePageChange"
      @size-change="handleSizeChange"
      @case-click="handleCaseClick"
      @reset="handleReset"
    />

    <CaseDetail
      v-model:visible="detailVisible"
      :case-item="selectedCase"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useCaseStore } from '@/stores/case'
import { storeToRefs } from 'pinia'
import SearchBar from '@/components/common/SearchBar.vue'
import CaseFilter from './CaseFilter.vue'
import CaseList from './CaseList.vue'
import CaseDetail from './CaseDetail.vue'
import type { CaseItem } from '@/types/case'

const caseStore = useCaseStore()
const { cases, total, loading } = storeToRefs(caseStore)

const currentPage = ref(1)
const pageSize = ref(12)
const detailVisible = ref(false)
const selectedCase = ref<CaseItem | null>(null)
const filters = ref({
  keyword: '',
  knowledge_point_id: '',
  sort: 'latest' as 'latest' | 'popular'
})

const loadCases = async () => {
  await caseStore.fetchCases({
    page: currentPage.value,
    size: pageSize.value,
    ...filters.value
  })
}

const handleSearch = (keyword: string) => {
  filters.value.keyword = keyword
  currentPage.value = 1
  loadCases()
}

const handleFilter = (newFilters: any) => {
  filters.value = { ...filters.value, ...newFilters }
  currentPage.value = 1
  loadCases()
}

const handlePageChange = (page: number) => {
  currentPage.value = page
  loadCases()
}

const handleCaseClick = (caseItem: CaseItem) => {
  selectedCase.value = caseItem
  detailVisible.value = true
}

const handleSizeChange = (size: number) => {
  pageSize.value = size
  currentPage.value = 1
  loadCases()
}

const handleReset = () => {
  filters.value = {
    keyword: '',
    knowledge_point_id: '',
    sort: 'latest'
  }
  currentPage.value = 1
  loadCases()
}

onMounted(() => {
  loadCases()
})
</script>

<style scoped lang="scss">
.cases-page {
  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;

    .page-title {
      font-size: 28px;
      font-weight: 600;
      color: #1f2937;
      margin: 0;
    }
  }
}
</style>
