<template>
  <div class="plan-detail">
    <PageLoading v-if="loading" />
    <div v-else>
      <div v-if="plan">
        <div class="page-header">
          <el-button text @click="$router.back()"><el-icon><ArrowLeft /></el-icon> 返回</el-button>
          <el-steps :active="3" finish-status="success" class="steps">
            <el-step title="选择知识点" />
            <el-step title="设置参数" />
            <el-step title="选择实践类型" />
            <el-step title="查看方案" />
          </el-steps>
        </div>

        <el-row :gutter="20">
          <el-col :span="16">
            <!-- 方案内容 -->
            <el-card class="content-card">
              <template #header>
                <div class="card-title">
                  <el-icon><Document /></el-icon>
                  <span>{{ plan.title }}</span>
                  <el-tag>{{ typeLabel(plan.practice_type) }}</el-tag>
                </div>
              </template>
              <div class="markdown-content" v-html="renderMarkdown(plan.content)"></div>
            </el-card>

            <!-- 任务清单 -->
            <el-card class="tasks-card" style="margin-top:16px">
              <template #header><span>📋 实践步骤</span></template>
              <el-timeline>
                <el-timeline-item
                  v-for="(task, i) in plan.tasks"
                  :key="i"
                  :type="task.required ? 'primary' : 'info'"
                >
                  <div class="task-item">
                    <strong>{{ task.task }}</strong>
                    <p>{{ task.description }}</p>
                  </div>
                </el-timeline-item>
              </el-timeline>
            </el-card>
          </el-col>

          <el-col :span="8">
            <!-- 基本信息 -->
            <el-card class="info-card">
              <template #header><span>📌 方案信息</span></template>
              <el-descriptions :column="1" size="small">
                <el-descriptions-item label="知识点来源">
                  <template v-if="plan.knowledge_point">
                    <div class="kp-source">
                      <el-tag size="small" type="info">{{ plan.knowledge_point.category }}</el-tag>
                      <span v-if="plan.knowledge_point.chapter" class="kp-chapter">{{ plan.knowledge_point.chapter }}</span>
                      <span class="kp-name">{{ plan.knowledge_point.name }}</span>
                    </div>
                  </template>
                  <span v-else>-</span>
                </el-descriptions-item>
                <el-descriptions-item label="实践类型">{{ typeLabel(plan.practice_type) }}</el-descriptions-item>
                <el-descriptions-item label="预计耗时">{{ plan.estimated_hours || 4 }} 小时</el-descriptions-item>
                <el-descriptions-item label="难度">
                  <el-tag :type="difficultyType(plan.difficulty)" size="small">{{ difficultyLabel(plan.difficulty) }}</el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="生成时间">{{ formatDate(plan.generated_at) }}</el-descriptions-item>
                <el-descriptions-item label="截止日期">
                  <div v-if="plan.deadline">{{ formatDate(plan.deadline) }}</div>
                  <el-button v-else text type="primary" size="small" @click="showDeadlineDialog = true">设置截止日期</el-button>
                </el-descriptions-item>
              </el-descriptions>
            </el-card>

            <!-- 实践场馆 -->
            <el-card v-if="venue" class="venues-card" style="margin-top:16px">
              <template #header><span>📍 实践场馆</span></template>
              <div class="venue-item">
                <strong>{{ venue.name }}</strong>
                <p>{{ venue.address }}</p>
                <p v-if="venue.description" class="venue-desc">{{ venue.description }}</p>
                <p v-if="venue.opening_hours" class="venue-desc">🕐 {{ venue.opening_hours }}</p>
                <p v-if="venue.contact_phone" class="venue-desc">📞 {{ venue.contact_phone }}</p>
              </div>
            </el-card>

            <!-- 操作按钮 -->
            <div class="action-btns">
              <el-button @click="regenerate" :loading="regenerating">重新生成</el-button>
              <el-button type="primary" @click="startSubmit">开始实践并提交</el-button>
            </div>
          </el-col>
        </el-row>
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
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { practiceAPI, venueAPI } from '@/api'
import { ElMessage } from 'element-plus'
import { marked } from 'marked'
import PageLoading from '@/components/PageLoading.vue'

const route = useRoute()
const router = useRouter()
const loading = ref(true)
const regenerating = ref(false)
const plan = ref(null)
const venue = ref(null)
const showDeadlineDialog = ref(false)
const selectedDeadline = ref(null)

const typeLabels = { writing:'写作设计类', presentation:'宣传表达类', visit:'参观研学类', performance:'表演体验类', interaction:'交往行动类', production:'生产改造类', free:'自由申请类' }
const typeLabel = (t) => typeLabels[t] || t
const difficultyLabel = (d) => ({ easy:'简单', medium:'中等', hard:'困难' }[d] || '中等')
const difficultyType = (d) => ({ easy:'success', medium:'warning', hard:'danger' }[d] || 'warning')
const formatDate = (d) => d ? new Date(d).toLocaleString('zh-CN') : '-'

const renderMarkdown = (text) => {
  if (!text) return ''
  return marked(text)
}

const fetchPlan = async () => {
  loading.value = true
  try {
    plan.value = await practiceAPI.getPlanDetail(route.params.id)
    if (plan.value.venue_id) {
      try {
        venue.value = await venueAPI.getDetail(plan.value.venue_id)
      } catch {
        // venue fetch failure is non-fatal
      }
    }
  } catch (e) {
    ElMessage.error('获取方案失败')
  } finally {
    loading.value = false
  }
}

const startSubmit = () => {
  router.push({ name: 'PracticeSubmit', params: { planId: plan.value.id } })
}

const regenerate = async () => {
  regenerating.value = true
  try {
    await practiceAPI.deletePlan(plan.value.id)
    router.back()
  } finally {
    regenerating.value = false
  }
}

const saveDeadline = async () => {
  if (!selectedDeadline.value) {
    ElMessage.warning('请选择截止日期')
    return
  }
  try {
    await practiceAPI.setDeadline(plan.value.id, selectedDeadline.value.toISOString())
    ElMessage.success('截止日期已设置')
    showDeadlineDialog.value = false
    fetchPlan()
  } catch (e) {
    ElMessage.error('设置失败')
  }
}

onMounted(fetchPlan)
</script>

<style scoped>
.plan-detail { width: 100%; }
.page-header { margin-bottom: 20px; }
.steps { margin: 12px 0; }
.card-title { display: flex; align-items: center; gap: 10px; font-size: 16px; font-weight: bold; }
.markdown-content { line-height: 1.8; color: #333; font-size: 14px; }
.markdown-content :deep(h1) { font-size: 18px; color: #333; margin: 16px 0 8px; font-weight: bold; }
.markdown-content :deep(h2) { font-size: 16px; color: #333; margin: 14px 0 8px; font-weight: bold; }
.markdown-content :deep(h3) { font-size: 15px; color: #c0392b; margin: 12px 0 6px; font-weight: bold; }
.markdown-content :deep(h4) { font-size: 14px; color: #555; margin: 10px 0 6px; font-weight: bold; }
.markdown-content :deep(p) { margin: 6px 0; font-size: 14px; }
.markdown-content :deep(ul), .markdown-content :deep(ol) { padding-left: 20px; margin: 6px 0; }
.markdown-content :deep(li) { font-size: 14px; line-height: 1.8; }
.markdown-content :deep(strong) { color: #333; }
.markdown-content :deep(blockquote) { border-left: 3px solid #ddd; padding-left: 12px; color: #666; margin: 8px 0; }
.task-item strong { font-size: 15px; margin-right: 8px; }
.task-item p { color: #666; font-size: 13px; margin-top: 4px; }
.venue-item { padding: 10px 0; border-bottom: 1px solid #f0f0f0; }
.venue-item:last-child { border-bottom: none; }
.venue-item strong { font-size: 14px; color: #333; }
.venue-item p { font-size: 13px; color: #666; margin-top: 4px; }
.venue-desc { color: #999; font-size: 12px; }
.action-btns { margin-top: 16px; display: flex; flex-direction: column; gap: 10px; }
.action-btns .el-button { width: 100%; }
.kp-source { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.kp-chapter { font-size: 12px; color: #999; }
.kp-name { font-size: 13px; font-weight: bold; color: #333; }
</style>
