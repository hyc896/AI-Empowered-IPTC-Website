<template>
  <div class="knowledge-select">
    <div class="page-header">
      <h2>选择知识点</h2>
      <p>从三门课程中选择你感兴趣的知识点，开始生成实践方案</p>
    </div>

    <!-- 步骤条 -->
    <el-steps :active="0" finish-status="success" class="steps">
      <el-step title="选择知识点" />
      <el-step title="自定义详情" />
      <el-step title="选择实践类型" />
      <el-step title="查看方案" />
    </el-steps>

    <!-- 搜索和筛选 -->
    <div class="filter-row">
      <el-input v-model="keyword" placeholder="搜索知识点..." prefix-icon="Search" clearable class="search-input" @input="fetchList" />
      <el-radio-group v-model="category" class="category-group" @change="fetchList">
        <el-radio-button value="">全部</el-radio-button>
        <el-radio-button value="习概">习近平新时代中国特色社会主义思想概论</el-radio-button>
        <el-radio-button value="思修">思想道德基础与法律修养</el-radio-button>
        <el-radio-button value="马原">马克思主义基本原理概论</el-radio-button>
      </el-radio-group>
    </div>

    <!-- 知识点列表 -->
    <PageLoading v-if="loading" />
    <div v-else class="knowledge-grid">
      <el-empty v-if="list.length === 0" description="暂无知识点" />
      <el-card
        v-for="item in list"
        :key="item.id"
        class="knowledge-card"
        :class="{ selected: selected?.id === item.id }"
        @click="selectItem(item)"
        shadow="hover"
      >
        <div class="card-header">
          <el-tag :type="tagType(item.category)" size="small">{{ categoryFullName(item.category) }}</el-tag>
        </div>
        <h4>{{ item.name }}</h4>
        <p class="desc">{{ item.description || '暂无描述' }}</p>
      </el-card>
    </div>

    <!-- 底部固定区域：分页 + 下一步 -->
    <div class="bottom-bar">
      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="prev, pager, next"
        @current-change="fetchList"
      />
      <div class="footer-right">
        <span v-if="selected" class="selected-tip">已选：{{ selected.name }}</span>
        <el-button type="primary" :disabled="!selected" @click="goNext">
          下一步：自定义详情 <el-icon><ArrowRight /></el-icon>
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { knowledgeAPI } from '@/api'
import { categoryFullName } from '@/utils/category'
import PageLoading from '@/components/PageLoading.vue'

const router = useRouter()
const loading = ref(false)
const list = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(12)
const keyword = ref('')
const category = ref('')
const selected = ref(null)

const tagType = (cat) => ({ '习概': 'primary', '思修': 'success', '马原': 'warning' }[cat] || 'info')

const fetchList = async () => {
  loading.value = true
  try {
    const res = await knowledgeAPI.getList({
      keyword: keyword.value || undefined,
      category: category.value || undefined,
      is_active: true,
      page: page.value,
      page_size: pageSize.value
    })
    list.value = res.items
    total.value = res.total
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

const selectItem = (item) => {
  selected.value = selected.value?.id === item.id ? null : item
}

const goNext = () => {
  router.push({ name: 'PracticeOptions', query: { kpId: selected.value.id, kpName: selected.value.name } })
}

onMounted(fetchList)
</script>

<style scoped>
.knowledge-select {
  width: 100%;
  display: flex;
  flex-direction: column;
  height: 100%;
}
.page-header { margin-bottom: 16px; flex-shrink: 0; }
.page-header h2 { font-size: 22px; color: #333; margin-bottom: 4px; }
.page-header p { color: #666; font-size: 14px; }
.steps { margin-bottom: 16px; flex-shrink: 0; }
.filter-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  flex-shrink: 0;
}
.search-input {
  flex: 1;
  min-width: 120px;
}
.category-group {
  flex-shrink: 0;
}

.knowledge-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  grid-template-rows: repeat(4, 1fr);
  gap: 12px;
  flex: 1;
  min-height: 0;
}
.knowledge-card {
  cursor: pointer;
  transition: all 0.2s;
  border: 2px solid transparent;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.knowledge-card :deep(.el-card__body) {
  padding: 12px;
  display: flex;
  flex-direction: column;
  height: 100%;
}
.knowledge-card.selected { border-color: #c0392b; background: #fff5f5; }
.knowledge-card:hover { border-color: #c0392b; transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
.card-header { margin-bottom: 6px; flex-shrink: 0; }
.card-header :deep(.el-tag) { font-size: 11px; max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.knowledge-card h4 { font-size: 15px; color: #333; margin-bottom: 6px; line-height: 1.4; flex-shrink: 0; }
.desc {
  font-size: 14px;
  color: #888;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  line-height: 1.6;
  max-height: calc(1.6em * 2);
}

.bottom-bar {
  flex-shrink: 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0 0;
  border-top: 1px solid #eee;
  margin-top: 12px;
  background: #f5f7fa;
}
.footer-right {
  display: flex;
  align-items: center;
  gap: 12px;
}
.selected-tip { color: #c0392b; font-size: 14px; }
</style>
