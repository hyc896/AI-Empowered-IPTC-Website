<template>
  <div class="admin-practices">
    <h2 class="page-title">实践项目</h2>
    <div v-if="loading" class="tip">加载中...</div>
    <div v-else>
      <table class="data-table">
        <thead><tr><th>标题</th><th>状态</th><th>提交时间</th></tr></thead>
        <tbody>
          <tr v-for="s in items" :key="s.id">
            <td>{{ s.title || s.id }}</td>
            <td><span class="badge">{{ s.status || '-' }}</span></td>
            <td>{{ s.created_at ? s.created_at.slice(0, 10) : '-' }}</td>
          </tr>
        </tbody>
      </table>
      <div class="pagination">
        <el-pagination v-model:current-page="page" :page-size="20" :total="total"
          layout="prev, pager, next" @current-change="load" background size="small" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { adminAPI } from '@/api/index'

const items = ref([])
const loading = ref(true)
const page = ref(1)
const total = ref(0)

async function load() {
  loading.value = true
  try {
    const r = await adminAPI.getPractices({ page: page.value })
    items.value = r.items || []
    total.value = r.total || 0
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.admin-practices { max-width: 960px; }
.page-title { color: #ffd700; margin-bottom: 24px; font-size: 20px; }
.tip { color: rgba(255,255,255,0.4); padding: 16px 0; }
.data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.data-table th, .data-table td { padding: 10px 14px; border-bottom: 1px solid rgba(255,255,255,0.08); text-align: left; }
.data-table th { color: rgba(255,215,0,0.7); font-weight: 600; }
.data-table td { color: rgba(255,255,255,0.8); }
.badge { padding: 2px 8px; border-radius: 8px; font-size: 11px; background: rgba(255,255,255,0.1); color: rgba(255,255,255,0.6); }
.pagination { padding: 16px 0; display: flex; justify-content: center; }
</style>
