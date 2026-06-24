<template>
  <div class="overview">
    <div class="page-header">
      <h2>系统概览</h2>
      <span class="subtitle">实时数据统计</span>
    </div>
    <div v-if="loading" class="loading">加载中...</div>
    <div v-else>
      <div class="stat-grid">
        <div class="stat-card" v-for="s in stats" :key="s.label">
          <div class="stat-icon">{{ s.icon }}</div>
          <div class="stat-num">{{ s.value ?? '-' }}</div>
          <div class="stat-label">{{ s.label }}</div>
        </div>
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
      { label: '实践提交', value: d.submission_count, icon: '📋' },
      { label: '注册用户', value: d.user_count, icon: '👥' },
      { label: '实践方案', value: d.plan_count, icon: '📝' },
      { label: '场馆资源', value: d.venue_count, icon: '🏛' },
      { label: '知识点', value: d.knowledge_point_count, icon: '🎯' },
    ]
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.overview { max-width: 960px; }
.page-header { margin-bottom: 32px; }
.page-header h2 { font-size: 24px; font-weight: 700; color: #fff; margin: 0 0 4px; }
.subtitle { font-size: 13px; color: rgba(255,255,255,0.4); }
.loading { color: rgba(255,255,255,0.4); padding: 32px 0; }
.stat-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(170px, 1fr)); gap: 16px; }
.stat-card {
  background: rgba(0,0,0,0.6);
  border: 1px solid rgba(255,215,0,0.12);
  border-radius: 12px;
  padding: 24px 20px;
  text-align: center;
  transition: border-color 0.2s;
}
.stat-card:hover { border-color: rgba(255,215,0,0.3); }
.stat-icon { font-size: 28px; margin-bottom: 12px; }
.stat-num { font-size: 36px; font-weight: 700; color: #ffd700; line-height: 1; margin-bottom: 10px; }
.stat-label { font-size: 13px; color: rgba(255,255,255,0.65); font-weight: 500; }
</style>
