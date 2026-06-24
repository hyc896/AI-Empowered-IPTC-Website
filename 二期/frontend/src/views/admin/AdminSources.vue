<template>
  <div class="admin-sources">
    <h2 class="page-title">消息采集</h2>

    <div class="section-title">消息源状态</div>
    <div v-if="sourcesLoading" class="tip">加载中...</div>
    <div v-else-if="sources.length" class="table-wrap">
      <table class="data-table">
        <thead><tr><th>消息源</th><th>消息数</th><th>状态</th><th>操作</th></tr></thead>
        <tbody>
          <tr v-for="s in sources" :key="s.source_id || s.name">
            <td>{{ s.display_name || s.name }}</td>
            <td>{{ s.message_count || 0 }}</td>
            <td><span :class="['badge', s.is_active ? 'active' : 'inactive']">{{ s.is_active ? '启用' : '停用' }}</span></td>
            <td>
              <el-button size="small" :loading="triggering === (s.name || s.source_name)"
                @click="trigger(s.name || s.source_name)">手动采集</el-button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <div v-else class="tip">暂无数据（采集服务可能未启动）</div>

    <div v-if="triggerResult" class="result-box">{{ triggerResult }}</div>

    <div class="section-title" style="margin-top:32px">撞库匹配情况</div>
    <div v-if="matchData" class="match-grid">
      <div class="stat-card"><div class="num">{{ matchData.total_knowledge_points || 0 }}</div><div class="lbl">总知识点</div></div>
      <div class="stat-card"><div class="num">{{ matchData.matched_knowledge_points || 0 }}</div><div class="lbl">已匹配</div></div>
      <div class="stat-card"><div class="num">{{ matchData.total_relations || 0 }}</div><div class="lbl">关联记录</div></div>
      <div class="stat-card"><div class="num">{{ matchData.cases_generated || 0 }}</div><div class="lbl">已生成案例</div></div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { adminAPI } from '@/api/index'

const sources = ref([])
const sourcesLoading = ref(true)
const triggering = ref(null)
const triggerResult = ref('')
const matchData = ref(null)

onMounted(async () => {
  try {
    const res = await adminAPI.getMessageSources()
    sources.value = res.sources || res.data?.sources || []
  } catch (e) {
    sources.value = []
  } finally {
    sourcesLoading.value = false
  }
  try {
    const r = await adminAPI.getMatchingStatus()
    matchData.value = r.data || r
  } catch (e) {}
})

async function trigger(name) {
  triggering.value = name
  triggerResult.value = ''
  try {
    const r = await adminAPI.triggerCollector(name)
    triggerResult.value = `✓ ${name} 采集任务已触发：${r.task_id || JSON.stringify(r)}`
  } catch (e) {
    triggerResult.value = `✗ 触发失败: ${e.message}`
  } finally {
    triggering.value = null
  }
}
</script>

<style scoped>
.admin-sources { max-width: 960px; }
.page-title { color: #ffd700; margin-bottom: 24px; font-size: 20px; }
.section-title { font-size: 13px; color: rgba(255,215,0,0.7); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 12px; }
.tip { color: rgba(255,255,255,0.4); padding: 16px 0; }
.table-wrap { overflow-x: auto; }
.data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.data-table th, .data-table td { padding: 10px 14px; border-bottom: 1px solid rgba(255,255,255,0.08); text-align: left; }
.data-table th { color: rgba(255,215,0,0.7); font-weight: 600; }
.data-table td { color: rgba(255,255,255,0.8); }
.badge { padding: 2px 8px; border-radius: 8px; font-size: 11px; }
.badge.active { background: rgba(39,174,96,0.2); color: #6fcf97; }
.badge.inactive { background: rgba(235,87,87,0.15); color: #eb5757; }
.result-box { margin-top: 12px; padding: 12px 16px; background: rgba(255,255,255,0.06); border-radius: 6px; font-size: 13px; color: rgba(255,255,255,0.7); }
.match-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 12px; }
.stat-card { background: rgba(0,0,0,0.4); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; padding: 20px 16px; text-align: center; }
.num { font-size: 28px; font-weight: 700; color: #ffd700; }
.lbl { font-size: 12px; color: rgba(255,255,255,0.5); margin-top: 6px; }
</style>
