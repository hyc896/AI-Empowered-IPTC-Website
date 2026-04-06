<template>
  <div class="my-practices">
    <div class="page-header">
      <h2>我的实践</h2>
      <div class="header-actions">
        <span v-if="userStore.user?.teacher_id" class="teacher-info">
          <el-icon><UserFilled /></el-icon>
          指导老师：<strong>{{ teacherName }}</strong>
          <el-button text type="primary" @click="showTeacherDialog = true" size="small">
            <el-icon><Edit /></el-icon>修改
          </el-button>
        </span>
        <el-button v-else type="warning" plain @click="showTeacherDialog = true" size="small">
          <el-icon><UserFilled /></el-icon> 选择指导教师
        </el-button>
        <el-button type="primary" @click="$router.push('/student/knowledge')">
          <el-icon><Plus /></el-icon> 新建实践
        </el-button>
      </div>
    </div>

    <!-- 顶层切换：我的方案 / 提交记录 -->
    <el-segmented v-model="viewMode" :options="viewOptions" class="view-switch" @change="onViewChange" />

    <!-- ========== 我的方案 ========== -->
    <div v-if="viewMode === 'plans'" class="list">
      <PageLoading v-if="loading" />
      <template v-else>
      <div v-if="plans.length > 0" class="batch-actions">
        <el-button v-if="!batchMode" size="small" @click="batchMode = true">批量处理</el-button>
        <template v-if="batchMode">
          <el-checkbox v-model="selectAll" @change="handleSelectAll" :indeterminate="isIndeterminate">全选</el-checkbox>
          <el-button v-if="selectedPlans.length > 0" type="danger" size="small" @click="batchDelete">批量删除 ({{ selectedPlans.length }})</el-button>
          <el-button size="small" @click="exitBatchMode">取消</el-button>
        </template>
      </div>

      <el-empty v-if="plans.length === 0" description="暂无方案，去选择知识点生成吧" />

      <el-card v-for="item in plans" :key="item.id" class="practice-card" shadow="hover">
        <div class="card-body">
          <el-checkbox v-if="batchMode" v-model="selectedPlans" :value="item.id" class="card-checkbox" />
          <div class="card-left">
            <div class="card-title">
              <span>{{ item.title }}</span>
              <el-tag :type="planStatusType(item.generation_status)" size="small">{{ planStatusLabel(item.generation_status) }}</el-tag>
            </div>
            <div class="card-meta">
              <span>{{ typeLabel(item.practice_type) }}</span>
              <span v-if="item.knowledge_point">{{ item.knowledge_point.category }} · {{ item.knowledge_point.name }}</span>
              <span>生成时间：{{ formatDate(item.created_at) }}</span>
              <span v-if="item.estimated_hours">预计 {{ item.estimated_hours }} 小时</span>
            </div>
          </div>
          <div class="card-actions">
            <el-button v-if="item.generation_status === 'success'" size="small" type="primary" @click="viewPlan(item)">查看方案</el-button>
            <el-button v-if="item.generation_status === 'success'" size="small" @click="goSubmit(item)">去提交</el-button>
            <el-tag v-if="item.generation_status === 'generating'" type="warning" size="small">生成中...</el-tag>
            <el-tag v-if="item.generation_status === 'failed'" type="danger" size="small">生成失败</el-tag>
            <el-button size="small" type="danger" text @click="deletePlan(item)">删除</el-button>
          </div>
        </div>
      </el-card>

      <el-pagination
        v-if="planTotal > pageSize"
        v-model:current-page="planPage"
        :page-size="pageSize"
        :total="planTotal"
        layout="prev, pager, next"
        class="pagination"
        @current-change="fetchPlans"
      />
      </template>
    </div>

    <!-- ========== 提交记录 ========== -->
    <div v-if="viewMode === 'submissions'">
      <el-tabs v-model="statusFilter" @tab-change="fetchSubmissions">
        <el-tab-pane label="全部" name="" />
        <el-tab-pane label="草稿" name="draft" />
        <el-tab-pane label="审核中" name="submitted" />
        <el-tab-pane label="已通过" name="approved" />
        <el-tab-pane label="未通过" name="rejected" />
      </el-tabs>

      <div class="list">
        <PageLoading v-if="loading" />
        <template v-else>
        <el-empty v-if="submissions.length === 0" description="暂无提交记录" />

        <el-card v-for="item in submissions" :key="item.id" class="practice-card" shadow="hover">
          <div class="card-body">
            <div class="card-left">
              <div class="card-title">
                <span>{{ item.title }}</span>
                <el-tag :type="statusType(item.status)" size="small">{{ statusLabel(item.status) }}</el-tag>
              </div>
              <div class="card-meta">
                <span>{{ typeLabel(item.practice_type) }}</span>
                <span>提交时间：{{ item.submitted_at ? formatDate(item.submitted_at) : '草稿' }}</span>
              </div>
              <div v-if="item.review" class="review-result">
                <span>评分：<strong>{{ item.review.score }}</strong> 分</span>
                <span v-if="item.review.comment">评语：{{ item.review.comment }}</span>
              </div>
            </div>
            <div class="card-actions">
              <el-button size="small" @click="viewDetail(item)">查看详情</el-button>
              <el-button v-if="item.status === 'rejected'" size="small" type="warning" @click="resubmit(item)">重新提交</el-button>
              <el-button v-if="item.status === 'draft'" size="small" type="danger" @click="deleteDraft(item)">删除</el-button>
            </div>
          </div>
        </el-card>
        </template>
      </div>

      <el-pagination
        v-if="subTotal > pageSize"
        v-model:current-page="subPage"
        :page-size="pageSize"
        :total="subTotal"
        layout="prev, pager, next"
        class="pagination"
        @current-change="fetchSubmissions"
      />
    </div>

    <!-- 修改指导教师对话框 -->
    <el-dialog v-model="showTeacherDialog" title="修改指导教师" width="400px">
      <el-select v-model="newTeacherId" placeholder="请选择指导教师" clearable filterable style="width:100%">
        <el-option v-for="t in teachers" :key="t.id" :label="`${t.real_name}${t.department ? ' (' + t.department + ')' : ''}`" :value="t.id" />
      </el-select>
      <template #footer>
        <el-button @click="showTeacherDialog = false">取消</el-button>
        <el-button type="primary" @click="updateTeacher">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { practiceAPI, submissionAPI, authAPI } from '@/api'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { useTaskStore } from '@/stores/task'
import PageLoading from '@/components/PageLoading.vue'

const router = useRouter()
const userStore = useUserStore()
const taskStore = useTaskStore()
const loading = ref(false)
const pageSize = ref(10)

// 视图切换
const viewMode = ref('plans')
const viewOptions = [
  { label: '我的方案', value: 'plans' },
  { label: '提交记录', value: 'submissions' }
]

// 方案列表
const plans = ref([])
const planTotal = ref(0)
const planPage = ref(1)

// 批量选择
const batchMode = ref(false)
const selectedPlans = ref([])
const selectAll = ref(false)
const isIndeterminate = computed(() => selectedPlans.value.length > 0 && selectedPlans.value.length < plans.value.length)

const exitBatchMode = () => {
  batchMode.value = false
  selectedPlans.value = []
  selectAll.value = false
}

// 修改教师
const showTeacherDialog = ref(false)
const teachers = ref([])
const newTeacherId = ref('')
const teacherName = computed(() => {
  const teacher = teachers.value.find(t => t.id === userStore.user?.teacher_id)
  return teacher ? teacher.real_name : '未设置'
})

const handleSelectAll = (val) => {
  selectedPlans.value = val ? plans.value.map(p => p.id) : []
}

const batchDelete = async () => {
  await ElMessageBox.confirm(`确认删除选中的 ${selectedPlans.value.length} 个方案？`, '批量删除', { type: 'warning' })
  try {
    await Promise.all(selectedPlans.value.map(id => practiceAPI.deletePlan(id)))
    ElMessage.success('批量删除成功')
    exitBatchMode()
    fetchPlans()
  } catch (e) {
    ElMessage.error('批量删除失败')
  }
}

const updateTeacher = async () => {
  try {
    await authAPI.updateTeacher(newTeacherId.value)
    ElMessage.success('指导教师已更新')
    showTeacherDialog.value = false
    await userStore.fetchUserInfo()
  } catch (e) {
    ElMessage.error('更新失败')
  }
}

// 提交列表
const submissions = ref([])
const subTotal = ref(0)
const subPage = ref(1)
const statusFilter = ref('')

// 标签映射
const statusLabel = (s) => ({ draft:'草稿', submitted:'审核中', reviewing:'审核中', approved:'已通过', rejected:'未通过' }[s] || s)
const statusType = (s) => ({ draft:'info', submitted:'warning', reviewing:'warning', approved:'success', rejected:'danger' }[s] || '')
const planStatusLabel = (s) => ({ pending:'等待中', generating:'生成中', success:'已完成', failed:'生成失败' }[s] || s)
const planStatusType = (s) => ({ pending:'info', generating:'warning', success:'success', failed:'danger' }[s] || '')
const typeLabel = (t) => ({ writing:'写作设计', presentation:'宣传表达', visit:'参观研学', performance:'表演体验', interaction:'交往行动', production:'生产改造', free:'自由申请' }[t] || t)
const formatDate = (d) => d ? new Date(d).toLocaleDateString('zh-CN') : '-'

const onViewChange = () => {
  if (viewMode.value === 'plans') fetchPlans()
  else fetchSubmissions()
}

const fetchPlans = async () => {
  loading.value = true
  try {
    const res = await practiceAPI.getMyPlans({ page: planPage.value, page_size: pageSize.value })
    plans.value = res.items
    planTotal.value = res.total
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

const fetchSubmissions = async () => {
  loading.value = true
  try {
    const res = await submissionAPI.getList({
      status: statusFilter.value || undefined,
      page: subPage.value,
      page_size: pageSize.value
    })
    submissions.value = res.items
    subTotal.value = res.total
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

const viewPlan = (item) => {
  router.push({ name: 'PlanDetail', params: { id: item.id } })
}

const goSubmit = (item) => {
  router.push({ name: 'PracticeSubmit', params: { planId: item.id } })
}

const deletePlan = async (item) => {
  await ElMessageBox.confirm('确认删除此方案？', '确认', { type: 'warning' })
  try {
    await practiceAPI.deletePlan(item.id)
    ElMessage.success('已删除')
    fetchPlans()
  } catch (e) {
    ElMessage.error('删除失败')
  }
}

const viewDetail = (item) => {
  router.push({ name: 'PlanDetail', params: { id: item.plan_id } })
}

const resubmit = (item) => {
  router.push({ name: 'PracticeSubmit', params: { planId: item.plan_id } })
}

const deleteDraft = async (item) => {
  await ElMessageBox.confirm('确认删除此草稿？', '确认', { type: 'warning' })
  try {
    await submissionAPI.delete(item.id)
    ElMessage.success('已删除')
    fetchSubmissions()
  } catch (e) {
    ElMessage.error('删除失败')
  }
}

onMounted(fetchPlans)

// 监听后台任务完成，自动刷新方案列表
const unsubscribe = taskStore.onComplete(() => {
  if (viewMode.value === 'plans') fetchPlans()
})
onUnmounted(() => unsubscribe())

// 加载教师列表
onMounted(async () => {
  try {
    teachers.value = await authAPI.getTeachers()
    newTeacherId.value = userStore.user?.teacher_id || ''
  } catch (e) {
    // ignore
  }
})
</script>

<style scoped>
.my-practices { width: 100%; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.page-header h2 { font-size: 22px; color: #333; }
.header-actions { display: flex; gap: 8px; align-items: center; }
.teacher-info {
  font-size: 14px; color: #555; display: flex; align-items: center; gap: 4px;
  background: #f0f9ff; padding: 4px 12px; border-radius: 20px; border: 1px solid #d9ecff;
}
.view-switch { margin-bottom: 20px; }
.batch-actions { display: flex; gap: 12px; align-items: center; margin-bottom: 12px; padding: 12px; background: #f5f7fa; border-radius: 4px; }
.list { display: flex; flex-direction: column; gap: 12px; min-height: 200px; }
.practice-card {}
.card-body { display: flex; justify-content: space-between; align-items: flex-start; }
.card-checkbox { margin-right: 12px; }
.card-left { flex: 1; }
.card-title { display: flex; align-items: center; gap: 10px; font-size: 16px; font-weight: bold; color: #333; margin-bottom: 8px; }
.card-meta { display: flex; gap: 20px; font-size: 13px; color: #888; margin-bottom: 6px; }
.review-result { font-size: 13px; color: #666; background: #f9f9f9; padding: 8px 12px; border-radius: 4px; margin-top: 8px; display: flex; gap: 16px; }
.card-actions { display: flex; gap: 8px; flex-shrink: 0; align-items: center; }
.pagination { margin-top: 20px; justify-content: center; display: flex; }
</style>
