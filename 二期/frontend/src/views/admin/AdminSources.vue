<template>
  <div class="admin-sources">
    <div class="page-header">
      <h2>消息采集</h2>
      <div class="header-actions">
        <button class="action-btn primary" :class="{loading: triggeringMatch}" @click="doTriggerMatch">
          {{ triggeringMatch ? '执行中...' : '立即撞库匹配' }}
        </button>
        <button class="action-btn" :class="{loading: triggeringGen}" @click="doTriggerGen">
          {{ triggeringGen ? '执行中...' : '立即生成案例' }}
        </button>
      </div>
    </div>

    <div v-if="triggerResult" class="result-bar" :class="triggerResult.startsWith('✓') ? 'ok' : 'err'">
      {{ triggerResult }}
    </div>

    <!-- 匹配统计 -->
    <div v-if="matchData" class="match-row">
      <div class="match-card" v-for="(val, label) in matchCards" :key="label">
        <div class="match-num">{{ val }}</div>
        <div class="match-lbl">{{ label }}</div>
      </div>
    </div>

    <!-- 消息源列表 -->
    <div class="section-header">
      <span class="section-title">消息源</span>
      <div class="filter-tabs">
        <button :class="['ftab', !categoryFilter && 'active']" @click="categoryFilter=null">全部</button>
        <button :class="['ftab', categoryFilter==='国内' && 'active']" @click="categoryFilter='国内'">国内</button>
        <button :class="['ftab', categoryFilter==='国际' && 'active']" @click="categoryFilter='国际'">国际</button>
      </div>
    </div>
    <div v-if="sourcesLoading" class="loading">加载中...</div>
    <div v-else-if="!filteredSources.length" class="loading">暂无数据（采集服务可能未启动）</div>
    <div v-else class="source-list">
      <div class="source-row" v-for="s in filteredSources" :key="s.source_id || s.name">
        <div class="source-info">
          <span class="source-name">{{ s.display_name || s.name }}</span>
          <span class="source-tag">{{ s.is_chinese ? '国内' : '国际' }}</span>
        </div>
        <div class="source-meta">
          <span class="meta-count">{{ (s.message_count || 0).toLocaleString() }} 条</span>
          <span :class="['status-dot', s.is_active ? 'on' : 'off']"></span>
          <span class="status-txt">{{ s.is_active ? '启用' : '停用' }}</span>
        </div>
        <button class="action-btn sm" :class="{loading: triggering === (s.name || s.source_name)}"
          @click="trigger(s.name || s.source_name)">
          {{ triggering === (s.name || s.source_name) ? '采集中...' : '手动采集' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { adminAPI } from '@/api/index'

const sources = ref([])
const sourcesLoading = ref(true)
const triggering = ref(null)
const triggerResult = ref('')
const matchData = ref(null)
const triggeringMatch = ref(false)
const triggeringGen = ref(false)
const categoryFilter = ref(null)

const filteredSources = computed(() => {
  if (!categoryFilter.value) return sources.value
  return sources.value.filter(s => categoryFilter.value === '国内' ? s.is_chinese : !s.is_chinese)
})

const matchCards = computed(() => matchData.value ? {
  '总知识点': matchData.value.total_knowledge_points || 0,
  '已匹配': matchData.value.matched_knowledge_points || 0,
  '关联记录': matchData.value.total_relations || 0,
  '已生成案例': matchData.value.cases_generated || 0,
} : {})

onMounted(async () => {
  try {
    const res = await adminAPI.getMessageSources()
    sources.value = res.sources || res.data?.sources || []
  } catch (e) { sources.value = [] } finally { sourcesLoading.value = false }
  try {
    const r = await adminAPI.getMatchingStatus()
    matchData.value = r.data || r
  } catch (e) {}
})

async function trigger(name) {
  triggering.value = name
  try {
    const r = await adminAPI.triggerCollector(name)
    triggerResult.value = `✓ 已触发 ${name}：${r.task_id || r.message || 'OK'}`
  } catch (e) { triggerResult.value = `✗ 失败: ${e.message}` }
  finally { triggering.value = null }
}

async function doTriggerMatch() {
  triggeringMatch.value = true
  try {
    const r = await adminAPI.triggerMatching()
    triggerResult.value = `✓ 撞库匹配已触发：${r.task_id || r.message || 'OK'}`
  } catch (e) { triggerResult.value = `✗ 失败: ${e.message}` }
  finally { triggeringMatch.value = false }
}

async function doTriggerGen() {
  triggeringGen.value = true
  try {
    const r = await adminAPI.triggerCaseGeneration()
    triggerResult.value = `✓ 案例生成已触发：${r.task_id || r.message || 'OK'}`
  } catch (e) { triggerResult.value = `✗ 失败: ${e.message}` }
  finally { triggeringGen.value = false }
}
</script>

<style scoped>
.admin-sources { width: 100%; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
.page-header h2 { font-size: 22px; font-weight: 700; color: #fff; margin: 0; }
.header-actions { display: flex; gap: 10px; }

.action-btn {
  padding: 8px 18px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid rgba(255,215,0,0.3);
  background: rgba(255,215,0,0.1);
  color: #ffd700;
  transition: all 0.15s;
}
.action-btn:hover { background: rgba(255,215,0,0.2); border-color: rgba(255,215,0,0.5); }
.action-btn.primary { background: rgba(255,215,0,0.2); border-color: #ffd700; }
.action-btn.sm { padding: 5px 12px; font-size: 12px; }
.action-btn.loading { opacity: 0.6; cursor: default; }

.result-bar { margin-bottom: 16px; padding: 10px 16px; border-radius: 8px; font-size: 13px; }
.result-bar.ok { background: rgba(39,174,96,0.15); border: 1px solid rgba(39,174,96,0.3); color: #6fcf97; }
.result-bar.err { background: rgba(235,87,87,0.15); border: 1px solid rgba(235,87,87,0.3); color: #eb8787; }

.match-row { display: grid; grid-template-columns: repeat(4,1fr); gap: 12px; margin-bottom: 28px; }
.match-card { background: rgba(0,0,0,0.55); border: 1px solid rgba(255,215,0,0.12); border-radius: 10px; padding: 18px; text-align: center; }
.match-num { font-size: 28px; font-weight: 700; color: #ffd700; }
.match-lbl { font-size: 12px; color: rgba(255,255,255,0.55); margin-top: 6px; }

.section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.section-title { font-size: 14px; font-weight: 600; color: rgba(255,255,255,0.7); text-transform: uppercase; letter-spacing: 1px; }
.filter-tabs { display: flex; gap: 4px; }
.ftab { padding: 4px 14px; border-radius: 20px; font-size: 12px; cursor: pointer; border: 1px solid rgba(255,255,255,0.15); background: transparent; color: rgba(255,255,255,0.45); transition: all 0.15s; }
.ftab:hover { color: #fff; }
.ftab.active { background: rgba(255,215,0,0.15); border-color: rgba(255,215,0,0.4); color: #ffd700; }

.loading { color: rgba(255,255,255,0.4); padding: 16px 0; font-size: 13px; }
.source-list { display: flex; flex-direction: column; gap: 2px; }
.source-row {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  border-radius: 8px;
  background: rgba(0,0,0,0.4);
  border: 1px solid rgba(255,255,255,0.05);
  transition: background 0.15s;
}
.source-row:hover { background: rgba(0,0,0,0.55); }
.source-info { flex: 1; display: flex; align-items: center; gap: 10px; }
.source-name { font-size: 14px; color: rgba(255,255,255,0.85); }
.source-tag { font-size: 11px; padding: 2px 8px; border-radius: 10px; background: rgba(255,255,255,0.08); color: rgba(255,255,255,0.4); }
.source-meta { display: flex; align-items: center; gap: 8px; margin-right: 16px; }
.meta-count { font-size: 13px; color: rgba(255,255,255,0.5); }
.status-dot { width: 6px; height: 6px; border-radius: 50%; }
.status-dot.on { background: #6fcf97; box-shadow: 0 0 6px rgba(111,207,151,0.5); }
.status-dot.off { background: rgba(255,255,255,0.2); }
.status-txt { font-size: 12px; color: rgba(255,255,255,0.4); }
</style>
