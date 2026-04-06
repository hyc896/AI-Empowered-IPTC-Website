<template>
  <div class="review-list">
    <div class="page-header">
      <h2>审核工作台</h2>
    </div>

    <!-- 统计卡片 -->
    <el-row :gutter="16" class="stats-row">
      <el-col :span="8">
        <el-card class="stat-card">
          <div class="stat-num" style="color:#e6a23c">{{ stats.pending }}</div>
          <div class="stat-label">待审核</div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card class="stat-card">
          <div class="stat-num" style="color:#67c23a">{{ stats.approved }}</div>
          <div class="stat-label">已通过</div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card class="stat-card">
          <div class="stat-num" style="color:#f56c6c">{{ stats.rejected }}</div>
          <div class="stat-label">未通过</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 筛选 -->
    <el-card class="filter-card">
      <el-row :gutter="16">
        <el-col :span="8">
          <el-select v-model="typeFilter" placeholder="实践类型" clearable @change="fetchList" style="width:100%">
            <el-option v-for="t in practiceTypes" :key="t.value" :label="t.label" :value="t.value" />
          </el-select>
        </el-col>
        <el-col :span="8">
          <el-input v-model="searchKeyword" placeholder="搜索学生姓名..." clearable @input="fetchList" />
        </el-col>
      </el-row>
    </el-card>

    <!-- 待审核列表 -->
    <div class="list">
      <PageLoading v-if="loading" />
      <template v-else>
      <el-empty v-if="list.length === 0" description="暂无待审核作业" />

      <el-card v-for="item in list" :key="item.id" class="review-card" shadow="hover">
        <div class="card-body">
          <div class="card-left">
            <div class="card-title">{{ item.title }}</div>
            <div class="card-meta">
              <span><el-icon><User /></el-icon> {{ item.user_name }}</span>
              <span>{{ typeLabel(item.practice_type) }}</span>
              <span>提交时间：{{ formatDate(item.submitted_at) }}</span>
            </div>
          </div>
          <div class="card-actions">
            <el-button type="primary" size="small" @click="goReview(item)">审核</el-button>
          </div>
        </div>
      </el-card>
      </template>
    </div>

    <el-pagination
      v-if="total > pageSize"
      v-model:current-page="page"
      :page-size="pageSize"
      :total="total"
      layout="prev, pager, next"
      class="pagination"
      @current-change="fetchList"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { reviewAPI } from '@/api'
import PageLoading from '@/components/PageLoading.vue'

const router = useRouter()
const loading = ref(false)
const list = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const typeFilter = ref('')
const searchKeyword = ref('')
const stats = ref({ pending: 0, approved: 0, rejected: 0 })

const practiceTypes = [
  { value: 'writing', label: '写作设计类' }, { value: 'presentation', label: '宣传表达类' },
  { value: 'visit', label: '参观研学类' }, { value: 'performance', label: '表演体验类' },
  { value: 'interaction', label: '交往行动类' }, { value: 'production', label: '生产改造类' },
  { value: 'free', label: '自由申请类' }
]

const typeLabel = (t) => practiceTypes.find(p => p.value === t)?.label || t
const formatDate = (d) => d ? new Date(d).toLocaleString('zh-CN') : '-'

const fetchList = async () => {
  loading.value = true
  try {
    const res = await reviewAPI.getPendingList({
      practice_type: typeFilter.value || undefined,
      keyword: searchKeyword.value || undefined,
      page: page.value,
      page_size: pageSize.value
    })
    list.value = res.items
    total.value = res.total
    await fetchStats()
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

const fetchStats = async () => {
  try {
    const res = await reviewAPI.getStatistics()
    stats.value = res
  } catch (e) {
    console.error(e)
  }
}

const goReview = (item) => {
  router.push({ name: 'ReviewDetail', params: { id: item.id } })
}

onMounted(fetchList)
</script>

<style scoped>
.review-list { width: 100%; }
.page-header { margin-bottom: 20px; }
.page-header h2 { font-size: 22px; color: #333; }
.stats-row { margin-bottom: 20px; }
.stat-card { text-align: center; padding: 10px; }
.stat-num { font-size: 36px; font-weight: bold; }
.stat-label { font-size: 14px; color: #888; margin-top: 4px; }
.filter-card { margin-bottom: 16px; }
.list { display: flex; flex-direction: column; gap: 12px; min-height: 200px; }
.card-body { display: flex; justify-content: space-between; align-items: center; }
.card-title { font-size: 16px; font-weight: bold; color: #333; margin-bottom: 8px; }
.card-meta { display: flex; gap: 20px; font-size: 13px; color: #888; align-items: center; }
.pagination { margin-top: 20px; justify-content: center; display: flex; }
</style>
