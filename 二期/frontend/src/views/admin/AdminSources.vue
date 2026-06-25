<template>
  <div class="admin-sources">
    <section class="workflow-hero">
      <div>
        <span class="eyebrow">Collection Workflow</span>
        <h2>采集、撞库与案例生成</h2>
        <p>按全国源与上海源分池管理。手动操作前可以先查看候选列表，避免一次性生成全部内容。</p>
      </div>
      <div class="scope-switch">
        <button
          v-for="item in scopeOptions"
          :key="item.value"
          :class="['scope-button', workflowScope === item.value && 'active']"
          @click="changeScope(item.value)"
        >
          {{ item.label }}
        </button>
      </div>
    </section>

    <section class="quick-grid">
      <article v-for="card in statusCards" :key="card.label" class="quick-card">
        <span>{{ card.label }}</span>
        <strong>{{ card.value }}</strong>
        <small>{{ card.hint }}</small>
      </article>
    </section>

    <section class="action-panel">
      <div class="action-copy">
        <span class="eyebrow">Manual Control</span>
        <h3>手动执行当前范围任务</h3>
        <p>当前范围：{{ currentScopeLabel }}。上海范围只处理上海源消息，全国范围只处理非上海源消息。</p>
      </div>
      <div class="action-buttons">
        <button class="solid-button" :disabled="triggeringMatch" @click="doTriggerMatch">
          {{ triggeringMatch ? '撞库任务提交中' : '立即撞库匹配' }}
        </button>
        <button class="outline-button" :disabled="triggeringGen" @click="doTriggerGen">
          {{ triggeringGen ? '生成任务提交中' : '立即生成案例' }}
        </button>
      </div>
    </section>

    <div v-if="triggerResult" :class="['result-bar', triggerResult.type]">
      <strong>{{ triggerResult.title }}</strong>
      <span>{{ triggerResult.message }}</span>
    </div>

    <section class="dashboard-grid">
      <article class="panel source-panel">
        <div class="panel-title">
          <div>
            <span class="eyebrow">Sources</span>
            <h3>消息源</h3>
          </div>
          <div class="filter-tabs">
            <button
              v-for="item in sourceFilterOptions"
              :key="item.value"
              :class="['filter-tab', sourceFilter === item.value && 'active']"
              @click="sourceFilter = item.value"
            >
              {{ item.label }}
            </button>
          </div>
        </div>

        <div v-if="sourcesLoading" class="state-panel">消息源加载中...</div>
        <div v-else-if="!filteredSources.length" class="state-panel">当前范围暂无消息源</div>
        <div v-else class="source-table">
          <div class="table-head">
            <span>名称</span>
            <span>范围</span>
            <span>消息数</span>
            <span>状态</span>
            <span>操作</span>
          </div>
          <div v-for="source in filteredSources" :key="source.key" class="source-row">
            <div class="source-name">
              <strong>{{ source.display_name || source.name }}</strong>
              <small>{{ source.name }}</small>
            </div>
            <span class="scope-pill" :class="source.source_scope">{{ sourceScopeLabel(source.source_scope) }}</span>
            <span>{{ formatNumber(source.message_count) }} 条</span>
            <span :class="['status-pill', source.is_active ? 'active' : 'inactive']">
              {{ source.is_active ? '启用' : '停用' }}
            </span>
            <button
              class="row-button"
              :disabled="triggering === source.name || !source.is_active"
              @click="trigger(source.name)"
            >
              {{ triggering === source.name ? '提交中' : '手动采集' }}
            </button>
          </div>
        </div>
      </article>

      <article class="panel review-panel">
        <div class="panel-title">
          <div>
            <span class="eyebrow">Review Queue</span>
            <h3>候选列表</h3>
          </div>
          <button class="row-button" @click="loadCandidates">刷新候选</button>
        </div>

        <div class="candidate-tabs">
          <button
            v-for="item in candidateTabs"
            :key="item.value"
            :class="['candidate-tab', candidateTab === item.value && 'active']"
            @click="candidateTab = item.value"
          >
            {{ item.label }}
          </button>
        </div>

        <div v-if="candidatesLoading" class="state-panel">候选数据加载中...</div>
        <div v-else-if="!activeCandidates.length" class="state-panel">当前范围暂无候选数据</div>
        <div v-else class="candidate-list">
          <div v-for="item in activeCandidates" :key="candidateKey(item)" class="candidate-item">
            <strong>{{ candidateTitle(item) }}</strong>
            <p>{{ candidateMeta(item) }}</p>
            <span v-if="candidateReason(item)">{{ candidateReason(item) }}</span>
          </div>
        </div>
      </article>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { adminAPI, caseAPI } from '@/api/index'

const scopeOptions = [
  { label: '全部', value: 'all' },
  { label: '全国源', value: 'national' },
  { label: '上海源', value: 'shanghai' },
]

const sourceFilterOptions = [
  { label: '全部', value: 'all' },
  { label: '全国源', value: 'national' },
  { label: '上海源', value: 'shanghai' },
  { label: '仅自动', value: 'auto' },
]

const candidateTabs = [
  { label: '采集消息', value: 'messages' },
  { label: '撞库匹配', value: 'matches' },
  { label: '案例候选', value: 'cases' },
]

const sources = ref([])
const sourcesLoading = ref(true)
const triggering = ref(null)
const triggerResult = ref(null)
const matchData = ref({})
const triggeringMatch = ref(false)
const triggeringGen = ref(false)
const workflowScope = ref('all')
const sourceFilter = ref('all')
const candidateTab = ref('messages')
const candidatesLoading = ref(false)
const candidates = ref({ messages: [], matches: [], cases: [] })

const currentScopeLabel = computed(() => scopeOptions.find(item => item.value === workflowScope.value)?.label || '全部')

const filteredSources = computed(() => {
  return sources.value.filter(source => {
    if (sourceFilter.value === 'auto') return source.auto_collect_enabled !== false
    if (sourceFilter.value !== 'all') return source.source_scope === sourceFilter.value
    return true
  })
})

const activeCandidates = computed(() => candidates.value[candidateTab.value] || [])

const statusCards = computed(() => {
  const shanghaiCount = sources.value.filter(source => source.source_scope === 'shanghai').length
  const nationalCount = sources.value.filter(source => source.source_scope !== 'shanghai').length
  return [
    { label: '知识点', value: formatNumber(matchData.value.total_knowledge_points), hint: '向量库与知识点配置' },
    { label: '关联记录', value: formatNumber(matchData.value.total_relations), hint: '消息和知识点关系' },
    { label: '已生成案例', value: formatNumber(matchData.value.cases_generated || matchData.value.total_cases), hint: '案例库当前规模' },
    { label: '上海源', value: formatNumber(shanghaiCount), hint: `全国源 ${formatNumber(nationalCount)} 个` },
  ]
})

function formatNumber(value) {
  return Number(value || 0).toLocaleString()
}

function sourceScopeLabel(scope) {
  if (scope === 'shanghai') return '上海'
  if (scope === 'national') return '全国'
  return '全国'
}

function normalizeSource(raw = {}, statusMap = new Map()) {
  const name = raw.name || raw.source_name || raw.display_name
  const table = raw.mysql_table || raw.source_table || raw.table_name
  const status = statusMap.get(name) || statusMap.get(raw.display_name) || statusMap.get(table) || {}
  const scope = raw.source_scope || (table && table.includes('shanghai') ? 'shanghai' : 'national')
  return {
    key: raw.source_id || raw.id || name || table,
    name,
    display_name: raw.display_name || status.display_name || name,
    mysql_table: table,
    source_scope: scope === 'shanghai' ? 'shanghai' : 'national',
    message_count: raw.message_count ?? status.message_count ?? 0,
    is_active: raw.is_active ?? status.is_active ?? true,
    auto_collect_enabled: raw.auto_collect_enabled ?? status.auto_collect_enabled ?? true,
    last_crawled_at: raw.last_crawled_at || status.last_crawled_at,
  }
}

function buildStatusMap(payload = {}) {
  const rows = payload.sources || payload.data?.sources || []
  const map = new Map()
  for (const row of rows) {
    const keys = [row.source_name, row.name, row.display_name, row.mysql_table, row.source_table].filter(Boolean)
    for (const key of keys) map.set(key, row)
  }
  return map
}

async function loadSources() {
  sourcesLoading.value = true
  try {
    const [collectorsRes, statusRes, matchRes, caseStatsRes] = await Promise.allSettled([
      adminAPI.getCollectors(),
      adminAPI.getMessageSources(),
      adminAPI.getMatchingStatus(),
      caseAPI.getStatistics(),
    ])
    const statusMap = statusRes.status === 'fulfilled' ? buildStatusMap(statusRes.value) : new Map()
    const collectors = collectorsRes.status === 'fulfilled'
      ? (Array.isArray(collectorsRes.value) ? collectorsRes.value : collectorsRes.value.data || [])
      : []
    const fallback = statusRes.status === 'fulfilled' ? (statusRes.value.sources || statusRes.value.data?.sources || []) : []
    sources.value = (collectors.length ? collectors : fallback)
      .map(item => normalizeSource(item, statusMap))
      .filter(item => item.name)
      .sort((a, b) => {
        if (a.source_scope !== b.source_scope) return a.source_scope === 'shanghai' ? -1 : 1
        return (b.message_count || 0) - (a.message_count || 0)
      })
    const oldStats = matchRes.status === 'fulfilled' ? (matchRes.value.data || matchRes.value || {}) : {}
    const caseStats = caseStatsRes.status === 'fulfilled' ? (caseStatsRes.value.data || caseStatsRes.value || {}) : {}
    matchData.value = {
      ...oldStats,
      total_knowledge_points: caseStats.total_knowledge_points ?? oldStats.total_knowledge_points,
      total_relations: caseStats.total_relations ?? oldStats.total_relations,
      total_cases: caseStats.total_cases ?? oldStats.total_cases,
      cases_generated: caseStats.total_cases ?? oldStats.cases_generated,
    }
  } finally {
    sourcesLoading.value = false
  }
}

async function loadCandidates() {
  candidatesLoading.value = true
  try {
    const params = { scope: workflowScope.value, limit: 12 }
    const [messagesRes, matchesRes, casesRes] = await Promise.allSettled([
      caseAPI.getMessageCandidates(params),
      caseAPI.getMatchCandidates(params),
      caseAPI.getCaseCandidates(params),
    ])
    candidates.value = {
      messages: messagesRes.status === 'fulfilled' ? (messagesRes.value.data || []) : [],
      matches: matchesRes.status === 'fulfilled' ? (matchesRes.value.data || []) : [],
      cases: casesRes.status === 'fulfilled' ? (casesRes.value.data || []) : [],
    }
  } finally {
    candidatesLoading.value = false
  }
}

async function changeScope(nextScope) {
  workflowScope.value = nextScope
  if (nextScope === 'national' || nextScope === 'shanghai') sourceFilter.value = nextScope
  await loadCandidates()
}

function showResult(type, title, message) {
  triggerResult.value = { type, title, message }
}

async function trigger(name) {
  triggering.value = name
  try {
    const r = await adminAPI.triggerCollector(name)
    showResult('ok', '采集任务已提交', r.task_id || r.message || name)
  } catch (e) {
    showResult('error', '采集触发失败', e.message || String(e))
  } finally {
    triggering.value = null
    await loadSources()
  }
}

async function doTriggerMatch() {
  triggeringMatch.value = true
  try {
    const r = await adminAPI.triggerMatching({ scope: workflowScope.value })
    showResult('ok', '撞库匹配任务已提交', r.task_id || r.message || currentScopeLabel.value)
  } catch (e) {
    showResult('error', '撞库匹配触发失败', e.message || String(e))
  } finally {
    triggeringMatch.value = false
  }
}

async function doTriggerGen() {
  triggeringGen.value = true
  try {
    const r = await adminAPI.triggerCaseGeneration({ scope: workflowScope.value })
    showResult('ok', '案例生成任务已提交', r.task_id || r.message || currentScopeLabel.value)
  } catch (e) {
    showResult('error', '案例生成触发失败', e.message || String(e))
  } finally {
    triggeringGen.value = false
  }
}

function candidateKey(item) {
  return item.id || item.message_id || item.relation_id || item.knowledge_point_id || item.knowledge_point_name || item.title
}

function candidateTitle(item) {
  return item.title || item.message_title || item.knowledge_point_name || item.case_title || '未命名候选'
}

function candidateMeta(item) {
  if (candidateTab.value === 'matches') {
    const score = item.similarity_score ? `相似度 ${Number(item.similarity_score).toFixed(4)}` : '相似度未记录'
    return `${sourceScopeLabel(item.source_scope)} · ${score} · ${item.knowledge_point_name || '知识点未记录'}`
  }
  if (candidateTab.value === 'cases') {
    return `${sourceScopeLabel(item.scope || item.source_scope)} · ${item.message_count || item.messages_count || 0} 条消息`
  }
  return `${sourceScopeLabel(item.source_scope)} · ${item.source_table || item.mysql_table || '来源表未记录'}`
}

function candidateReason(item) {
  return item.local_relevance_reason || item.relevance_reason || item.reason || ''
}

onMounted(async () => {
  await Promise.all([loadSources(), loadCandidates()])
})
</script>

<style scoped>
.admin-sources {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.workflow-hero,
.action-panel,
.panel,
.quick-card,
.result-bar {
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(14, 17, 22, 0.76);
  box-shadow: 0 18px 40px rgba(0, 0, 0, 0.22);
}

.workflow-hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 22px;
}

.eyebrow {
  display: block;
  font-size: 11px;
  color: #d6b15f;
  letter-spacing: 0;
}

.workflow-hero h2,
.action-copy h3,
.panel-title h3 {
  margin: 3px 0 0;
  color: #fff;
  font-size: 20px;
  letter-spacing: 0;
}

.workflow-hero p,
.action-copy p {
  max-width: 720px;
  margin: 8px 0 0;
  color: rgba(245, 239, 228, 0.58);
  line-height: 1.7;
}

.scope-switch,
.filter-tabs,
.candidate-tabs,
.action-buttons {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.scope-button,
.filter-tab,
.candidate-tab,
.row-button,
.outline-button,
.solid-button {
  border-radius: 8px;
  border: 1px solid rgba(214, 177, 95, 0.22);
  background: rgba(255, 255, 255, 0.04);
  color: rgba(245, 239, 228, 0.72);
  cursor: pointer;
  transition: all 0.18s ease;
}

.scope-button {
  height: 42px;
  padding: 0 18px;
  font-weight: 700;
}

.scope-button.active,
.filter-tab.active,
.candidate-tab.active {
  background: #d6b15f;
  color: #151515;
  border-color: #d6b15f;
}

.quick-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.quick-card {
  min-height: 112px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.quick-card span,
.quick-card small {
  color: rgba(245, 239, 228, 0.52);
}

.quick-card strong {
  font-size: 30px;
  line-height: 1;
  color: #fff;
}

.action-panel {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 18px;
}

.solid-button,
.outline-button {
  height: 40px;
  padding: 0 16px;
  font-weight: 700;
}

.solid-button {
  background: #d6b15f;
  color: #151515;
  border-color: #d6b15f;
}

.outline-button:hover,
.row-button:hover,
.filter-tab:hover,
.candidate-tab:hover,
.scope-button:hover {
  border-color: rgba(214, 177, 95, 0.55);
  color: #fff;
}

button:disabled {
  opacity: 0.48;
  cursor: default;
}

.result-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
}

.result-bar.ok {
  border-color: rgba(82, 137, 115, 0.34);
  background: rgba(82, 137, 115, 0.16);
}

.result-bar.error {
  border-color: rgba(196, 91, 87, 0.34);
  background: rgba(196, 91, 87, 0.14);
}

.result-bar span {
  color: rgba(245, 239, 228, 0.65);
}

.dashboard-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(360px, 0.85fr);
  gap: 18px;
}

.panel {
  padding: 18px;
  min-width: 0;
}

.panel-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 14px;
}

.filter-tab,
.candidate-tab,
.row-button {
  min-height: 32px;
  padding: 0 11px;
  font-size: 12px;
}

.state-panel {
  padding: 28px;
  border-radius: 8px;
  color: rgba(245, 239, 228, 0.55);
  background: rgba(255, 255, 255, 0.045);
  text-align: center;
}

.source-table {
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.table-head,
.source-row {
  display: grid;
  grid-template-columns: minmax(220px, 1.5fr) 86px 96px 76px 92px;
  align-items: center;
  gap: 12px;
  padding: 11px 14px;
}

.table-head {
  background: rgba(255, 255, 255, 0.05);
  color: #d6b15f;
  font-size: 12px;
}

.source-row {
  min-height: 62px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  color: rgba(245, 239, 228, 0.72);
}

.source-name {
  min-width: 0;
}

.source-name strong,
.source-name small {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.source-name strong {
  color: #fff;
  font-size: 14px;
}

.source-name small {
  margin-top: 3px;
  color: rgba(245, 239, 228, 0.42);
  font-size: 12px;
}

.scope-pill,
.status-pill {
  justify-self: start;
  padding: 3px 9px;
  border-radius: 999px;
  font-size: 12px;
}

.scope-pill.shanghai {
  color: #9bd2bd;
  background: rgba(82, 137, 115, 0.18);
}

.scope-pill.national {
  color: #d8c28e;
  background: rgba(214, 177, 95, 0.14);
}

.status-pill.active {
  color: #9bd2bd;
  background: rgba(82, 137, 115, 0.18);
}

.status-pill.inactive {
  color: #d9958f;
  background: rgba(196, 91, 87, 0.14);
}

.candidate-tabs {
  margin-bottom: 12px;
}

.candidate-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 620px;
  overflow-y: auto;
}

.candidate-item {
  padding: 13px;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.045);
}

.candidate-item strong {
  display: block;
  color: #fff;
  font-size: 13px;
  line-height: 1.45;
}

.candidate-item p {
  margin: 6px 0 0;
  color: rgba(245, 239, 228, 0.56);
  font-size: 12px;
}

.candidate-item span {
  display: block;
  margin-top: 6px;
  color: #d6b15f;
  font-size: 12px;
  line-height: 1.5;
}

@media (max-width: 1180px) {
  .quick-grid,
  .dashboard-grid,
  .action-panel,
  .workflow-hero {
    grid-template-columns: 1fr;
    display: grid;
  }

  .table-head,
  .source-row {
    grid-template-columns: minmax(180px, 1fr) 76px 76px 72px 88px;
  }
}
</style>
