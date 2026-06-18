<template>
  <div class="graph-view">
    <!-- 顶部导航 -->
    <div class="header">
      <div class="header-left">
        <el-button text style="color:rgba(255,255,255,0.6)" @click="router.push('/case-platform')">
          ← 返回
        </el-button>
        <span class="title">知识图谱</span>
      </div>
      <div class="header-center">
        <el-segmented
          v-if="books.length"
          v-model="selectedBookId"
          :options="bookOptions"
          @change="onBookChange"
          class="book-tabs"
        />
      </div>
      <div class="header-right">
        <span class="tip">点击节点查看详情 · 滚轮缩放</span>
      </div>
    </div>

    <!-- 主体区域 -->
    <div class="main">
      <!-- 图谱区域 -->
      <div class="chart-wrap" ref="chartWrap">
        <div v-if="loading" class="loading-mask">
          <el-icon class="spinning" :size="32"><Loading /></el-icon>
          <p>加载知识图谱中...</p>
        </div>
        <div ref="chartEl" class="chart" />
      </div>

      <!-- 右侧详情面板 -->
      <transition name="slide-right">
        <div v-if="selectedNode" class="detail-panel">
          <div class="panel-header">
            <span class="panel-type-badge" :class="selectedNode.type">{{ typeLabel(selectedNode.type) }}</span>
            <el-button text style="color:rgba(255,255,255,0.4)" @click="selectedNode = null">✕</el-button>
          </div>
          <h3 class="panel-title">{{ selectedNode.label }}</h3>

          <template v-if="selectedNode.type === 'knowledge_point' && kpDetail">
            <div class="panel-section" v-if="kpDetail.theory_description">
              <div class="section-label">理论描述</div>
              <p>{{ kpDetail.theory_description }}</p>
            </div>
            <div class="panel-section" v-if="kpDetail.application_scenarios">
              <div class="section-label">应用场景</div>
              <p>{{ kpDetail.application_scenarios }}</p>
            </div>
            <div class="panel-section" v-if="kpDetail.typical_keywords">
              <div class="section-label">典型关键词</div>
              <p>{{ kpDetail.typical_keywords }}</p>
            </div>
            <el-button class="view-cases-btn" @click="viewCasesForKP">
              查看相关案例 →
            </el-button>
          </template>

          <template v-else-if="selectedNode.type === 'book'">
            <p class="panel-desc">点击展开该书的章节结构</p>
          </template>
          <template v-else-if="selectedNode.type === 'chapter'">
            <p class="panel-desc">展开后可查看本章各节知识点</p>
          </template>
          <template v-else-if="selectedNode.type === 'section'">
            <p class="panel-desc">展开后可查看本节知识点详情</p>
          </template>
        </div>
      </transition>
    </div>

    <!-- 图例 -->
    <div class="legend">
      <div class="legend-item" v-for="item in legendItems" :key="item.type">
        <span class="legend-dot" :style="{ background: item.color }"></span>
        <span>{{ item.label }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { Loading } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { graphAPI, caseAPI } from '@/api/index'

const router = useRouter()
const chartEl = ref(null)
const chartWrap = ref(null)
let chartInstance = null

const loading = ref(false)
const books = ref([])
const selectedBookId = ref('')
const selectedNode = ref(null)
const kpDetail = ref(null)

const NODE_COLORS = {
  book: '#c0392b',
  chapter: '#e67e22',
  section: '#f1c40f',
  knowledge_point: '#3498db'
}

const legendItems = [
  { type: 'book', color: NODE_COLORS.book, label: '教材' },
  { type: 'chapter', color: NODE_COLORS.chapter, label: '章' },
  { type: 'section', color: NODE_COLORS.section, label: '节' },
  { type: 'knowledge_point', color: NODE_COLORS.knowledge_point, label: '知识点' }
]

const bookOptions = computed(() =>
  [{ label: '全部', value: '' }, ...books.value.map(b => ({
    label: `${b.book_name} (${b.kp_count})`,
    value: b.book_id
  }))]
)

function typeLabel(type) {
  return { book: '教材', chapter: '章', section: '节', knowledge_point: '知识点' }[type] || type
}

function buildEChartsOption(nodes, edges) {
  const eNodes = nodes.map(n => ({
    id: n.id,
    name: n.label,
    value: n.label,
    symbolSize: n.size,
    itemStyle: { color: NODE_COLORS[n.type] || '#888' },
    label: {
      show: n.type !== 'knowledge_point' || nodes.length < 100,
      fontSize: n.type === 'book' ? 14 : n.type === 'chapter' ? 12 : 10,
      color: '#fff',
      formatter: params => {
        const text = params.name
        return text.length > 10 ? text.slice(0, 9) + '…' : text
      }
    },
    _raw: n
  }))

  const eEdges = edges.map(e => ({
    source: e.source,
    target: e.target,
    lineStyle: { color: 'rgba(255,255,255,0.12)', width: 1 }
  }))

  return {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      formatter: params => {
        if (params.dataType === 'node') {
          return `<b>${params.name}</b><br/>${typeLabel(params.data._raw?.type || '')}`
        }
        return ''
      },
      backgroundColor: 'rgba(20,5,5,0.9)',
      borderColor: 'rgba(192,57,43,0.4)',
      textStyle: { color: '#fff' }
    },
    series: [{
      type: 'graph',
      layout: 'force',
      data: eNodes,
      links: eEdges,
      roam: true,
      draggable: true,
      force: {
        repulsion: 300,
        gravity: 0.05,
        edgeLength: [80, 200],
        layoutAnimation: true
      },
      emphasis: {
        focus: 'adjacency',
        lineStyle: { width: 2 }
      },
      lineStyle: { color: 'rgba(255,255,255,0.12)', curveness: 0.1 },
      edgeSymbol: ['none', 'none']
    }]
  }
}

async function loadGraph(bookId) {
  if (!chartInstance) return
  loading.value = true
  selectedNode.value = null
  kpDetail.value = null

  try {
    const res = await graphAPI.getGraphData(bookId)
    const { nodes, edges } = (res.code === 200 ? res.data : res) || { nodes: [], edges: [] }
    chartInstance.setOption(buildEChartsOption(nodes, edges), true)
  } finally {
    loading.value = false
  }
}

function onBookChange(val) {
  selectedBookId.value = val
  loadGraph(val)
}

async function onNodeClick(params) {
  if (params.dataType !== 'node') return
  const raw = params.data._raw
  selectedNode.value = raw
  kpDetail.value = null

  if (raw.type === 'knowledge_point') {
    try {
      const res = await graphAPI.getKnowledgePointDetail(raw.id)
      kpDetail.value = res.code === 200 ? res.data : res
    } catch (e) {
      kpDetail.value = raw.data || null
    }
  }
}

function viewCasesForKP() {
  if (!selectedNode.value) return
  router.push(`/cases?search=${encodeURIComponent(selectedNode.value.label)}`)
}

function initChart() {
  if (!chartEl.value) return
  chartInstance = echarts.init(chartEl.value, null, { renderer: 'canvas' })
  chartInstance.on('click', onNodeClick)

  const ro = new ResizeObserver(() => chartInstance?.resize())
  ro.observe(chartWrap.value)
}

onMounted(async () => {
  await nextTick()
  initChart()

  try {
    const res = await graphAPI.getBooks()
    books.value = res.code === 200 ? res.data : (res.data || res || [])
  } catch (e) {
    books.value = []
  }

  await loadGraph('')
})

onUnmounted(() => {
  chartInstance?.dispose()
})
</script>

<style scoped>
.graph-view {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: linear-gradient(160deg, #2d0505 0%, #1a0a0a 40%, #0d0505 100%);
  color: #fff;
  overflow: hidden;
}

/* Header */
.header {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 60px;
  padding: 0 24px;
  background: rgba(0,0,0,0.4);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(192,57,43,0.2);
  gap: 16px;
}
.header-left { display: flex; align-items: center; gap: 12px; flex-shrink: 0; }
.title { font-size: 16px; font-weight: 700; color: #ffd700; }
.header-center { flex: 1; display: flex; justify-content: center; }
.header-right { flex-shrink: 0; }
.tip { font-size: 12px; color: rgba(255,255,255,0.35); }

/* Book tabs */
.book-tabs :deep(.el-segmented) {
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(192,57,43,0.2);
}
.book-tabs :deep(.el-segmented__item) {
  color: rgba(255,255,255,0.55);
  font-size: 12px;
}
.book-tabs :deep(.el-segmented__item.is-selected) {
  background: rgba(192,57,43,0.4);
  color: #fff;
}

/* Main */
.main {
  flex: 1;
  display: flex;
  overflow: hidden;
  position: relative;
}
.chart-wrap {
  flex: 1;
  position: relative;
  overflow: hidden;
}
.chart {
  width: 100%;
  height: 100%;
}
.loading-mask {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: rgba(13,5,5,0.7);
  z-index: 10;
  gap: 12px;
  color: rgba(255,255,255,0.6);
}
.spinning { animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* Detail Panel */
.detail-panel {
  width: 320px;
  flex-shrink: 0;
  background: rgba(15,5,5,0.85);
  backdrop-filter: blur(20px);
  border-left: 1px solid rgba(192,57,43,0.2);
  padding: 24px 20px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.panel-type-badge {
  font-size: 11px;
  padding: 2px 10px;
  border-radius: 10px;
  background: rgba(255,255,255,0.08);
  color: rgba(255,255,255,0.5);
}
.panel-type-badge.book { background: rgba(192,57,43,0.25); color: #e57373; }
.panel-type-badge.chapter { background: rgba(230,126,34,0.2); color: #ffb74d; }
.panel-type-badge.section { background: rgba(241,196,15,0.15); color: #fff176; }
.panel-type-badge.knowledge_point { background: rgba(52,152,219,0.2); color: #64b5f6; }

.panel-title {
  font-size: 18px;
  font-weight: 700;
  color: #fff;
  line-height: 1.4;
  margin: 0;
}
.panel-desc { font-size: 13px; color: rgba(255,255,255,0.4); }
.panel-section { display: flex; flex-direction: column; gap: 6px; }
.section-label {
  font-size: 11px;
  color: rgba(255,215,0,0.6);
  text-transform: uppercase;
  letter-spacing: 1px;
}
.panel-section p { font-size: 13px; color: rgba(255,255,255,0.7); line-height: 1.6; margin: 0; }
.view-cases-btn {
  margin-top: 8px;
  background: rgba(192,57,43,0.2);
  border: 1px solid rgba(192,57,43,0.4);
  color: #ff8a65;
  font-size: 13px;
  width: 100%;
}
.view-cases-btn:hover {
  background: rgba(192,57,43,0.35);
  color: #ffccbc;
}

/* Slide transition */
.slide-right-enter-active, .slide-right-leave-active { transition: transform 0.25s ease, opacity 0.25s; }
.slide-right-enter-from, .slide-right-leave-to { transform: translateX(40px); opacity: 0; }

/* Legend */
.legend {
  flex-shrink: 0;
  display: flex;
  gap: 20px;
  padding: 10px 24px;
  background: rgba(0,0,0,0.3);
  border-top: 1px solid rgba(255,255,255,0.05);
}
.legend-item { display: flex; align-items: center; gap: 6px; font-size: 12px; color: rgba(255,255,255,0.5); }
.legend-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
</style>
