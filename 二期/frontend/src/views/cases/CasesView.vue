<template>
  <div class="cases-view">
    <header class="topbar">
      <button class="ghost-button" @click="router.push('/case-platform')">返回案例平台</button>
      <div class="title-block">
        <span class="eyebrow">Teaching Case Library</span>
        <h1>教学案例库</h1>
      </div>
      <div class="region-tabs" aria-label="案例地区筛选">
        <button
          v-for="item in regionOptions"
          :key="item.value"
          :class="['region-tab', region === item.value && 'active']"
          @click="setRegion(item.value)"
        >
          <span>{{ item.label }}</span>
          <strong>{{ regionCounts[item.value] ?? '-' }}</strong>
        </button>
      </div>
      <el-input
        v-model="search"
        placeholder="搜索标题、摘要、知识点"
        clearable
        class="search-input"
        @keyup.enter="doSearch"
        @clear="doSearch"
      >
        <template #suffix>
          <el-icon class="search-icon" @click="doSearch"><Search /></el-icon>
        </template>
      </el-input>
    </header>

    <main class="library-shell">
      <aside class="knowledge-panel">
        <div class="panel-head">
          <div>
            <span class="eyebrow">Knowledge Map</span>
            <h2>知识点筛选</h2>
          </div>
          <button v-if="selectedKpId" class="clear-button" @click="clearKnowledge">清除</button>
        </div>

        <div v-if="treeLoading" class="state-panel">知识点加载中...</div>
        <div v-else-if="!treeData.length" class="state-panel">
          暂未读取到知识点层级，请先检查知识点数据文件。
        </div>
        <el-tree
          v-else
          ref="treeRef"
          :data="treeData"
          node-key="id"
          :props="{ label: 'label', children: 'children' }"
          highlight-current
          default-expand-all
          class="kp-tree"
          @node-click="onNodeClick"
        >
          <template #default="{ node, data }">
            <span :class="['tree-node', data.isKp && 'leaf']">
              <span class="node-label">{{ node.label }}</span>
              <span v-if="data.case_count !== undefined" class="kp-count">{{ data.case_count }}</span>
            </span>
          </template>
        </el-tree>
      </aside>

      <section class="case-panel">
        <div class="case-toolbar">
          <div>
            <span class="eyebrow">Results</span>
            <h2>{{ currentRegionLabel }}案例</h2>
          </div>
          <div class="result-meta">
            <span>共 {{ total }} 条</span>
            <span v-if="selectedKpName">知识点：{{ selectedKpName }}</span>
          </div>
        </div>

        <div v-if="loading" class="state-panel">案例加载中...</div>
        <div v-else-if="!cases.length" class="empty-panel">
          <h3>{{ emptyTitle }}</h3>
          <p>{{ emptyText }}</p>
        </div>
        <div v-else class="case-grid">
          <article v-for="c in cases" :key="c.id" class="case-card" @click="router.push(`/cases/${c.id}`)">
            <div class="card-tags">
              <span class="tag region-tag">{{ normalizeRegion(c.primary_region) }}</span>
              <span
                v-for="kp in getKnowledgeLabels(c).slice(0, 2)"
                :key="kp"
                class="tag knowledge-tag"
              >
                {{ kp }}
              </span>
            </div>
            <h3>{{ c.title }}</h3>
            <p>{{ excerpt(c.summary || c.content) }}</p>
            <footer>
              <span>生成时间：{{ formatDate(c.created_at || c.createdAt) }}</span>
              <span v-if="c.published_at || c.publishDate">素材时间：{{ formatDate(c.published_at || c.publishDate) }}</span>
            </footer>
          </article>
        </div>

        <div class="pagination">
          <el-pagination
            v-model:current-page="page"
            :page-size="pageSize"
            :total="total"
            layout="prev, pager, next"
            background
            size="small"
            @current-change="loadCases"
          />
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { Search } from '@element-plus/icons-vue'
import { caseAPI } from '@/api/index'

const router = useRouter()
const route = useRoute()

const regionOptions = [
  { label: '全部', value: 'all' },
  { label: '全国', value: 'national' },
  { label: '上海', value: 'shanghai' },
]

const search = ref(route.query.search || '')
const page = ref(1)
const pageSize = 20
const total = ref(0)
const cases = ref([])
const loading = ref(false)
const treeLoading = ref(true)
const treeData = ref([])
const treeRef = ref(null)
const selectedKpId = ref(null)
const selectedKpName = ref(null)
const region = ref('all')
const regionCounts = ref({ all: 0, national: 0, shanghai: 0 })

const currentRegionLabel = computed(() => {
  return regionOptions.find(item => item.value === region.value)?.label || '全部'
})

const emptyTitle = computed(() => {
  if (region.value === 'shanghai') return '暂时没有上海案例'
  if (region.value === 'national') return '暂时没有全国案例'
  return '暂时没有案例'
})

const emptyText = computed(() => {
  if (region.value === 'shanghai') return '上海案例需要先采集上海源，再执行上海范围的撞库匹配和案例生成。'
  if (region.value === 'national') return '全国案例需要先采集全国源，再执行全国范围的撞库匹配和案例生成。'
  return '可以在管理员工作台执行采集、撞库匹配和案例生成。'
})

function scopeParams() {
  return region.value === 'all' ? {} : { scope: region.value }
}

function normalizeRegion(value) {
  if (value === 'shanghai') return '上海'
  if (value === 'national') return '全国'
  return value || '全国'
}

function getKnowledgeLabels(item) {
  if (Array.isArray(item.related_knowledge_points)) {
    return item.related_knowledge_points.map(kp => typeof kp === 'string' ? kp : kp.name).filter(Boolean)
  }
  if (Array.isArray(item.knowledgePoints)) return item.knowledgePoints.filter(Boolean)
  return []
}

function excerpt(text = '') {
  const clean = String(text).replace(/\s+/g, ' ').trim()
  return clean.length > 96 ? `${clean.slice(0, 96)}...` : clean
}

function formatDate(value) {
  if (!value) return '未记录'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value).slice(0, 10)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function toTreeData(books = []) {
  return books
    .filter(book => book && (book.book_name || book.chapters?.length))
    .map(book => ({
      id: `book_${book.book_id || book.book_name}`,
      label: book.book_name || '思政知识点',
      case_count: book.case_count,
      children: (book.chapters || []).map(chapter => ({
        id: `chapter_${chapter.id || chapter.label}`,
        label: chapter.label || '全部知识点',
        case_count: chapter.case_count,
        children: (chapter.sections || []).map(section => ({
          id: `section_${section.id || section.label}`,
          label: section.label || '未分组知识点',
          case_count: section.case_count,
          children: (section.knowledge_points || []).map(kp => ({
            id: kp.id || kp.name,
            label: kp.name,
            case_count: kp.case_count || 0,
            isKp: true,
          })),
        })),
      })),
    }))
}

async function loadTree() {
  treeLoading.value = true
  try {
    const res = await caseAPI.getKnowledgeTreeByParams(scopeParams())
    const books = res.code === 200 ? res.data : (res.data || res || [])
    treeData.value = toTreeData(Array.isArray(books) ? books : [])
  } catch (e) {
    treeData.value = []
  } finally {
    treeLoading.value = false
  }
}

async function loadRegionCounts() {
  try {
    const [allRes, nationalRes, shanghaiRes] = await Promise.all([
      caseAPI.getList({ page: 1, page_size: 1 }),
      caseAPI.getList({ page: 1, page_size: 1, scope: 'national' }),
      caseAPI.getList({ page: 1, page_size: 1, scope: 'shanghai' }),
    ])
    regionCounts.value = {
      all: allRes?.data?.total ?? allRes?.total ?? 0,
      national: nationalRes?.data?.total ?? nationalRes?.total ?? 0,
      shanghai: shanghaiRes?.data?.total ?? shanghaiRes?.total ?? 0,
    }
  } catch (e) {
    regionCounts.value = { all: 0, national: 0, shanghai: 0 }
  }
}

async function loadCases() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize, ...scopeParams() }
    if (search.value) params.search = search.value
    if (selectedKpName.value) params.knowledge_point_name = selectedKpName.value
    const res = await caseAPI.getList(params)
    const d = res.code === 200 ? res.data : res
    cases.value = d.items || d.cases || []
    total.value = d.total || 0
  } finally {
    loading.value = false
  }
}

async function setRegion(nextRegion) {
  region.value = nextRegion
  page.value = 1
  selectedKpId.value = null
  selectedKpName.value = null
  treeRef.value?.setCurrentKey?.(null)
  await Promise.all([loadTree(), loadCases()])
}

function doSearch() {
  page.value = 1
  loadCases()
}

function clearKnowledge() {
  selectedKpId.value = null
  selectedKpName.value = null
  treeRef.value?.setCurrentKey?.(null)
  page.value = 1
  loadCases()
}

function onNodeClick(data) {
  if (!data.isKp) return
  if (selectedKpId.value === data.id) {
    clearKnowledge()
    return
  }
  selectedKpId.value = data.id
  selectedKpName.value = data.label
  page.value = 1
  loadCases()
}

onMounted(async () => {
  await Promise.all([loadRegionCounts(), loadTree(), loadCases()])
})
</script>

<style scoped>
.cases-view {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background:
    linear-gradient(180deg, rgba(20, 24, 30, 0.86), rgba(10, 12, 16, 0.94)),
    url('@/assets/bg-main.webp') center/cover no-repeat fixed;
  color: #f7f2e8;
  overflow: hidden;
}

.topbar {
  display: grid;
  grid-template-columns: auto minmax(170px, 1fr) auto 280px;
  align-items: center;
  gap: 18px;
  min-height: 76px;
  padding: 14px 24px;
  border-bottom: 1px solid rgba(226, 191, 116, 0.18);
  background: rgba(12, 15, 20, 0.74);
  backdrop-filter: blur(18px);
}

.title-block h1,
.panel-head h2,
.case-toolbar h2 {
  margin: 2px 0 0;
  font-size: 20px;
  line-height: 1.2;
  letter-spacing: 0;
}

.eyebrow {
  display: block;
  font-size: 11px;
  color: #d7b46a;
  letter-spacing: 0;
}

.ghost-button,
.clear-button,
.region-tab {
  border: 1px solid rgba(226, 191, 116, 0.2);
  background: rgba(255, 255, 255, 0.04);
  color: rgba(247, 242, 232, 0.78);
  cursor: pointer;
  transition: all 0.18s ease;
}

.ghost-button {
  height: 36px;
  padding: 0 14px;
  border-radius: 8px;
}

.ghost-button:hover,
.clear-button:hover,
.region-tab:hover {
  border-color: rgba(226, 191, 116, 0.5);
  color: #fff;
  background: rgba(226, 191, 116, 0.08);
}

.region-tabs {
  display: flex;
  gap: 8px;
}

.region-tab {
  min-width: 82px;
  height: 42px;
  border-radius: 8px;
  display: inline-flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 0 12px;
}

.region-tab strong {
  color: #e8c476;
  font-size: 13px;
}

.region-tab.active {
  background: #d7b46a;
  color: #181817;
  border-color: #d7b46a;
}

.region-tab.active strong {
  color: #181817;
}

.search-input :deep(.el-input__wrapper) {
  height: 40px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.08);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.12);
}

.search-input :deep(.el-input__inner) {
  color: #fff;
}

.search-icon {
  cursor: pointer;
  color: rgba(247, 242, 232, 0.72);
}

.library-shell {
  flex: 1;
  display: grid;
  grid-template-columns: 340px minmax(0, 1fr);
  min-height: 0;
}

.knowledge-panel {
  min-height: 0;
  overflow-y: auto;
  padding: 22px 16px 28px;
  border-right: 1px solid rgba(255, 255, 255, 0.09);
  background: rgba(10, 13, 18, 0.72);
}

.panel-head,
.case-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.clear-button {
  height: 30px;
  padding: 0 10px;
  border-radius: 8px;
  font-size: 12px;
}

.kp-tree {
  background: transparent;
}

.kp-tree :deep(.el-tree-node__content) {
  height: auto;
  min-height: 32px;
  padding: 5px 0;
  color: rgba(247, 242, 232, 0.74);
}

.kp-tree :deep(.el-tree-node__content:hover) {
  background: rgba(255, 255, 255, 0.06);
}

.kp-tree :deep(.el-tree-node.is-current > .el-tree-node__content) {
  background: rgba(215, 180, 106, 0.16);
  color: #fff;
}

.kp-tree :deep(.el-tree-node__expand-icon) {
  color: rgba(247, 242, 232, 0.45);
}

.tree-node {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  width: 100%;
  gap: 10px;
  padding-right: 8px;
  font-size: 12px;
  line-height: 1.45;
}

.tree-node.leaf {
  color: rgba(247, 242, 232, 0.86);
}

.node-label {
  flex: 1;
  word-break: break-word;
}

.kp-count {
  min-width: 22px;
  padding: 1px 7px;
  border-radius: 999px;
  text-align: center;
  color: #e8c476;
  background: rgba(226, 191, 116, 0.1);
  border: 1px solid rgba(226, 191, 116, 0.14);
}

.case-panel {
  min-width: 0;
  overflow-y: auto;
  padding: 24px;
}

.result-meta {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  font-size: 13px;
  color: rgba(247, 242, 232, 0.58);
}

.case-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}

.case-card {
  min-height: 224px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 18px;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(13, 16, 22, 0.78);
  cursor: pointer;
  transition: border-color 0.18s ease, transform 0.18s ease, background 0.18s ease;
}

.case-card:hover {
  transform: translateY(-2px);
  border-color: rgba(226, 191, 116, 0.42);
  background: rgba(18, 22, 29, 0.92);
}

.card-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tag {
  max-width: 100%;
  padding: 3px 8px;
  border-radius: 999px;
  font-size: 11px;
  line-height: 1.3;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.region-tag {
  background: rgba(82, 137, 115, 0.18);
  color: #9bd2bd;
  border: 1px solid rgba(82, 137, 115, 0.24);
}

.knowledge-tag {
  background: rgba(226, 191, 116, 0.12);
  color: #e8c476;
  border: 1px solid rgba(226, 191, 116, 0.18);
}

.case-card h3 {
  margin: 0;
  color: #fff;
  font-size: 17px;
  line-height: 1.45;
  letter-spacing: 0;
}

.case-card p {
  margin: 0;
  flex: 1;
  color: rgba(247, 242, 232, 0.68);
  font-size: 13px;
  line-height: 1.7;
}

.case-card footer {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding-top: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  color: rgba(247, 242, 232, 0.48);
  font-size: 12px;
}

.state-panel,
.empty-panel {
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  background: rgba(13, 16, 22, 0.62);
  color: rgba(247, 242, 232, 0.58);
  padding: 28px;
  text-align: center;
}

.empty-panel h3 {
  margin: 0 0 8px;
  color: #fff;
  font-size: 18px;
}

.empty-panel p {
  margin: 0;
  font-size: 13px;
}

.pagination {
  padding: 20px 0 4px;
  display: flex;
  justify-content: center;
}

@media (max-width: 980px) {
  .topbar {
    grid-template-columns: 1fr;
    align-items: stretch;
  }

  .region-tabs {
    overflow-x: auto;
  }

  .library-shell {
    grid-template-columns: 1fr;
  }

  .knowledge-panel {
    max-height: 42vh;
    border-right: 0;
    border-bottom: 1px solid rgba(255, 255, 255, 0.09);
  }
}
</style>
