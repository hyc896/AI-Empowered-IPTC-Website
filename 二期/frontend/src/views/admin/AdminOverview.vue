<template>
  <div class="admin-overview">
    <div v-if="loadWarnings.length" class="warning-strip">
      <strong>数据加载提示</strong>
      <span>{{ loadWarnings.join('；') }}</span>
    </div>

    <section class="metric-grid">
      <article v-for="item in metrics" :key="item.label" class="metric-card">
        <span class="metric-kicker">{{ item.kicker }}</span>
        <strong>{{ item.value }}</strong>
        <span>{{ item.label }}</span>
      </article>
    </section>

    <section class="overview-grid">
      <article class="panel wide-panel">
        <div class="panel-title">
          <div>
            <span class="eyebrow">Case Pipeline</span>
            <h2>案例生产状态</h2>
          </div>
          <button class="panel-action" @click="router.push('/admin/sources')">进入采集与生成</button>
        </div>
        <div class="pipeline-row">
          <div v-for="step in pipeline" :key="step.label" class="pipeline-step">
            <span>{{ step.label }}</span>
            <strong>{{ step.value }}</strong>
            <p>{{ step.desc }}</p>
          </div>
        </div>
      </article>

      <article class="panel">
        <div class="panel-title compact">
          <div>
            <span class="eyebrow">Latest</span>
            <h2>最近案例</h2>
          </div>
        </div>
        <div v-if="latestCases.length" class="latest-list">
          <div v-for="item in latestCases" :key="item.id" class="latest-item">
            <strong>{{ item.title }}</strong>
            <span>{{ formatDate(item.created_at) }}</span>
          </div>
        </div>
        <div v-else class="empty-text">暂无最近案例</div>
      </article>
    </section>

    <section class="panel">
      <div class="panel-title compact">
        <div>
          <span class="eyebrow">Operational Notes</span>
          <h2>当前建议</h2>
        </div>
      </div>
      <div class="advice-grid">
        <div class="advice-item">
          <strong>全国与上海分池</strong>
          <span>全国源用于全国案例，上海源用于上海案例和实践地点提取。</span>
        </div>
        <div class="advice-item">
          <strong>手动操作先看候选</strong>
          <span>在采集与生成页先查看消息、匹配和案例候选，再触发对应范围任务。</span>
        </div>
        <div class="advice-item">
          <strong>生成时间已补齐</strong>
          <span>案例库卡片会展示生成时间，便于判断新旧案例。</span>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { adminAPI, caseAPI } from '@/api/index'

const router = useRouter()
const loading = ref(true)
const overview = ref({})
const caseStats = ref({})
const loadWarnings = ref([])

const metrics = computed(() => [
  { kicker: 'Cases', label: '教学案例', value: formatNumber(caseStats.value.total_cases ?? 0) },
  { kicker: 'Knowledge', label: '知识点总数', value: formatNumber(caseStats.value.total_knowledge_points ?? overview.value.knowledge_point_count ?? 0) },
  { kicker: 'Users', label: '注册用户', value: formatNumber(overview.value.user_count ?? 0) },
  { kicker: 'Venues', label: '实践场馆', value: formatNumber(overview.value.venue_count ?? 0) },
])

const pipeline = computed(() => [
  {
    label: '知识点覆盖',
    value: formatNumber(caseStats.value.generated_knowledge_points ?? 0),
    desc: '已经生成案例的知识点数量',
  },
  {
    label: '关联记录',
    value: formatNumber(caseStats.value.total_relations ?? 0),
    desc: '消息与知识点的撞库关系',
  },
  {
    label: '实践方案',
    value: formatNumber(overview.value.plan_count ?? 0),
    desc: '学生端已创建的实践方案',
  },
])

const latestCases = computed(() => caseStats.value.latest_cases || [])

function unwrapResponse(value) {
  return value?.data?.data || value?.data || value || {}
}

async function loadCaseStatsFallback() {
  const result = await caseAPI.getList({ page: 1, page_size: 5 })
  const payload = unwrapResponse(result)
  return {
    total_cases: payload.total ?? 0,
    latest_cases: payload.items || payload.cases || [],
  }
}

function formatNumber(value) {
  return Number(value || 0).toLocaleString()
}

function formatDate(value) {
  if (!value) return '未记录'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value).slice(0, 10)
  return date.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

onMounted(async () => {
  loadWarnings.value = []
  try {
    const [ov, cs] = await Promise.allSettled([adminAPI.getOverview(), caseAPI.getStatistics()])
    overview.value = ov.status === 'fulfilled' ? unwrapResponse(ov.value) : {}

    if (cs.status === 'fulfilled') {
      caseStats.value = unwrapResponse(cs.value)
    } else {
      loadWarnings.value.push('案例统计接口暂时不可用，已尝试使用案例列表兜底')
      try {
        caseStats.value = await loadCaseStatsFallback()
      } catch (e) {
        loadWarnings.value.push('案例列表兜底也失败，请检查 collector-backend')
        caseStats.value = {}
      }
    }

    if (ov.status !== 'fulfilled') {
      loadWarnings.value.push('用户、实践、场馆统计暂时不可用，请检查 practice-backend')
    }
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.admin-overview {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.warning-strip {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border-radius: 8px;
  border: 1px solid rgba(234, 179, 8, 0.28);
  background: rgba(234, 179, 8, 0.1);
  color: rgba(255, 244, 214, 0.86);
  font-size: 13px;
}

.warning-strip strong {
  color: #f2ca76;
  white-space: nowrap;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.metric-card,
.panel {
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(14, 17, 22, 0.76);
  box-shadow: 0 18px 40px rgba(0, 0, 0, 0.22);
}

.metric-card {
  min-height: 128px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.metric-kicker,
.eyebrow {
  font-size: 11px;
  color: #d6b15f;
  letter-spacing: 0;
}

.metric-card strong {
  font-size: 34px;
  line-height: 1;
  color: #fff;
}

.metric-card span:last-child {
  color: rgba(245, 239, 228, 0.56);
  font-size: 13px;
}

.overview-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.55fr) minmax(320px, 0.95fr);
  gap: 18px;
}

.panel {
  padding: 20px;
}

.panel-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.panel-title.compact {
  margin-bottom: 12px;
}

.panel-title h2 {
  margin: 2px 0 0;
  font-size: 18px;
}

.panel-action {
  height: 36px;
  padding: 0 14px;
  border-radius: 8px;
  border: 1px solid rgba(214, 177, 95, 0.28);
  background: rgba(214, 177, 95, 0.12);
  color: #f2ca76;
  cursor: pointer;
}

.pipeline-row {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.pipeline-step,
.advice-item,
.latest-item {
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.045);
  border: 1px solid rgba(255, 255, 255, 0.07);
}

.pipeline-step {
  min-height: 128px;
  padding: 16px;
}

.pipeline-step span,
.latest-item span,
.advice-item span,
.empty-text {
  color: rgba(245, 239, 228, 0.55);
  font-size: 13px;
}

.pipeline-step strong {
  display: block;
  margin: 12px 0 8px;
  font-size: 28px;
  color: #f2ca76;
}

.pipeline-step p {
  margin: 0;
  color: rgba(245, 239, 228, 0.52);
  font-size: 12px;
  line-height: 1.6;
}

.latest-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.latest-item {
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.latest-item strong {
  color: #fff;
  line-height: 1.45;
  font-size: 13px;
}

.advice-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.advice-item {
  padding: 14px;
}

.advice-item strong {
  display: block;
  margin-bottom: 8px;
  color: #fff;
}

.advice-item span {
  line-height: 1.7;
}

@media (max-width: 1100px) {
  .metric-grid,
  .overview-grid,
  .advice-grid,
  .pipeline-row {
    grid-template-columns: 1fr;
  }
}
</style>
