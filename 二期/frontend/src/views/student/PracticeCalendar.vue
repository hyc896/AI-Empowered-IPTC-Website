<template>
  <div class="practice-calendar">
    <div class="page-header">
      <h2>实践日历</h2>
      <el-button type="primary" @click="$router.push('/student/knowledge')">
        <el-icon><Plus /></el-icon> 新建实践
      </el-button>
    </div>

    <div class="calendar-layout">
      <div class="calendar-left">
        <el-card class="calendar-card">
          <el-calendar v-model="currentDate">
            <template #date-cell="{ data }">
              <div class="calendar-day">
                <div class="day-number">{{ data.day.split('-').slice(-1)[0] }}</div>
                <div v-for="plan in getPlansForDate(data.day)" :key="plan.id"
                  class="plan-badge" :class="getBadgeClass(plan)"
                  @click="viewPlan(plan)">
                  {{ plan.title }}
                </div>
              </div>
            </template>
          </el-calendar>
        </el-card>
      </div>

      <div class="calendar-right">
        <!-- 我的方案列表 -->
        <el-card class="right-card plans-card">
          <template #header><span>📋 我的方案</span></template>
          <div class="scroll-body">
            <div v-if="plans.length === 0" style="text-align:center;color:#999;padding:20px">暂无方案</div>
            <div v-for="plan in plans" :key="plan.id" class="plan-item">
              <div class="plan-item-title" @click="viewPlan(plan)">{{ plan.title }}</div>
              <div class="plan-item-meta">
                <el-tag size="small">{{ typeLabel(plan.practice_type) }}</el-tag>
                <span class="plan-item-date">{{ formatDate(plan.created_at) }}</span>
              </div>
              <div class="plan-item-deadline">
                <template v-if="plan.deadline">
                  <span :class="getDeadlineClass(plan.deadline)">{{ formatDeadline(plan.deadline) }}</span>
                  <el-button text size="small" @click="openDeadlineDialog(plan)">修改</el-button>
                </template>
                <el-button v-else text type="primary" size="small" @click="openDeadlineDialog(plan)">设置截止日期</el-button>
              </div>
            </div>
          </div>
        </el-card>

        <!-- 即将到期提醒 -->
        <el-card class="right-card upcoming-card">
          <template #header><span>⏰ 即将到期</span></template>
          <div class="scroll-body">
            <div v-if="upcomingPlans.length === 0" style="text-align:center;color:#999;padding:16px">暂无即将到期的方案</div>
            <div v-for="plan in upcomingPlans" :key="plan.id" class="upcoming-item">
              <div class="upcoming-title">{{ plan.title }}</div>
              <div class="upcoming-meta">
                <span :class="getDeadlineClass(plan.deadline)">{{ formatDeadline(plan.deadline) }}</span>
              </div>
              <div class="upcoming-actions">
                <el-button size="small" @click="viewPlan(plan)">查看</el-button>
                <el-button size="small" type="primary" @click="goSubmit(plan)">去提交</el-button>
              </div>
            </div>
          </div>
        </el-card>
      </div>
    </div>

    <!-- 设置截止日期对话框 -->
    <el-dialog v-model="showDeadlineDialog" title="设置截止日期" width="400px">
      <el-date-picker
        v-model="selectedDeadline"
        type="datetime"
        placeholder="选择截止日期"
        style="width: 100%"
      />
      <template #footer>
        <el-button @click="showDeadlineDialog = false">取消</el-button>
        <el-button type="primary" @click="saveDeadline">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { practiceAPI } from '@/api'
import { ElMessage } from 'element-plus'

const router = useRouter()
const currentDate = ref(new Date())
const plans = ref([])
const showDeadlineDialog = ref(false)
const selectedPlan = ref(null)
const selectedDeadline = ref(null)

const typeLabel = (t) => ({ writing:'写作设计', presentation:'宣传表达', visit:'参观研学', performance:'表演体验', interaction:'交往行动', production:'生产改造', free:'自由申请' }[t] || t)
const formatDate = (d) => d ? new Date(d).toLocaleDateString('zh-CN') : '-'

const upcomingPlans = computed(() => {
  const now = new Date()
  const sevenDaysLater = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000)
  return plans.value
    .filter(p => p.deadline && new Date(p.deadline) > now && new Date(p.deadline) <= sevenDaysLater)
    .sort((a, b) => new Date(a.deadline) - new Date(b.deadline))
})

// 日历上只显示一个日期：有 deadline 显示 deadline，没有则显示创建日期
const getPlansForDate = (dateStr) => {
  return plans.value.filter(p => {
    if (p.deadline) {
      return new Date(p.deadline).toISOString().split('T')[0] === dateStr
    }
    return new Date(p.created_at).toISOString().split('T')[0] === dateStr
  })
}

const getBadgeClass = (plan) => {
  if (!plan.deadline) return 'no-deadline'
  const now = new Date()
  const daysLeft = (new Date(plan.deadline) - now) / (1000 * 60 * 60 * 24)
  if (daysLeft < 0) return 'overdue'
  if (daysLeft < 3) return 'urgent'
  return 'normal'
}

const getDeadlineClass = (deadline) => {
  const now = new Date()
  const daysLeft = (new Date(deadline) - now) / (1000 * 60 * 60 * 24)
  if (daysLeft < 0) return 'text-overdue'
  if (daysLeft < 3) return 'text-urgent'
  return 'text-normal'
}

const formatDeadline = (d) => {
  if (!d) return ''
  const date = new Date(d)
  const now = new Date()
  const daysLeft = Math.ceil((date - now) / (1000 * 60 * 60 * 24))
  if (daysLeft < 0) return `已逾期 ${Math.abs(daysLeft)} 天`
  if (daysLeft === 0) return '今天截止'
  if (daysLeft === 1) return '明天截止'
  return `${daysLeft} 天后截止 (${date.toLocaleDateString('zh-CN')})`
}

const fetchPlans = async () => {
  try {
    const res = await practiceAPI.getMyPlans({ page: 1, page_size: 100 })
    plans.value = res.items.filter(p => p.generation_status === 'success')
  } catch (e) {
    console.error(e)
  }
}

const viewPlan = (plan) => {
  router.push({ name: 'PlanDetail', params: { id: plan.id } })
}

const goSubmit = (plan) => {
  router.push({ name: 'PracticeSubmit', params: { planId: plan.id } })
}

const openDeadlineDialog = (plan) => {
  selectedPlan.value = plan
  selectedDeadline.value = plan.deadline ? new Date(plan.deadline) : null
  showDeadlineDialog.value = true
}

const saveDeadline = async () => {
  if (!selectedDeadline.value) {
    ElMessage.warning('请选择截止日期')
    return
  }
  try {
    await practiceAPI.setDeadline(selectedPlan.value.id, selectedDeadline.value.toISOString())
    ElMessage.success('截止日期已设置')
    showDeadlineDialog.value = false
    fetchPlans()
  } catch (e) {
    ElMessage.error('设置失败')
  }
}

onMounted(fetchPlans)
</script>

<style scoped>
.practice-calendar { width: 100%; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.page-header h2 { font-size: 22px; color: #333; }

.calendar-layout { display: flex; gap: 20px; height: calc(100vh - 140px); }
.calendar-left { flex: 1; min-width: 0; }
.calendar-card { height: 100%; display: flex; flex-direction: column; }
.calendar-card :deep(.el-card__body) { flex: 1; overflow: auto; padding: 0; }
.calendar-card :deep(.el-calendar) { height: 100%; }
.calendar-card :deep(.el-calendar__body) { height: calc(100% - 60px); }
.calendar-card :deep(.el-calendar-table) { height: 100%; }
.calendar-card :deep(.el-calendar-table td) { vertical-align: top; }

.calendar-right { width: 340px; flex-shrink: 0; display: flex; flex-direction: column; gap: 16px; }
.plans-card { flex: 3; min-height: 0; display: flex; flex-direction: column; }
.upcoming-card { flex: 1; min-height: 0; display: flex; flex-direction: column; }
.right-card :deep(.el-card__body) { flex: 1; overflow: hidden; padding: 0; }
.scroll-body { height: 100%; overflow-y: auto; padding: 0 16px; }

.calendar-day { min-height: 70px; padding: 4px; }
.day-number { font-size: 14px; color: #666; margin-bottom: 4px; }
.plan-badge {
  font-size: 11px; padding: 2px 6px; border-radius: 2px;
  cursor: pointer; overflow: hidden; text-overflow: ellipsis;
  white-space: nowrap; margin-bottom: 2px;
}
.plan-badge.no-deadline { background: #f4f4f5; color: #909399; }
.plan-badge.normal { background: #e1f3d8; color: #67c23a; }
.plan-badge.urgent { background: #fdf6ec; color: #e6a23c; }
.plan-badge.overdue { background: #fef0f0; color: #f56c6c; }

.plan-item { padding: 12px 0; border-bottom: 1px solid #f0f0f0; }
.plan-item:last-child { border-bottom: none; }
.plan-item-title { font-size: 14px; font-weight: bold; color: #333; cursor: pointer; margin-bottom: 6px; }
.plan-item-title:hover { color: #409eff; }
.plan-item-meta { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.plan-item-date { font-size: 12px; color: #999; }
.plan-item-deadline { font-size: 13px; }

.text-normal { color: #67c23a; }
.text-urgent { color: #e6a23c; }
.text-overdue { color: #f56c6c; }

.upcoming-item { padding: 10px 0; border-bottom: 1px solid #f0f0f0; }
.upcoming-item:last-child { border-bottom: none; }
.upcoming-title { font-size: 14px; font-weight: bold; color: #333; margin-bottom: 4px; }
.upcoming-meta { font-size: 13px; margin-bottom: 6px; }
.upcoming-actions { display: flex; gap: 4px; }
</style>
