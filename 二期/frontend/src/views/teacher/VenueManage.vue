<template>
  <div class="venue-manage">
    <div class="page-header">
      <h2>场馆管理 <span class="total-badge">共 {{ total }} 个</span></h2>
      <el-button type="primary" @click="openAddDialog"><el-icon><Plus /></el-icon> 新增场馆</el-button>
    </div>

    <!-- 搜索筛选 -->
    <el-card class="filter-card">
      <el-row :gutter="12">
        <el-col :span="8">
          <el-input v-model="keyword" placeholder="搜索场馆名称或地址..." clearable @input="onSearch" prefix-icon="Search" />
        </el-col>
        <el-col :span="4">
          <el-select v-model="categoryFilter" placeholder="场馆类别" clearable @change="onFilterChange" style="width:100%">
            <el-option v-for="item in categories" :key="item.category" :label="`${item.category}（${item.count}）`" :value="item.category" />
          </el-select>
        </el-col>
        <el-col :span="4">
          <el-select v-model="regionFilter" placeholder="所在区域" clearable @change="onFilterChange" style="width:100%">
            <el-option v-for="item in regions" :key="item.region" :label="`${item.region}（${item.count}）`" :value="item.region" />
          </el-select>
        </el-col>
        <el-col :span="4">
          <el-select v-model="sourceFilter" placeholder="数据来源" clearable @change="onFilterChange" style="width:100%">
            <el-option label="上海红色资源名录" value="红途" />
            <el-option label="手动录入" value="手动" />
          </el-select>
        </el-col>
      </el-row>
    </el-card>

    <!-- 场馆列表 -->
    <PageLoading v-if="loading" />
    <div v-else class="table-wrapper">
      <el-table :data="list" stripe height="100%" style="width:100%">
      <el-table-column prop="name" label="场馆名称" min-width="160" show-overflow-tooltip />
      <el-table-column prop="category" label="类别" width="90">
        <template #default="{ row }">
          <el-tag size="small" :type="categoryTagType(row.category)">{{ row.category || '未分类' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="address" label="地址" min-width="180" show-overflow-tooltip />
      <el-table-column prop="contact_phone" label="联系电话" width="130" />
      <el-table-column label="来源" width="140">
        <template #default="{ row }">
          <el-tag :type="row.source === '红途' ? 'warning' : 'success'" size="small" effect="plain">
            {{ row.source === '红途' ? '红色资源名录' : (row.source || '手动') }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <div class="action-buttons">
            <el-button size="small" class="edit-btn" @click="editVenue(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="deleteVenue(row)">删除</el-button>
          </div>
        </template>
      </el-table-column>
    </el-table>
    </div>

    <el-pagination
      v-if="total > pageSize"
      v-model:current-page="page"
      :page-size="pageSize"
      :total="total"
      layout="total, prev, pager, next, jumper"
      class="pagination"
      @current-change="fetchList"
    />

    <!-- 新增/编辑弹窗 -->
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑场馆' : '新增场馆'" width="620px">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="90px">
        <el-form-item label="场馆名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入场馆名称" />
        </el-form-item>
        <el-form-item label="场馆类别">
          <el-select v-model="form.category" placeholder="选择或输入类别" allow-create filterable style="width:100%">
            <el-option v-for="item in categories" :key="item.category" :label="item.category" :value="item.category" />
          </el-select>
        </el-form-item>
        <el-form-item label="详细地址" prop="address">
          <el-input v-model="form.address" placeholder="请输入详细地址" />
        </el-form-item>
        <el-form-item label="联系电话">
          <el-input v-model="form.contact_phone" placeholder="可选" />
        </el-form-item>
        <el-form-item label="开放时间">
          <el-input v-model="form.opening_hours" placeholder="如：9:00-17:00（周一闭馆）" />
        </el-form-item>
        <el-form-item label="官网链接">
          <el-input v-model="form.official_website" placeholder="可选，https://..." />
        </el-form-item>
        <el-form-item label="场馆简介">
          <el-input v-model="form.description" type="textarea" :autosize="{ minRows: 3, maxRows: 10 }" placeholder="可选" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveVenue">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '@/utils/request'
import PageLoading from '@/components/PageLoading.vue'

const loading = ref(false)
const saving = ref(false)
const list = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(12)
const keyword = ref('')
const categoryFilter = ref('')
const regionFilter = ref('')
const sourceFilter = ref('')
const dialogVisible = ref(false)
const editingId = ref(null)
const formRef = ref(null)
const categories = ref([])
const regions = ref([])

const form = reactive({
  name: '', category: '', address: '',
  contact_phone: '', opening_hours: '',
  official_website: '', description: ''
})

const rules = {
  name: [{ required: true, message: '请输入场馆名称', trigger: 'blur' }],
  address: [{ required: true, message: '请输入地址', trigger: 'blur' }]
}

const categoryTagType = (cat) => {
  const map = { '遗址': 'danger', '旧址': 'warning', '设施': 'info', '纪念馆': 'primary', '博物馆': 'success' }
  return map[cat] || ''
}

// 搜索时重置到第一页
const onSearch = () => {
  page.value = 1
  fetchList()
  fetchMeta()
}

const onFilterChange = () => {
  page.value = 1
  fetchList()
  fetchMeta()
}

const fetchList = async () => {
  loading.value = true
  try {
    const res = await request.get('/venues', {
      params: {
        keyword: keyword.value || undefined,
        category: categoryFilter.value || undefined,
        region: regionFilter.value || undefined,
        source: sourceFilter.value || undefined,
        page: page.value,
        page_size: pageSize.value
      }
    })
    list.value = res.items || []
    total.value = res.total || 0
  } catch (e) {
    list.value = []
  } finally {
    loading.value = false
  }
}

const fetchMeta = async () => {
  try {
    // 获取类别计数时传入除category外的所有筛选条件
    const catParams = {}
    if (keyword.value) catParams.keyword = keyword.value
    if (regionFilter.value) catParams.region = regionFilter.value
    if (sourceFilter.value) catParams.source = sourceFilter.value

    // 获取区域计数时传入除region外的所有筛选条件
    const regParams = {}
    if (keyword.value) regParams.keyword = keyword.value
    if (categoryFilter.value) regParams.category = categoryFilter.value
    if (sourceFilter.value) regParams.source = sourceFilter.value

    const [cats, regs] = await Promise.all([
      request.get('/venues/categories', { params: catParams }),
      request.get('/venues/regions', { params: regParams })
    ])
    categories.value = cats || []
    regions.value = (regs || []).slice(0, 20)  // 最多显示20个区域
  } catch (e) {
    // 元数据加载失败不影响主功能
  }
}

const openAddDialog = () => {
  editingId.value = null
  Object.assign(form, { name: '', category: '', address: '', contact_phone: '', opening_hours: '', official_website: '', description: '' })
  dialogVisible.value = true
}

const editVenue = (row) => {
  editingId.value = row.id
  Object.assign(form, {
    name: row.name || '',
    category: row.category || '',
    address: row.address || '',
    contact_phone: row.contact_phone || '',
    opening_hours: row.opening_hours || '',
    official_website: row.official_website || '',
    description: row.description || ''
  })
  dialogVisible.value = true
}

const saveVenue = async () => {
  try {
    await formRef.value.validate()
  } catch {
    return
  }
  saving.value = true
  try {
    if (editingId.value) {
      await request.put(`/venues/${editingId.value}`, form)
    } else {
      await request.post('/venues', form)
    }
    ElMessage.success('保存成功')
    dialogVisible.value = false
    fetchList()
    fetchMeta()
  } catch (e) {
    ElMessage.error(e.message || '保存失败')
  } finally {
    saving.value = false
  }
}


const deleteVenue = async (row) => {
  try {
    await ElMessageBox.confirm(`确认删除场馆"${row.name}"？`, '确认删除', { type: 'warning' })
  } catch {
    return
  }
  try {
    await request.delete(`/venues/${row.id}`)
    ElMessage.success('已删除')
    fetchList()
  } catch (e) {
    ElMessage.error('删除失败')
  }
}

onMounted(() => {
  fetchList()
  fetchMeta()
})
</script>

<style scoped>
.venue-manage { width: 100%; display: flex; flex-direction: column; height: 100%; overflow: hidden; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; flex-shrink: 0; }
.page-header h2 { font-size: 22px; color: #333; display: flex; align-items: center; gap: 10px; }
.total-badge { font-size: 14px; color: #999; font-weight: normal; }
.filter-card { margin-bottom: 12px; flex-shrink: 0; }
.table-wrapper { flex: 1; min-height: 0; overflow: hidden; }
.table-wrapper :deep(.el-table) { height: 100% !important; }
.table-wrapper :deep(.el-table__body-wrapper) { overflow-y: auto; }
.table-wrapper :deep(td .cell) { padding: 4px 12px; }
.pagination { height: 48px; flex-shrink: 0; display: flex; justify-content: center; align-items: center; }
.action-buttons { display: flex; flex-direction: row; gap: 8px; }
.edit-btn { border-color: #79bbff; color: #409eff; }
.edit-btn:hover { border-color: #409eff; background-color: #ecf5ff; color: #409eff; }
</style>
