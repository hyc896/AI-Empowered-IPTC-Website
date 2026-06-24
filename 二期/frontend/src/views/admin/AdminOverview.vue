<template>
  <div class="overview">
    <h2 class="page-title">系统概览</h2>
    <div v-if="loading" class="tip">加载中...</div>
    <div v-else class="stat-grid">
      <div class="stat-card" v-for="s in stats" :key="s.label">
        <div class="stat-num">{{ s.value }}</div>
        <div class="stat-label">{{ s.label }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { adminAPI } from '@/api/index'

const loading = ref(true)
const stats = ref([])

onMounted(async () => {
  try {
    const d = await adminAPI.getOverview()
    stats.value = [
      { label: '实践提交', value: d.submission_count },
      { label: '注册用户', value: d.user_count },
      { label: '实践方案', value: d.plan_count },
      { label: '场馆数量', value: d.venue_count },
      { label: '知识点', value: d.knowledge_point_count },
    ]
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.overview { max-width: 900px; }
.page-title { color: #ffd700; margin-bottom: 24px; font-size: 20px; }
.stat-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 16px; }
.stat-card { background: rgba(0,0,0,0.65); border: 1px solid rgba(255,215,0,0.15); border-radius: 10px; padding: 28px 16px; text-align: center; }
.stat-num { font-size: 36px; font-weight: 700; color: #ffd700; }
.stat-label { font-size: 13px; color: rgba(255,255,255,0.75); margin-top: 10px; font-weight: 500; }
.tip { color: rgba(255,255,255,0.4); padding: 32px; }
</style>
