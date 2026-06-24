<template>
  <div class="cases-view">
    <div class="header">
      <el-button text style="color:rgba(255,255,255,0.6)" @click="router.push('/case-platform')">← 返回</el-button>
      <span class="title">教学案例库</span>
      <el-input v-model="search" placeholder="搜索案例..." clearable class="search-input" @keyup.enter="doSearch" @clear="doSearch">
        <template #suffix><el-icon style="cursor:pointer" @click="doSearch"><Search /></el-icon></template>
      </el-input>
    </div>

    <div class="main">
      <div class="sidebar">
        <div class="sidebar-title">知识点筛选</div>
        <div v-if="treeLoading" class="tip">加载中...</div>
        <el-tree v-else :data="treeData" node-key="id" :props="{ label: 'label', children: 'children' }"
          highlight-current @node-click="onNodeClick" class="kp-tree">
          <template #default="{ node, data }">
            <span class="tree-node">
              <span>{{ node.label }}</span>
              <span v-if="data.case_count !== undefined" class="kp-count">{{ data.case_count }}</span>
            </span>
          </template>
        </el-tree>
      </div>

      <div class="content">
        <div v-if="loading" class="tip">加载中...</div>
        <div v-else-if="!cases.length" class="tip">暂无案例</div>
        <div v-else class="case-grid">
          <div v-for="c in cases" :key="c.id" class="case-card" @click="router.push(`/cases/${c.id}`)">
            <div class="card-tags">
              <el-tag v-for="kp in (c.related_knowledge_points || []).slice(0,2)" :key="kp.name || kp" size="small" type="info">{{ kp.name || kp }}</el-tag>
              <el-tag v-if="c.primary_region === '上海'" size="small" type="warning">上海</el-tag>
            </div>
            <h4 class="card-title">{{ c.title }}</h4>
            <p class="card-summary">{{ (c.summary || c.content || '').slice(0, 80) }}...</p>
            <div class="card-date">{{ new Date(c.created_at).toLocaleDateString('zh-CN') }}</div>
          </div>
        </div>
        <div class="pagination">
          <el-pagination v-model:current-page="page" :page-size="pageSize" :total="total"
            layout="prev, pager, next" @current-change="loadCases" background small />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { Search } from '@element-plus/icons-vue'
import { caseAPI } from '@/api/index'

const router = useRouter()
const route = useRoute()
const search = ref(route.query.search || '')
const page = ref(1)
const pageSize = 20
const total = ref(0)
const cases = ref([])
const loading = ref(false)
const treeLoading = ref(true)
const treeData = ref([])
const selectedKpId = ref(null)

async function loadTree() {
  try {
    const res = await caseAPI.getKnowledgeTree()
    const books = res.code === 200 ? res.data : (res.data || res || [])
    treeData.value = books.map(b => ({
      id: 'book_' + b.book_id,
      label: b.book_name,
      children: b.chapters.map(ch => ({
        id: 'ch_' + ch.id,
        label: ch.label,
        children: ch.sections.map(sec => ({
          id: 'sec_' + sec.id,
          label: sec.label,
          children: sec.knowledge_points.map(kp => ({
            id: kp.id, label: kp.name, case_count: kp.case_count, isKp: true
          }))
        }))
      }))
    }))
  } catch (e) {
    treeData.value = []
  } finally {
    treeLoading.value = false
  }
}

async function loadCases() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize }
    if (search.value) params.search = search.value
    if (selectedKpId.value) params.knowledge_point_id = selectedKpId.value
    const res = await caseAPI.getList(params)
    const d = res.code === 200 ? res.data : res
    cases.value = d.items || d.cases || []
    total.value = d.total || 0
  } finally {
    loading.value = false
  }
}

function doSearch() { page.value = 1; loadCases() }

function onNodeClick(data) {
  if (!data.isKp) return
  selectedKpId.value = selectedKpId.value === data.id ? null : data.id
  page.value = 1
  loadCases()
}

onMounted(() => { loadTree(); loadCases() })
</script>

<style scoped>
.cases-view {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: url('@/assets/bg-main.webp') center/cover no-repeat fixed;
  color: #fff;
  overflow: hidden;
}
.header {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 0 24px;
  height: 60px;
  background: rgba(0,0,0,0.5);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(192,57,43,0.2);
}
.title { font-size: 16px; font-weight: 700; color: #ffd700; }
.search-input { width: 260px; margin-left: auto; }
.search-input :deep(.el-input__wrapper) { background: rgba(255,255,255,0.08); box-shadow: none; border: 1px solid rgba(255,255,255,0.15); }
.search-input :deep(.el-input__inner) { color: #fff; }
.search-input :deep(.el-input__inner::placeholder) { color: rgba(255,255,255,0.35); }
.main { flex: 1; display: flex; overflow: hidden; }
.sidebar {
  width: 260px;
  flex-shrink: 0;
  overflow-y: auto;
  background: rgba(0,0,0,0.45);
  border-right: 1px solid rgba(255,255,255,0.08);
  padding: 12px 0;
}
.sidebar-title { padding: 8px 16px 12px; font-size: 11px; color: rgba(255,215,0,0.7); text-transform: uppercase; letter-spacing: 1px; }
.kp-tree { background: transparent; }
.kp-tree :deep(.el-tree-node__content) { color: rgba(255,255,255,0.7); height: 28px; }
.kp-tree :deep(.el-tree-node__content:hover) { background: rgba(255,255,255,0.06); }
.kp-tree :deep(.el-tree-node.is-current > .el-tree-node__content) { background: rgba(192,57,43,0.3); color: #fff; }
.kp-tree :deep(.el-tree-node__expand-icon) { color: rgba(255,255,255,0.4); }
.tree-node { display: flex; justify-content: space-between; align-items: center; width: 100%; font-size: 12px; padding-right: 8px; }
.kp-count { font-size: 11px; color: rgba(255,215,0,0.7); background: rgba(255,215,0,0.1); padding: 1px 6px; border-radius: 8px; flex-shrink: 0; }
.content { flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; }
.case-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; }
.case-card {
  background: rgba(0,0,0,0.5);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 8px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.case-card:hover { border-color: rgba(255,215,0,0.4); background: rgba(255,255,255,0.05); }
.card-tags { display: flex; gap: 6px; flex-wrap: wrap; }
.card-title { font-size: 14px; font-weight: 600; color: #fff; line-height: 1.5; margin: 0; }
.card-summary { font-size: 12px; color: rgba(255,255,255,0.5); line-height: 1.6; margin: 0; }
.card-date { font-size: 11px; color: rgba(255,255,255,0.3); }
.tip { color: rgba(255,255,255,0.4); padding: 48px; text-align: center; }
.pagination { padding: 16px 0; display: flex; justify-content: center; }
</style>
