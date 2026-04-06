<template>
  <el-dialog
    v-model="visible"
    title="选择实践场馆"
    width="800px"
    :close-on-click-modal="true"
    class="venue-dialog"
    @close="handleClose"
  >
    <!-- 筛选栏 -->
    <div class="filter-bar">
      <el-input
        v-model="keyword"
        placeholder="搜索场馆名称或地址..."
        clearable
        class="search-input"
        @input="debouncedSearch"
      >
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
      <el-select v-model="selectedRegion" placeholder="地区" clearable class="filter-select" @change="loadVenues">
        <el-option v-for="r in regions" :key="r.region" :label="`${r.region} (${r.count})`" :value="r.region" />
      </el-select>
      <el-select v-model="selectedCategory" placeholder="类别" clearable class="filter-select" @change="loadVenues">
        <el-option v-for="c in categories" :key="c.category" :label="`${c.category} (${c.count})`" :value="c.category" />
      </el-select>
    </div>

    <!-- 场馆列表 -->
    <div class="venue-list" v-loading="loading">
      <div v-if="venues.length === 0 && !loading" class="empty-state">
        <el-empty description="未找到匹配的场馆" />
      </div>

      <div
        v-for="venue in venues"
        :key="venue.id"
        class="venue-item"
        :class="{ selected: selectedVenueId === venue.id }"
        @click="selectVenue(venue)"
      >
        <div class="venue-main">
          <div class="venue-name">
            {{ venue.name }}
            <el-tag v-if="venue.is_verified" size="small" type="success" effect="plain">已验证</el-tag>
            <el-tag v-if="venue.category" size="small" effect="plain">{{ venue.category }}</el-tag>
          </div>
          <div class="venue-address">{{ venue.address }}</div>
          <div v-if="venue.opening_hours" class="venue-hours">
            <el-icon><Clock /></el-icon> {{ venue.opening_hours }}
          </div>
        </div>
        <div class="venue-check">
          <el-icon v-if="selectedVenueId === venue.id" :size="20" color="#67c23a"><CircleCheckFilled /></el-icon>
        </div>
      </div>
    </div>

    <!-- 分页 -->
    <div v-if="total > pageSize" class="pagination">
      <el-pagination
        layout="prev, pager, next"
        :total="total"
        :page-size="pageSize"
        v-model:current-page="currentPage"
        @current-change="loadVenues"
        small
      />
    </div>

    <template #footer>
      <el-button @click="handleClose">取消</el-button>
      <el-button @click="clearSelection">不选择场馆</el-button>
      <el-button type="primary" :disabled="!selectedVenueId" @click="confirmSelection">
        确认选择
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { venueAPI } from '@/api'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  currentVenueId: { type: String, default: '' },
  knowledgePointId: { type: String, default: '' }
})

const emit = defineEmits(['update:modelValue', 'select'])

const visible = ref(false)
const loading = ref(false)
const keyword = ref('')
const selectedRegion = ref('')
const selectedCategory = ref('')
const venues = ref([])
const regions = ref([])
const categories = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = 10
const selectedVenueId = ref('')
const selectedVenueData = ref(null)

let debounceTimer = null

watch(() => props.modelValue, (val) => {
  visible.value = val
  if (val) {
    selectedVenueId.value = props.currentVenueId || ''
    loadFilters()
    loadVenues()
  }
})

watch(visible, (val) => {
  if (!val) emit('update:modelValue', false)
})

const loadFilters = async () => {
  try {
    // 区域计数：传入除region外的筛选条件
    const regParams = {}
    if (keyword.value) regParams.keyword = keyword.value
    if (selectedCategory.value) regParams.category = selectedCategory.value
    if (props.knowledgePointId) regParams.knowledge_point_id = props.knowledgePointId

    // 类别计数：传入除category外的筛选条件
    const catParams = {}
    if (keyword.value) catParams.keyword = keyword.value
    if (selectedRegion.value) catParams.region = selectedRegion.value
    if (props.knowledgePointId) catParams.knowledge_point_id = props.knowledgePointId

    const [regionsRes, categoriesRes] = await Promise.all([
      venueAPI.getRegions(regParams),
      venueAPI.getCategories(catParams)
    ])
    regions.value = regionsRes
    categories.value = categoriesRes
  } catch (e) {
    // ignore
  }
}

const loadVenues = async () => {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize
    }
    if (keyword.value) params.keyword = keyword.value
    if (selectedRegion.value) params.region = selectedRegion.value
    if (selectedCategory.value) params.category = selectedCategory.value
    if (props.knowledgePointId) params.knowledge_point_id = props.knowledgePointId

    const res = await venueAPI.getList(params)
    venues.value = res.items
    total.value = res.total
  } catch (e) {
    venues.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
  loadFilters()
}

const debouncedSearch = () => {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    currentPage.value = 1
    loadVenues()
  }, 300)
}

const selectVenue = (venue) => {
  if (selectedVenueId.value === venue.id) {
    selectedVenueId.value = ''
    selectedVenueData.value = null
  } else {
    selectedVenueId.value = venue.id
    selectedVenueData.value = venue
  }
}

const confirmSelection = () => {
  emit('select', selectedVenueData.value)
  handleClose()
}

const clearSelection = () => {
  emit('select', null)
  handleClose()
}

const handleClose = () => {
  visible.value = false
}
</script>

<style scoped>
.filter-bar {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
}
.search-input { flex: 1; }
.filter-select { width: 160px; }

.venue-list {
  max-height: 400px;
  overflow-y: auto;
  border: 1px solid #eee;
  border-radius: 8px;
}

.venue-item {
  display: flex;
  align-items: center;
  padding: 14px 16px;
  border-bottom: 1px solid #f0f0f0;
  cursor: pointer;
  transition: background 0.15s;
}
.venue-item:last-child { border-bottom: none; }
.venue-item:hover { background: #f5f7fa; }
.venue-item.selected { background: #f0f9eb; border-left: 3px solid #67c23a; }

.venue-main { flex: 1; }
.venue-name {
  font-size: 15px;
  font-weight: 500;
  color: #333;
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
}
.venue-address {
  font-size: 13px;
  color: #888;
  margin-bottom: 2px;
}
.venue-hours {
  font-size: 12px;
  color: #aaa;
  display: flex;
  align-items: center;
  gap: 4px;
}

.venue-check {
  flex-shrink: 0;
  width: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.empty-state {
  padding: 40px 0;
}

.pagination {
  display: flex;
  justify-content: center;
  margin-top: 12px;
}
</style>
