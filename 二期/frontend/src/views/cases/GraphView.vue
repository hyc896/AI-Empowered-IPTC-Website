<template>
  <div class="graph-view">
    <aside class="graph-sidebar">
      <button class="back-button" @click="router.push('/case-platform')">返回案例平台</button>
      <div class="brand-block">
        <span class="eyebrow">Knowledge Graph</span>
        <h1>三本教材知识图谱</h1>
        <p>按教材、章节、节、知识点四层结构浏览，点击知识点可查看理论说明并跳转相关案例。</p>
      </div>

      <div class="book-list">
        <button
          v-for="book in books"
          :key="book.book_id"
          :class="['book-card', selectedBookId === book.book_id && 'active']"
          @click="selectBook(book.book_id)"
        >
          <strong>{{ book.book_name }}</strong>
          <span>{{ book.chapter_count }} 章 · {{ book.section_count }} 节 · {{ book.kp_count }} 个知识点</span>
        </button>
      </div>

      <div class="toolbar-card">
        <span class="eyebrow">View</span>
        <div class="tool-row">
          <button @click="fitGraph">适配视图</button>
          <button @click="reloadGraph">重新布局</button>
        </div>
        <label class="toggle-row">
          <input v-model="showKnowledgeLabels" type="checkbox" @change="renderGraph" />
          <span>显示知识点标签</span>
        </label>
      </div>
    </aside>

    <main :class="['graph-main', graphTransitioning && 'is-transitioning']">
      <header class="graph-header">
        <div>
          <span class="eyebrow">Current Book</span>
          <h2>{{ currentBook?.book_name || '知识图谱' }}</h2>
        </div>
        <div class="graph-stats">
          <span>{{ graphStats.nodes }} 节点</span>
          <span>{{ graphStats.edges }} 关系</span>
        </div>
      </header>

      <section :class="['graph-stage', selectedNode && 'has-selection']">
        <div class="graph-orbit" aria-hidden="true">
          <span></span>
          <span></span>
          <span></span>
        </div>
        <div class="transition-wash" aria-hidden="true"></div>
        <div v-if="loading" class="state-layer">
          <el-icon class="spinning" :size="34"><Loading /></el-icon>
          <p>正在加载知识图谱...</p>
        </div>
        <div v-else-if="errorMessage" class="state-layer error">
          <h3>知识图谱暂时无法加载</h3>
          <p>{{ errorMessage }}</p>
          <button @click="reloadGraph">重试</button>
        </div>
        <div v-else-if="!graphData.nodes.length" class="state-layer">
          <h3>当前教材暂无图谱数据</h3>
          <p>请检查知识点数据文件是否包含 book_id、chapter、section 和 name 字段。</p>
        </div>
        <div ref="chartEl" class="chart" />
      </section>
    </main>

    <aside class="detail-panel">
      <Transition name="detail-swap" mode="out-in">
        <div v-if="selectedNode" :key="selectedNode.id" class="detail-content">
          <div class="detail-head">
            <span :class="['type-pill', selectedNode.type]">{{ typeLabel(selectedNode.type) }}</span>
            <button class="close-button" @click="clearSelection">关闭</button>
          </div>
          <h3>{{ selectedNode.label }}</h3>
          <p v-if="selectedNode.type !== 'knowledge_point'" class="node-path">
            {{ nodeHint(selectedNode.type) }}
          </p>

          <template v-if="selectedNode.type === 'knowledge_point'">
            <div class="meta-line">
              <span>{{ kpDetail?.book_name || selectedNode.data?.book_name }}</span>
              <span>{{ kpDetail?.chapter || selectedNode.data?.chapter }}</span>
              <span>{{ kpDetail?.section || selectedNode.data?.section }}</span>
            </div>

            <section v-if="kpDetail?.theory_description" class="detail-section">
              <span>理论描述</span>
              <p>{{ kpDetail.theory_description }}</p>
            </section>
            <section v-if="kpDetail?.application_scenarios" class="detail-section">
              <span>应用场景</span>
              <p>{{ kpDetail.application_scenarios }}</p>
            </section>
            <section v-if="kpDetail?.typical_keywords" class="detail-section">
              <span>典型关键词</span>
              <p>{{ kpDetail.typical_keywords }}</p>
            </section>

            <button class="primary-action" @click="viewCasesForKP">查看相关案例</button>
          </template>
        </div>

        <div v-else key="empty" class="empty-detail">
          <span class="eyebrow">Node Detail</span>
          <h3>选择一个节点</h3>
          <p>点击教材、章节、节或知识点查看结构说明。点击知识点后，可以继续进入案例库检索相关教学案例。</p>
        </div>
      </Transition>

      <div class="legend">
        <div v-for="item in legendItems" :key="item.type" class="legend-item">
          <span :style="{ background: item.color }"></span>
          {{ item.label }}
        </div>
      </div>
    </aside>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Loading } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { graphAPI } from '@/api/index'

const router = useRouter()
const chartEl = ref(null)
let chartInstance = null
let resizeObserver = null

const loading = ref(false)
const errorMessage = ref('')
const books = ref([])
const selectedBookId = ref('')
const graphData = ref({ nodes: [], edges: [] })
const selectedNode = ref(null)
const kpDetail = ref(null)
const showKnowledgeLabels = ref(false)
const graphTransitioning = ref(false)
const selectedNodeId = ref('')
const activeNeighborIds = ref(new Set())

const NODE_COLORS = {
  book: '#c85b4a',
  chapter: '#d8a84d',
  section: '#5aa889',
  knowledge_point: '#5f8fd6',
}

const legendItems = [
  { type: 'book', color: NODE_COLORS.book, label: '教材' },
  { type: 'chapter', color: NODE_COLORS.chapter, label: '章' },
  { type: 'section', color: NODE_COLORS.section, label: '节' },
  { type: 'knowledge_point', color: NODE_COLORS.knowledge_point, label: '知识点' },
]

const currentBook = computed(() => books.value.find(book => book.book_id === selectedBookId.value))
const graphStats = computed(() => ({
  nodes: graphData.value.nodes.length,
  edges: graphData.value.edges.length,
}))

function typeLabel(type) {
  return { book: '教材', chapter: '章', section: '节', knowledge_point: '知识点' }[type] || type
}

function nodeHint(type) {
  return {
    book: '该节点代表一本教材，向下连接各章结构。',
    chapter: '该节点代表教材章节，向下连接本章各节。',
    section: '该节点代表教材节次，向下连接具体知识点。',
  }[type] || ''
}

function shortLabel(text = '', max = 14) {
  return text.length > max ? `${text.slice(0, max - 1)}…` : text
}

function nodeCategory(type) {
  return { book: 0, chapter: 1, section: 2, knowledge_point: 3 }[type] ?? 3
}

function pause(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

function isActiveNode(id) {
  return selectedNodeId.value === id || activeNeighborIds.value.has(id)
}

function updateActivePath(nodeId = '') {
  selectedNodeId.value = nodeId
  if (!nodeId) {
    activeNeighborIds.value = new Set()
    return
  }

  const related = new Set()
  graphData.value.edges.forEach(edge => {
    if (edge.source === nodeId) related.add(edge.target)
    if (edge.target === nodeId) related.add(edge.source)
  })
  activeNeighborIds.value = related
}

function buildOption() {
  const nodes = graphData.value.nodes.map(node => ({
    id: node.id,
    name: node.label,
    value: node.label,
    category: nodeCategory(node.type),
    symbolSize: selectedNodeId.value === node.id ? node.size + 9 : isActiveNode(node.id) ? node.size + 4 : node.size,
    itemStyle: {
      color: NODE_COLORS[node.type] || '#8b929b',
      borderColor: selectedNodeId.value === node.id ? '#fff4c7' : 'rgba(255,255,255,0.34)',
      borderWidth: selectedNodeId.value === node.id ? 3 : node.type === 'knowledge_point' ? 0 : 1,
      shadowBlur: selectedNodeId.value === node.id ? 30 : isActiveNode(node.id) ? 18 : 0,
      shadowColor: selectedNodeId.value === node.id ? 'rgba(255,228,150,0.72)' : 'rgba(214,177,95,0.28)',
      opacity: selectedNodeId.value && !isActiveNode(node.id) ? 0.34 : 1,
    },
    label: {
      show: node.type !== 'knowledge_point' || showKnowledgeLabels.value,
      color: '#f6efe4',
      fontSize: node.type === 'book' ? 14 : node.type === 'chapter' ? 12 : 10,
      formatter: () => shortLabel(node.label, node.type === 'book' ? 16 : 12),
    },
    _raw: node,
  }))

  const links = graphData.value.edges.map(edge => ({
    source: edge.source,
    target: edge.target,
    symbol: selectedNodeId.value && (edge.source === selectedNodeId.value || edge.target === selectedNodeId.value) ? ['none', 'arrow'] : 'none',
    symbolSize: 8,
    lineStyle: {
      color: selectedNodeId.value && (edge.source === selectedNodeId.value || edge.target === selectedNodeId.value)
        ? 'rgba(246,215,142,0.82)'
        : 'rgba(214,177,95,0.18)',
      width: selectedNodeId.value && (edge.source === selectedNodeId.value || edge.target === selectedNodeId.value) ? 2.4 : 1,
      opacity: selectedNodeId.value && edge.source !== selectedNodeId.value && edge.target !== selectedNodeId.value ? 0.1 : 0.72,
      curveness: selectedNodeId.value && (edge.source === selectedNodeId.value || edge.target === selectedNodeId.value) ? 0.18 : 0.08,
    },
  }))

  return {
    backgroundColor: 'transparent',
    animation: true,
    animationDuration: 1100,
    animationEasing: 'cubicOut',
    animationDurationUpdate: 980,
    animationEasingUpdate: 'quinticInOut',
    stateAnimation: {
      duration: 420,
      easing: 'cubicOut',
    },
    tooltip: {
      trigger: 'item',
      borderWidth: 0,
      backgroundColor: 'rgba(12,16,22,0.94)',
      textStyle: { color: '#f6efe4' },
      formatter: params => {
        if (params.dataType !== 'node') return ''
        const raw = params.data._raw
        return `<b>${raw.label}</b><br/>${typeLabel(raw.type)}`
      },
    },
    categories: legendItems.map(item => ({ name: item.label })),
    series: [{
      type: 'graph',
      layout: 'force',
      data: nodes,
      links,
      roam: true,
      draggable: true,
      focusNodeAdjacency: true,
      edgeSymbol: ['none', 'arrow'],
      edgeSymbolSize: [0, 7],
      universalTransition: true,
      force: {
        repulsion: graphData.value.nodes.length > 180 ? 520 : 360,
        gravity: selectedNodeId.value ? 0.032 : 0.045,
        edgeLength: selectedNodeId.value ? [88, 190] : [72, 170],
        layoutAnimation: true,
      },
      lineStyle: {
        color: 'source',
        opacity: 0.28,
      },
      emphasis: {
        focus: 'adjacency',
        scale: true,
        lineStyle: { width: 2.5, opacity: 0.64 },
      },
    }],
  }
}

function renderGraph(mode = 'replace') {
  if (!chartInstance) return
  chartInstance.setOption(buildOption(), {
    notMerge: mode === 'replace',
    replaceMerge: ['series'],
    lazyUpdate: false,
  })
  requestAnimationFrame(() => chartInstance?.resize())
}

async function loadBooks() {
  const res = await graphAPI.getBooks()
  const data = res.code === 200 ? res.data : (res.data || res || [])
  books.value = Array.isArray(data) ? data : []
  if (!selectedBookId.value && books.value.length) {
    selectedBookId.value = books.value[0].book_id
  }
}

async function loadGraph(bookId) {
  if (!chartInstance) return
  loading.value = true
  errorMessage.value = ''
  selectedNode.value = null
  kpDetail.value = null
  updateActivePath('')
  graphTransitioning.value = true
  chartInstance.setOption({
    series: [{
      type: 'graph',
      data: [],
      links: [],
    }],
  }, { replaceMerge: ['series'] })
  await pause(180)
  try {
    const res = await graphAPI.getGraphData(bookId)
    const data = res.code === 200 ? res.data : (res.data || { nodes: [], edges: [] })
    graphData.value = {
      nodes: Array.isArray(data.nodes) ? data.nodes : [],
      edges: Array.isArray(data.edges) ? data.edges : [],
    }
    renderGraph()
    await pause(720)
  } catch (error) {
    graphData.value = { nodes: [], edges: [] }
    errorMessage.value = error?.response?.data?.detail || error.message || '图谱接口请求失败'
  } finally {
    loading.value = false
    graphTransitioning.value = false
  }
}

async function selectBook(bookId) {
  selectedBookId.value = bookId
  await loadGraph(bookId)
}

async function reloadGraph() {
  await loadGraph(selectedBookId.value)
}

function fitGraph() {
  chartInstance?.dispatchAction({ type: 'restore' })
  chartInstance?.resize()
}

async function onNodeClick(params) {
  if (params.dataType !== 'node') return
  const raw = params.data._raw
  selectedNode.value = raw
  kpDetail.value = raw.data || null
  updateActivePath(raw.id)
  renderGraph('focus')
  const dataIndex = graphData.value.nodes.findIndex(node => node.id === raw.id)
  if (dataIndex >= 0) {
    chartInstance?.dispatchAction({ type: 'downplay', seriesIndex: 0 })
    chartInstance?.dispatchAction({ type: 'highlight', seriesIndex: 0, dataIndex })
  }

  if (raw.type === 'knowledge_point') {
    try {
      const res = await graphAPI.getKnowledgePointDetail(raw.id)
      kpDetail.value = res.code === 200 ? res.data : res
    } catch (e) {
      kpDetail.value = raw.data || null
    }
  }
}

function clearSelection() {
  selectedNode.value = null
  kpDetail.value = null
  updateActivePath('')
  chartInstance?.dispatchAction({ type: 'downplay', seriesIndex: 0 })
  renderGraph('focus')
}

function viewCasesForKP() {
  if (!selectedNode.value) return
  router.push({
    path: '/cases',
    query: { knowledge_point_name: selectedNode.value.label },
  })
}

function initChart() {
  if (!chartEl.value) return
  chartInstance = echarts.init(chartEl.value, null, { renderer: 'canvas' })
  chartInstance.on('click', onNodeClick)
  resizeObserver = new ResizeObserver(() => chartInstance?.resize())
  resizeObserver.observe(chartEl.value)
}

onMounted(async () => {
  await nextTick()
  initChart()
  try {
    await loadBooks()
    await loadGraph(selectedBookId.value)
  } catch (error) {
    errorMessage.value = error?.response?.data?.detail || error.message || '图谱初始化失败'
  }
})

onUnmounted(() => {
  resizeObserver?.disconnect()
  chartInstance?.dispose()
})
</script>

<style scoped>
.graph-view {
  height: 100vh;
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr) 340px;
  background:
    linear-gradient(135deg, rgba(13, 17, 22, 0.96), rgba(28, 30, 33, 0.92)),
    url('@/assets/bg-main.webp') center/cover no-repeat fixed;
  color: #f6efe4;
  overflow: hidden;
}

.graph-sidebar,
.detail-panel {
  min-height: 0;
  overflow-y: auto;
  background: rgba(9, 12, 16, 0.82);
  backdrop-filter: blur(20px);
  border-color: rgba(214, 177, 95, 0.16);
}

.graph-sidebar {
  padding: 22px 18px;
  border-right: 1px solid rgba(214, 177, 95, 0.16);
}

.detail-panel {
  padding: 22px 18px;
  border-left: 1px solid rgba(214, 177, 95, 0.16);
}

.back-button,
.book-card,
.tool-row button,
.close-button,
.primary-action,
.state-layer button {
  border-radius: 8px;
  border: 1px solid rgba(214, 177, 95, 0.24);
  background: rgba(255, 255, 255, 0.045);
  color: rgba(246, 239, 228, 0.78);
  cursor: pointer;
  transition: all 0.18s ease;
}

.back-button {
  height: 36px;
  padding: 0 14px;
  margin-bottom: 22px;
}

.back-button:hover,
.tool-row button:hover,
.close-button:hover,
.state-layer button:hover {
  border-color: rgba(214, 177, 95, 0.55);
  color: #fff;
  background: rgba(214, 177, 95, 0.08);
}

.eyebrow {
  display: block;
  color: #d6b15f;
  font-size: 11px;
  letter-spacing: 0;
}

.brand-block h1,
.graph-header h2,
.detail-panel h3,
.empty-detail h3 {
  margin: 4px 0 0;
  line-height: 1.22;
  letter-spacing: 0;
}

.brand-block h1 {
  font-size: 25px;
}

.brand-block p,
.empty-detail p,
.node-path {
  margin: 12px 0 0;
  color: rgba(246, 239, 228, 0.56);
  line-height: 1.75;
  font-size: 13px;
}

.book-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin: 22px 0;
}

.book-card {
  width: 100%;
  min-height: 94px;
  padding: 14px;
  text-align: left;
  position: relative;
  overflow: hidden;
}

.book-card strong,
.book-card span {
  display: block;
  position: relative;
  z-index: 1;
}

.book-card strong {
  color: #fff;
  line-height: 1.45;
  font-size: 14px;
}

.book-card span {
  margin-top: 8px;
  color: rgba(246, 239, 228, 0.5);
  font-size: 12px;
}

.book-card.active {
  background: rgba(214, 177, 95, 0.16);
  border-color: rgba(214, 177, 95, 0.56);
  box-shadow: inset 3px 0 0 #d6b15f;
}

.book-card::before {
  content: "";
  position: absolute;
  inset: -40% auto -40% -70%;
  width: 64%;
  background: linear-gradient(90deg, transparent, rgba(255, 238, 186, 0.16), transparent);
  transform: skewX(-18deg);
  transition: left 0.65s cubic-bezier(0.16, 1, 0.3, 1);
}

.book-card:hover::before,
.book-card.active::before {
  left: 108%;
}

.toolbar-card {
  padding: 14px;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.045);
}

.tool-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-top: 12px;
}

.tool-row button,
.state-layer button {
  height: 34px;
}

.toggle-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  color: rgba(246, 239, 228, 0.62);
  font-size: 13px;
}

.graph-main {
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.graph-header {
  min-height: 82px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 18px 24px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(12, 16, 22, 0.56);
  backdrop-filter: blur(18px);
}

.graph-header h2 {
  font-size: 22px;
}

.graph-stats {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.graph-stats span {
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.06);
  color: rgba(246, 239, 228, 0.64);
  font-size: 12px;
}

.graph-stage {
  flex: 1;
  min-height: 0;
  position: relative;
  overflow: hidden;
}

.chart {
  width: 100%;
  height: 100%;
  position: relative;
  z-index: 1;
  transition:
    opacity 0.28s ease,
    filter 0.58s cubic-bezier(0.16, 1, 0.3, 1),
    transform 0.58s cubic-bezier(0.16, 1, 0.3, 1);
}

.graph-main.is-transitioning .chart {
  opacity: 0.38;
  filter: blur(2px) saturate(0.72);
  transform: scale(0.985);
}

.graph-orbit {
  position: absolute;
  inset: 34px;
  z-index: 0;
  pointer-events: none;
  opacity: 0.72;
  transition: opacity 0.36s ease;
}

.graph-orbit span {
  position: absolute;
  border-radius: 50%;
  border: 1px solid rgba(214, 177, 95, 0.13);
  box-shadow: 0 0 48px rgba(95, 143, 214, 0.09);
  animation: orbit-drift 16s linear infinite;
}

.graph-orbit span:nth-child(1) {
  inset: 8% 18%;
}

.graph-orbit span:nth-child(2) {
  inset: 18% 8%;
  animation-duration: 22s;
  animation-direction: reverse;
  border-color: rgba(90, 168, 137, 0.12);
}

.graph-orbit span:nth-child(3) {
  inset: 28% 28%;
  animation-duration: 12s;
  border-color: rgba(95, 143, 214, 0.12);
}

.graph-stage.has-selection .graph-orbit {
  opacity: 0.92;
}

.transition-wash {
  position: absolute;
  inset: 0;
  z-index: 2;
  pointer-events: none;
  opacity: 0;
  background:
    radial-gradient(circle at 50% 48%, rgba(214, 177, 95, 0.22), transparent 34%),
    linear-gradient(105deg, transparent 10%, rgba(255, 238, 186, 0.12) 46%, transparent 70%);
  transform: translateX(-32%) scaleX(0.72);
}

.graph-main.is-transitioning .transition-wash {
  animation: graph-wash 0.92s cubic-bezier(0.16, 1, 0.3, 1);
}

.state-layer {
  position: absolute;
  inset: 0;
  z-index: 3;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  text-align: center;
  padding: 32px;
  background: rgba(13, 17, 22, 0.76);
}

.state-layer p {
  margin: 0;
  max-width: 420px;
  color: rgba(246, 239, 228, 0.6);
  line-height: 1.7;
}

.state-layer.error h3 {
  margin: 0;
  color: #fff;
}

.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@keyframes graph-wash {
  0% {
    opacity: 0;
    transform: translateX(-36%) scaleX(0.72);
  }
  35% {
    opacity: 1;
  }
  100% {
    opacity: 0;
    transform: translateX(42%) scaleX(1.1);
  }
}

@keyframes orbit-drift {
  from { transform: rotate(0deg) scale(1); }
  50% { transform: rotate(180deg) scale(1.035); }
  to { transform: rotate(360deg) scale(1); }
}

.detail-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.type-pill {
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  background: rgba(255, 255, 255, 0.07);
  color: rgba(246, 239, 228, 0.62);
}

.type-pill.book { color: #f0a39a; background: rgba(200, 91, 74, 0.18); }
.type-pill.chapter { color: #ebcb87; background: rgba(216, 168, 77, 0.16); }
.type-pill.section { color: #a8d8c4; background: rgba(90, 168, 137, 0.16); }
.type-pill.knowledge_point { color: #aac8f2; background: rgba(95, 143, 214, 0.16); }

.close-button {
  height: 30px;
  padding: 0 10px;
  font-size: 12px;
}

.detail-panel h3 {
  margin-top: 16px;
  font-size: 20px;
}

.meta-line {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin: 14px 0;
}

.meta-line span {
  padding: 8px 10px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.05);
  color: rgba(246, 239, 228, 0.62);
  font-size: 12px;
}

.detail-section {
  margin-top: 18px;
}

.detail-section > span {
  display: block;
  color: #d6b15f;
  font-size: 12px;
  margin-bottom: 8px;
}

.detail-section p {
  margin: 0;
  color: rgba(246, 239, 228, 0.7);
  font-size: 13px;
  line-height: 1.75;
}

.primary-action {
  width: 100%;
  height: 40px;
  margin-top: 22px;
  background: #d6b15f;
  border-color: #d6b15f;
  color: #151515;
  font-weight: 700;
}

.empty-detail {
  padding: 16px 0 22px;
}

.detail-content,
.empty-detail {
  transform-origin: 50% 16px;
}

.detail-swap-enter-active,
.detail-swap-leave-active {
  transition:
    opacity 0.28s ease,
    transform 0.36s cubic-bezier(0.16, 1, 0.3, 1),
    filter 0.36s ease;
}

.detail-swap-enter-from {
  opacity: 0;
  filter: blur(8px);
  transform: translateY(18px) scale(0.98);
}

.detail-swap-leave-to {
  opacity: 0;
  filter: blur(6px);
  transform: translateY(-12px) scale(0.99);
}

.legend {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-top: 22px;
  padding-top: 18px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  color: rgba(246, 239, 228, 0.58);
  font-size: 12px;
}

.legend-item span {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

@media (max-width: 1120px) {
  .graph-view {
    grid-template-columns: 280px minmax(0, 1fr);
  }

  .detail-panel {
    position: fixed;
    top: 0;
    right: 0;
    bottom: 0;
    z-index: 8;
    width: 340px;
    transform: translateX(0);
  }
}

@media (max-width: 820px) {
  .graph-view {
    grid-template-columns: 1fr;
  }

  .graph-sidebar {
    max-height: 42vh;
    border-right: 0;
    border-bottom: 1px solid rgba(214, 177, 95, 0.16);
  }

  .graph-main {
    min-height: 58vh;
  }
}

@media (prefers-reduced-motion: reduce) {
  .chart,
  .book-card,
  .detail-swap-enter-active,
  .detail-swap-leave-active {
    transition: none;
  }

  .graph-orbit span,
  .graph-main.is-transitioning .transition-wash,
  .spinning {
    animation: none;
  }
}
</style>
