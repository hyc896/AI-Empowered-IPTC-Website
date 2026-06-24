<template>
  <div class="admin-practices">
    <div class="page-header">
      <h2>实践项目</h2>
      <span class="subtitle">共 {{ total }} 条提交</span>
    </div>
    <div v-if="loading" class="loading">加载中...</div>
    <div v-else>
      <div class="list">
        <div class="list-header">
          <span>标题</span><span>状态</span><span>提交时间</span>
        </div>
        <div class="list-row" v-for="s in items" :key="s.id">
          <span class="item-title">{{ s.title || s.id }}</span>
          <span>
            <span class="status-badge" :class="s.status">{{ s.status || '—' }}</span>
          </span>
          <span class="item-date">{{ s.created_at ? s.created_at.slice(0,10) : '—' }}</span>
        </div>
      </div>
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
  } finally { loading.value = false }
}

onMounted(load)
</script>

<style scoped>
.admin-practices { max-width: 960px; }
.page-header { display: flex; align-items: baseline; gap: 12px; margin-bottom: 24px; }
.page-header h2 { font-size: 22px; font-weight: 700; color: #fff; margin: 0; }
.subtitle { font-size: 13px; color: rgba(255,255,255,0.4); }
.loading { color: rgba(255,255,255,0.4); padding: 32px 0; font-size: 13px; }

.list { border-radius: 10px; overflow: hidden; border: 1px solid rgba(255,255,255,0.08); }
.list-header {
  display: grid;
  grid-template-columns: 2fr 0.8fr 1fr;
  padding: 10px 16px;
  background: rgba(0,0,0,0.5);
  font-size: 11px;
  color: rgba(255,215,0,0.6);
  text-transform: uppercase;
  letter-spacing: 1px;
}
.list-row {
  display: grid;
  grid-template-columns: 2fr 0.8fr 1fr;
  padding: 13px 16px;
  font-size: 13px;
  color: rgba(255,255,255,0.8);
  border-top: 1px solid rgba(255,255,255,0.05);
  background: rgba(0,0,0,0.35);
  transition: background 0.15s;
  align-items: center;
}
.list-row:hover { background: rgba(0,0,0,0.5); }
.item-title { color: #fff; font-weight: 500; }
.item-date { font-size: 12px; color: rgba(255,255,255,0.4); }
.status-badge { padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; background: rgba(255,255,255,0.1); color: rgba(255,255,255,0.6); border: 1px solid rgba(255,255,255,0.15); }
.status-badge.submitted { background: rgba(39,174,96,0.15); color: #6fcf97; border-color: rgba(39,174,96,0.25); }
.status-badge.pending { background: rgba(255,193,7,0.15); color: #ffc107; border-color: rgba(255,193,7,0.25); }
.status-badge.reviewed { background: rgba(52,152,219,0.15); color: #64b5f6; border-color: rgba(52,152,219,0.25); }
.pagination { padding: 16px 0; display: flex; justify-content: center; }
</style>
