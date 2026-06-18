<template>
  <div class="cases-page">
    <!-- 顶部栏 -->
    <div class="header">
      <div class="header-left">
        <el-button text :icon="ArrowLeft" style="color:rgba(255,255,255,0.7)" @click="router.push('/')">返回首页</el-button>
        <span class="logo-text">案例库</span>
      </div>
      <div class="header-right">
        <el-input
          v-model="searchQuery"
          placeholder="搜索案例标题、内容..."
          :prefix-icon="Search"
          clearable
          style="width:320px"
          @keyup.enter="onSearch"
          @clear="onSearch"
        />
        <el-button type="primary" style="margin-left:8px;background:#c0392b;border-color:#c0392b" @click="onSearch">搜索</el-button>
      </div>
    </div>

    <div class="main">
      <!-- 左侧知识点筛选 -->
      <div class="sidebar">
        <div class="sidebar-title">按知识点筛选</div>
        <div
          class="kp-item"
          :class="{ active: !selectedKpId }"
          @click="selectKp(null)"
        >
          全部案例
          <span class="kp-count">{{ stats.total_cases || 0 }}</span>
        </div>
        <div
          v-for="kp in knowledgePoints"
          :key="kp.id"
          class="kp-item"
          :class="{ active: selectedKpId === kp.id }"
          @click="selectKp(kp.id)"
        >
          <span class="kp-name">{{ kp.name }}</span>
          <span class="kp-count">{{ kp.case_count }}</span>
        </div>
      </div>

      <!-- 右侧案例列表 -->
      <div class="content">
        <!-- 统计栏 -->
        <div class="stat-bar">
          <span>共 <strong>{{ total }}</strong> 篇案例</span>
          <span v-if="selectedKpId" class="filter-tag">
            {{ currentKpName }}
            <el-icon style="cursor:pointer;margin-left:4px" @click="selectKp(null)"><Close /></el-icon>
          </span>
          <span v-if="searchQuery && searched" class="filter-tag">
            搜索：{{ searchQuery }}
            <el-icon style="cursor:pointer;margin-left:4px" @click="clearSearch"><Close /></el-icon>
          </span>
        </div>

        <!-- 骨架屏 -->
        <div v-if="loading" class="case-list">
          <div v-for="i in 6" :key="i" class="case-card skeleton">
            <el-skeleton :rows="4" animated />
          </div>
        </div>

        <!-- 案例列表 -->
        <div v-else-if="cases.length" class="case-list">
          <div
            v-for="item in cases"
            :key="item.id"
            class="case-card"
            @click="router.push(`/cases/${item.id}`)"
          >
            <div class="case-kps">
              <el-tag
                v-for="kp in item.knowledgePoints.slice(0, 3)"
                :key="kp"
                size="small"
                effect="light"
                style="margin-right:4px;background:rgba(192,57,43,0.1);border-color:rgba(192,57,43,0.3);color:#c0392b"
              >{{ kp }}</el-tag>
            </div>
            <h3 class="case-title">{{ item.title }}</h3>
            <p class="case-summary">{{ item.summary || item.content.slice(0, 120) }}</p>
            <div class="case-meta">
              <span>{{ formatDate(item.publishDate) }}</span>
              <span class="read-more">阅读全文 →</span>
            </div>
          </div>
        </div>

        <!-- 空状态 -->
        <div v-else class="empty">
          <el-empty description="暂无案例" />
        </div>

        <!-- 分页 -->
        <div v-if="total > pageSize" class="pagination">
          <el-pagination
            v-model:current-page="page"
            :page-size="pageSize"
            :total="total"
            background
            layout="prev, pager, next"
            @current-change="loadCases"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowLeft, Search, Close } from '@element-plus/icons-vue'
import { caseAPI } from '@/api/index'

const router = useRouter()

const cases = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const loading = ref(false)
const searchQuery = ref('')
const searched = ref(false)
const selectedKpId = ref(null)
const knowledgePoints = ref([])
const stats = ref({})

const currentKpName = computed(() => {
  const kp = knowledgePoints.value.find(k => k.id === selectedKpId.value)
  return kp?.name || ''
})

const formatDate = (dateStr) => {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric' })
}

const loadCases = async () => {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize }
    if (selectedKpId.value) params.knowledge_point_id = selectedKpId.value
    if (searched.value && searchQuery.value) params.search = searchQuery.value
    const res = await caseAPI.getList(params)
    const data = res.data
    cases.value = data.items
    total.value = data.total
  } catch (e) {
    cases.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

const loadSidebar = async () => {
  try {
    const [kpRes, statsRes] = await Promise.all([
      caseAPI.getKnowledgePoints(),
      caseAPI.getStatistics()
    ])
    knowledgePoints.value = (kpRes || []).filter(k => k.case_count > 0)
    stats.value = statsRes || {}
  } catch (e) {
    // sidebar load failure is non-blocking
  }
}

const selectKp = (id) => {
  selectedKpId.value = id
  page.value = 1
  loadCases()
}

const onSearch = () => {
  searched.value = true
  page.value = 1
  loadCases()
}

const clearSearch = () => {
  searchQuery.value = ''
  searched.value = false
  page.value = 1
  loadCases()
}

onMounted(() => {
  loadSidebar()
  loadCases()
})
</script>

<style scoped>
.cases-page {
  min-height: 100vh;
  background: #1a0a0a;
  color: #e8d5d5;
}

.header {
  background: rgba(0,0,0,0.6);
  backdrop-filter: blur(12px);
  padding: 0 40px;
  height: 60px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid rgba(192,57,43,0.2);
  position: sticky;
  top: 0;
  z-index: 100;
}
.header-left { display: flex; align-items: center; gap: 12px; }
.logo-text { color: #fff; font-size: 18px; font-weight: bold; letter-spacing: 1px; }
.header-right { display: flex; align-items: center; }

.main {
  display: flex;
  max-width: 1280px;
  margin: 0 auto;
  padding: 24px 20px;
  gap: 24px;
}

/* 侧边栏 */
.sidebar {
  width: 220px;
  flex-shrink: 0;
}
.sidebar-title {
  font-size: 12px;
  color: rgba(255,255,255,0.4);
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: 12px;
  padding: 0 8px;
}
.kp-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  color: rgba(255,255,255,0.6);
  transition: all 0.2s;
  margin-bottom: 2px;
}
.kp-item:hover { background: rgba(192,57,43,0.1); color: #e8d5d5; }
.kp-item.active { background: rgba(192,57,43,0.15); color: #e8b4b8; border-left: 3px solid #c0392b; padding-left: 9px; }
.kp-name { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.kp-count {
  font-size: 11px;
  background: rgba(255,255,255,0.1);
  color: rgba(255,255,255,0.4);
  padding: 1px 6px;
  border-radius: 10px;
  flex-shrink: 0;
  margin-left: 4px;
}

/* 内容区 */
.content { flex: 1; min-width: 0; }

.stat-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 14px;
  color: rgba(255,255,255,0.5);
  margin-bottom: 16px;
}
.stat-bar strong { color: #e8b4b8; }
.filter-tag {
  display: inline-flex;
  align-items: center;
  background: rgba(192,57,43,0.15);
  border: 1px solid rgba(192,57,43,0.3);
  color: #e8b4b8;
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 4px;
}

.case-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 16px;
}

.case-card {
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 10px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.25s;
}
.case-card:hover {
  background: rgba(192,57,43,0.08);
  border-color: rgba(192,57,43,0.3);
  transform: translateY(-2px);
}
.case-card.skeleton { cursor: default; }
.case-card.skeleton:hover { transform: none; }

.case-kps { margin-bottom: 10px; min-height: 22px; }
.case-title {
  font-size: 16px;
  font-weight: 600;
  color: #f0e0e0;
  margin-bottom: 8px;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.case-summary {
  font-size: 13px;
  color: rgba(255,255,255,0.45);
  line-height: 1.6;
  margin-bottom: 12px;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.case-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: rgba(255,255,255,0.3);
  border-top: 1px solid rgba(255,255,255,0.06);
  padding-top: 10px;
  margin-top: auto;
}
.read-more { color: rgba(192,57,43,0.7); }
.case-card:hover .read-more { color: #c0392b; }

.empty { padding: 80px 0; }
.pagination { display: flex; justify-content: center; margin-top: 32px; }
</style>
