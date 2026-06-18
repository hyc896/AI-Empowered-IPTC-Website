<template>
  <div class="mindmap-view">
    <!-- 顶部导航 -->
    <div class="header">
      <div class="header-left">
        <el-button text style="color:rgba(255,255,255,0.6)" @click="router.push('/case-platform')">
          ← 返回
        </el-button>
        <span class="title">思维导图</span>
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
        <el-button size="small" class="reset-btn" @click="resetView">重置视图</el-button>
        <span class="tip">点击节点展开/收起</span>
      </div>
    </div>

    <!-- 图表区域 -->
    <div class="chart-wrap" ref="chartWrap">
      <div v-if="loading" class="loading-mask">
        <el-icon class="spinning" :size="32"><Loading /></el-icon>
        <p>加载思维导图中...</p>
      </div>
      <div ref="chartEl" class="chart" />
    </div>

    <!-- 右侧详情面板 -->
    <transition name="slide-right">
      <div v-if="selectedKP" class="detail-panel">
        <div class="panel-header">
          <span class="panel-badge">知识点</span>
          <el-button text style="color:rgba(255,255,255,0.4)" @click="selectedKP = null">✕</el-button>
        </div>
        <h3 class="panel-title">{{ selectedKP.name }}</h3>
        <div class="panel-path">{{ selectedKP.book_name }} › {{ selectedKP.chapter }} › {{ selectedKP.section }}</div>
        <div class="panel-section" v-if="selectedKP.theory_description">
          <div class="section-label">理论描述</div>
          <p>{{ selectedKP.theory_description }}</p>
        </div>
        <div class="panel-section" v-if="selectedKP.application_scenarios">
          <div class="section-label">应用场景</div>
          <p>{{ selectedKP.application_scenarios }}</p>
        </div>
        <div class="panel-section" v-if="selectedKP.typical_keywords">
          <div class="section-label">典型关键词</div>
          <p class="keywords">{{ selectedKP.typical_keywords }}</p>
        </div>
        <el-button class="view-cases-btn" @click="viewCases">
          查看相关案例 →
        </el-button>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { Loading } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { graphAPI } from '@/api/index'

const router = useRouter()
const chartEl = ref(null)
const chartWrap = ref(null)
let chartInstance = null

const loading = ref(false)
const books = ref([])
const selectedBookId = ref('')
const selectedKP = ref(null)

const bookOptions = computed(() =>
  [{ label: '全部', value: '' }, ...books.value.map(b => ({
    label: `${b.book_name}`,
    value: b.book_id
  }))]
)

const NODE_COLORS = {
  book: '#c0392b',
  chapter: '#e67e22',
  section: '#f1c40f',
  knowledge_point: '#3498db'
}

function nodesToTree(nodes, edges) {
  if (!nodes || !nodes.length) return null

  const nodeMap = {}
  nodes.forEach(n => { nodeMap[n.id] = { ...n, children: [] } })

  const childIds = new Set()
  edges.forEach(e => {
    const parent = nodeMap[e.source]
    const child = nodeMap[e.target]
    if (parent && child) {
      parent.children.push(child)
      childIds.add(e.target)
    }
  })

  const roots = nodes.filter(n => !childIds.has(n.id))

  if (roots.length === 0 && nodes.length > 0) return nodeMap[nodes[0].id]
  if (roots.length === 1) return nodeMap[roots[0].id]

  return {
    id: 'root',
    label: '思政理论课',
    type: 'root',
    size: 70,
    children: roots.map(r => nodeMap[r.id])
  }
}

function treeToECharts(node) {
  if (!node) return null
  const color = NODE_COLORS[node.type] || '#999'
  return {
    name: node.label || node.id,
    value: node.id,
    _type: node.type,
    _raw: node,
    symbol: 'circle',
    symbolSize: node.size || 20,
    itemStyle: { color, borderColor: 'rgba(255,255,255,0.2)', borderWidth: 1 },
    label: {
      show: true,
      color: '#fff',
      fontSize: node.type === 'root' ? 14 : node.type === 'book' ? 13 : node.type === 'chapter' ? 11 : 10,
      formatter: params => {
        const t = params.name
        return t.length > 12 ? t.slice(0, 11) + '…' : t
      }
    },
    children: node.children ? node.children.map(treeToECharts) : []
  }
}

function buildOption(treeData) {
  return {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      formatter: params => `<b>${params.name}</b>`,
      backgroundColor: 'rgba(20,5,5,0.9)',
      borderColor: 'rgba(192,57,43,0.4)',
      textStyle: { color: '#fff' }
    },
    series: [{
      type: 'tree',
      data: [treeData],
      top: '5%',
      left: '5%',
      bottom: '5%',
      right: '5%',
      layout: 'radial',
      symbol: 'circle',
      initialTreeDepth: 2,
      roam: true,
      expandAndCollapse: true,
      animationDuration: 550,
      animationDurationUpdate: 750,
      lineStyle: {
        color: 'rgba(255,255,255,0.15)',
        width: 1,
        curveness: 0.5
      },
      emphasis: {
        focus: 'relative',
        itemStyle: { shadowBlur: 10, shadowColor: 'rgba(255,215,0,0.4)' }
      }
    }]
  }
}

async function loadMindMap(bookId) {
  if (!chartInstance) return
  loading.value = true
  selectedKP.value = null

  try {
    const res = await graphAPI.getGraphData(bookId)
    const { nodes, edges } = (res.code === 200 ? res.data : res) || { nodes: [], edges: [] }
    const tree = nodesToTree(nodes, edges)
    if (tree) {
      const eTree = treeToECharts(tree)
      chartInstance.setOption(buildOption(eTree), true)
    }
  } finally {
    loading.value = false
  }
}

function onBookChange(val) {
  selectedBookId.value = val
  loadMindMap(val)
}

function resetView() {
  chartInstance?.dispatchAction({ type: 'restore' })
}

async function onNodeClick(params) {
  if (params.componentType !== 'series') return
  const raw = params.data?._raw
  if (!raw || raw.type !== 'knowledge_point') {
    selectedKP.value = null
    return
  }

  try {
    const res = await graphAPI.getKnowledgePointDetail(raw.id)
    const detail = res.code === 200 ? res.data : res
    selectedKP.value = { ...detail, id: raw.id }
  } catch (e) {
    selectedKP.value = { name: raw.label, id: raw.id, ...(raw.data || {}) }
  }
}

function viewCases() {
  if (!selectedKP.value) return
  router.push(`/cases?search=${encodeURIComponent(selectedKP.value.name)}`)
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

  await loadMindMap('')
})

onUnmounted(() => {
  chartInstance?.dispose()
})
</script>

<style scoped>
.mindmap-view {
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
.header-right { display: flex; align-items: center; gap: 12px; flex-shrink: 0; }
.tip { font-size: 12px; color: rgba(255,255,255,0.35); }
.reset-btn {
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.1);
  color: rgba(255,255,255,0.6);
  font-size: 12px;
}
.reset-btn:hover { background: rgba(255,255,255,0.1); color: #fff; }

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

/* Chart */
.chart-wrap {
  flex: 1;
  position: relative;
  overflow: hidden;
}
.chart { width: 100%; height: 100%; }
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
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  width: 320px;
  background: rgba(15,5,5,0.9);
  backdrop-filter: blur(20px);
  border-left: 1px solid rgba(192,57,43,0.2);
  padding: 24px 20px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
  z-index: 20;
}
.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.panel-badge {
  font-size: 11px;
  padding: 2px 10px;
  border-radius: 10px;
  background: rgba(52,152,219,0.2);
  color: #64b5f6;
}
.panel-title {
  font-size: 18px;
  font-weight: 700;
  color: #fff;
  line-height: 1.4;
  margin: 0;
}
.panel-path {
  font-size: 12px;
  color: rgba(255,215,0,0.5);
  line-height: 1.5;
}
.panel-section { display: flex; flex-direction: column; gap: 6px; }
.section-label {
  font-size: 11px;
  color: rgba(255,215,0,0.6);
  text-transform: uppercase;
  letter-spacing: 1px;
}
.panel-section p { font-size: 13px; color: rgba(255,255,255,0.7); line-height: 1.6; margin: 0; }
.keywords { word-break: break-all; }
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
</style>
