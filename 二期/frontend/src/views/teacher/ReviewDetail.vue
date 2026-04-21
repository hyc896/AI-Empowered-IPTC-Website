<template>
  <div class="review-detail">
    <div class="page-header">
      <el-button text @click="$router.back()"><el-icon><ArrowLeft /></el-icon> 返回</el-button>
      <h2>审核实践作业</h2>
    </div>

    <PageLoading v-if="loading" />
    <div v-else>
      <el-row :gutter="20" v-if="submission">
        <!-- 左侧：学生提交内容 -->
        <el-col :span="16">
          <!-- 基本信息卡片 -->
          <el-card>
            <template #header>
              <div style="display:flex;justify-content:space-between;align-items:center">
                <span class="card-header-title">{{ submission.title }}</span>
                <el-tag>{{ typeLabel(submission.practice_type) }}</el-tag>
              </div>
            </template>

            <el-descriptions :column="2" border size="small" style="margin-bottom:16px">
              <el-descriptions-item label="学生">{{ submission.user_name }}</el-descriptions-item>
              <el-descriptions-item label="班级学号">{{ submission.class_name_id || '-' }}</el-descriptions-item>
              <el-descriptions-item label="完成日期">{{ formatDate(submission.completion_date) }}</el-descriptions-item>
              <el-descriptions-item label="提交时间">{{ formatDate(submission.submitted_at) }}</el-descriptions-item>
              <el-descriptions-item label="实践类型">{{ typeLabel(submission.practice_type) }}</el-descriptions-item>
              <el-descriptions-item label="成果形式">{{ submission.result_form || '-' }}</el-descriptions-item>
              <el-descriptions-item label="任课教师">{{ submission.instructor_name || '-' }}</el-descriptions-item>
              <el-descriptions-item label="展示偏好">{{ showcaseLabel(submission.showcase_preference) }}</el-descriptions-item>
            </el-descriptions>
          </el-card>

          <!-- 实践方案卡片 -->
          <el-card v-if="plan" style="margin-top:16px">
            <template #header>
              <div style="display:flex;justify-content:space-between;align-items:center">
                <span class="card-header-title">📋 实践方案</span>
                <el-tag type="info" size="small">{{ plan.difficulty || '标准' }} · 预计{{ plan.estimated_hours || '?' }}小时</el-tag>
              </div>
            </template>

            <div class="plan-info">
              <div v-if="plan.knowledge_point" class="plan-meta">
                <el-tag size="small" type="info">{{ plan.knowledge_point.category }}</el-tag>
                <span>{{ plan.knowledge_point.name }}</span>
              </div>
              <div v-if="plan.content" class="plan-content formatted-text" v-html="renderMarkdown(plan.content)"></div>
            </div>
          </el-card>

          <!-- 实践内容 - 按步骤展示 -->
          <el-card style="margin-top:16px">
            <template #header>
              <span class="card-header-title">📝 实践内容</span>
            </template>

            <!-- 有方案任务时，按步骤展示 -->
            <template v-if="plan?.tasks?.length && parsedContent.length">
              <div v-for="(task, taskIndex) in plan.tasks" :key="taskIndex" class="task-section">
                <div class="task-header">
                  <div class="task-step-badge">步骤 {{ taskIndex + 1 }}</div>
                  <span class="task-title">{{ task.task }}</span>
                </div>
                <div v-if="task.description" class="task-description">{{ task.description }}</div>

                <!-- 该步骤的提交内容 -->
                <div class="task-content-list">
                  <template v-if="parsedContent[taskIndex]">
                    <div v-for="(text, reqIndex) in parsedContent[taskIndex]" :key="reqIndex" class="content-item">
                      <div v-if="task.submission_requirements && task.submission_requirements[reqIndex]" class="req-label">
                        <el-icon><EditPen /></el-icon>
                        <span>{{ task.submission_requirements[reqIndex].description || getReqLabel(task.submission_requirements[reqIndex].type) }}</span>
                      </div>
                      <div class="formatted-text" v-if="text && text.trim()">{{ text }}</div>
                      <div v-else class="empty-hint">（未填写）</div>
                    </div>
                  </template>
                  <div v-else class="empty-hint">（该步骤未提交内容）</div>
                </div>
              </div>
            </template>

            <!-- 没有方案任务时，直接显示原始内容 -->
            <template v-else>
              <div class="formatted-text">{{ displayContent }}</div>
            </template>
          </el-card>

          <!-- 学生建议 -->
          <el-card v-if="submission.reflection" style="margin-top:16px">
            <template #header>
              <span class="card-header-title">💬 学生建议</span>
            </template>
            <div class="formatted-text">{{ submission.reflection }}</div>
          </el-card>

          <!-- 附件材料 -->
          <el-card v-if="submission.files?.length" style="margin-top:16px">
            <template #header>
              <div style="display:flex;justify-content:space-between;align-items:center">
                <span class="card-header-title">📎 附件材料</span>
                <el-tag size="small">{{ submission.files.length }} 个文件</el-tag>
              </div>
            </template>
            <div class="files-list">
              <div v-for="file in submission.files" :key="file.path" class="file-block">
                <!-- 图片 -->
                <template v-if="isImage(file.type)">
                  <el-image
                    :src="file.path"
                    :preview-src-list="imageUrls"
                    fit="contain"
                    class="file-image"
                  />
                  <div class="file-name">{{ file.filename }}</div>
                </template>
                <!-- 视频 -->
                <template v-else-if="isVideo(file.type)">
                  <video controls class="file-video" preload="metadata">
                    <source :src="file.path" :type="file.type" />
                    您的浏览器不支持视频播放
                  </video>
                  <div class="file-name">{{ file.filename }}</div>
                </template>
                <!-- 音频 -->
                <template v-else-if="isAudio(file.type)">
                  <div class="audio-block">
                    <el-icon :size="24" color="#409eff"><Headset /></el-icon>
                    <div class="audio-info">
                      <div class="file-name">{{ file.filename }}</div>
                      <audio controls class="file-audio" preload="metadata">
                        <source :src="file.path" :type="file.type" />
                        您的浏览器不支持音频播放
                      </audio>
                    </div>
                  </div>
                </template>
                <!-- 其他文件 -->
                <template v-else>
                  <div class="file-doc">
                    <el-icon :size="20"><Document /></el-icon>
                    <a :href="file.path" target="_blank" class="file-link">{{ file.filename }}</a>
                    <span class="file-size" v-if="file.size">{{ formatFileSize(file.size) }}</span>
                  </div>
                </template>
              </div>
            </div>
          </el-card>

          <!-- 批注面板 -->
          <el-card style="margin-top:16px">
            <template #header>
              <div style="display:flex;justify-content:space-between;align-items:center">
                <span>📝 教师批注</span>
                <el-tag>{{ annotations.length }} 条</el-tag>
              </div>
            </template>

            <!-- 添加批注 -->
            <div class="add-annotation">
              <el-input
                v-model="newAnnotation"
                type="textarea"
                :autosize="{ minRows: 2, maxRows: 10 }"
                placeholder="输入批注内容..."
              />
              <el-button type="primary" size="small" @click="addAnnotation" :disabled="!newAnnotation.trim()" style="margin-top:8px">
                添加批注
              </el-button>
            </div>

            <el-divider v-if="annotations.length" />

            <!-- 批注列表 -->
            <div v-for="ann in annotations" :key="ann.id" class="annotation-item">
              <div class="annotation-header">
                <span class="annotation-author">{{ ann.reviewer_name }}</span>
                <span class="annotation-time">{{ formatDate(ann.created_at) }}</span>
                <el-button text type="danger" size="small" @click="deleteAnnotation(ann.id)">删除</el-button>
              </div>
              <div v-if="ann.target_text" class="annotation-quote">{{ ann.target_text }}</div>
              <div class="annotation-content">{{ ann.content }}</div>
            </div>

            <el-empty v-if="!annotations.length" description="暂无批注" :image-size="60" />
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card class="review-form-card">
            <template #header><span>✅ 审核操作</span></template>

            <el-form :model="reviewForm" :rules="reviewRules" ref="reviewFormRef" label-width="80px">
              <el-form-item label="审核结果" prop="status">
                <el-radio-group v-model="reviewForm.status">
                  <el-radio label="approved">
                    <el-tag type="success">通过</el-tag>
                  </el-radio>
                  <el-radio label="rejected">
                    <el-tag type="danger">不通过</el-tag>
                  </el-radio>
                </el-radio-group>
              </el-form-item>

              <el-form-item label="评分" prop="score">
                <el-input-number
                  v-model="reviewForm.score"
                  :min="0"
                  :max="100"
                  :disabled="reviewForm.status === 'rejected'"
                  style="width:100%"
                />
              </el-form-item>

              <el-form-item label="评语">
                <el-input
                  v-model="reviewForm.comment"
                  type="textarea"
                  :autosize="{ minRows: 5, maxRows: 15 }"
                  placeholder="请输入评语（可选）..."
                />
              </el-form-item>

              <el-form-item>
                <el-button @click="getAISuggestion" :loading="aiLoading" style="width:100%">
                  🤖 AI辅助评分
                </el-button>
              </el-form-item>

              <!-- AI评分结果 -->
              <div v-if="aiResult" class="ai-result">
                <div class="ai-result-header">
                  <span>AI评分建议</span>
                  <el-button type="primary" text size="small" @click="adoptAISuggestion">采纳建议</el-button>
                </div>
                <div class="ai-score">建议评分：<strong>{{ aiResult.suggested_score }}</strong> 分</div>
                <div class="ai-comment">{{ aiResult.suggested_comment }}</div>

                <div v-if="aiResult.dimensions?.length" class="ai-dimensions">
                  <div v-for="dim in aiResult.dimensions" :key="dim.name" class="ai-dim-item">
                    <span class="dim-name">{{ dim.name }}</span>
                    <el-progress :percentage="dim.score" :stroke-width="8" style="flex:1" />
                    <span class="dim-score">{{ dim.score }}</span>
                  </div>
                </div>

                <div v-if="aiResult.highlights?.length" class="ai-section">
                  <div class="ai-section-title">亮点</div>
                  <div v-for="h in aiResult.highlights" :key="h" class="ai-tag-item">✅ {{ h }}</div>
                </div>

                <div v-if="aiResult.suggestions?.length" class="ai-section">
                  <div class="ai-section-title">改进建议</div>
                  <div v-for="s in aiResult.suggestions" :key="s" class="ai-tag-item">💡 {{ s }}</div>
                </div>
              </div>

              <el-form-item>
                <el-button type="primary" :loading="submitting" @click="submitReview" style="width:100%">
                  提交审核结果
                </el-button>
              </el-form-item>

              <el-form-item v-if="reviewForm.status === 'approved'">
                <el-button
                  :type="submission?.is_showcased ? 'warning' : 'success'"
                  @click="toggleShowcase"
                  style="width:100%"
                >
                  {{ submission?.is_showcased ? '取消展示' : '展示到优秀作品墙' }}
                </el-button>
              </el-form-item>
            </el-form>
          </el-card>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { submissionAPI, reviewAPI, annotationAPI, practiceAPI } from '@/api'
import { ElMessage } from 'element-plus'
import PageLoading from '@/components/PageLoading.vue'

const route = useRoute()
const router = useRouter()
const loading = ref(true)
const submitting = ref(false)
const submission = ref(null)
const plan = ref(null)
const reviewFormRef = ref(null)
const aiLoading = ref(false)
const aiResult = ref(null)
const annotations = ref([])
const newAnnotation = ref('')

const reviewForm = reactive({ status: 'approved', score: 80, comment: '' })
const reviewRules = {
  status: [{ required: true, message: '请选择审核结果', trigger: 'change' }],
  score: [{ required: true, message: '请输入评分', trigger: 'blur' }]
}

const typeLabel = (t) => ({ writing:'写作设计', presentation:'宣传表达', visit:'参观研学', performance:'表演体验', interaction:'交往行动', production:'生产改造', free:'自由申请' }[t] || t)
const formatDate = (d) => d ? new Date(d).toLocaleString('zh-CN') : '-'
const showcaseLabel = (s) => ({ none: '不展示', original: '原样展示', anonymous: '匿名展示' }[s] || s || '-')
const isImage = (type) => type?.startsWith('image/')
const isVideo = (type) => type?.startsWith('video/')
const isAudio = (type) => type?.startsWith('audio/')
const imageUrls = computed(() => submission.value?.files?.filter(f => isImage(f.type)).map(f => f.path) || [])

const getReqLabel = (type) => {
  const labels = { photo: '照片说明', video: '视频说明', audio: '音频说明', document: '文档内容', text: '文字说明', url: '链接' }
  return labels[type] || '内容描述'
}

const formatFileSize = (bytes) => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

// 解析 JSON 内容为二维数组
const parsedContent = computed(() => {
  if (!submission.value?.content) return []
  try {
    const parsed = JSON.parse(submission.value.content)
    if (Array.isArray(parsed)) return parsed
    return []
  } catch {
    return []
  }
})

// 如果 JSON 解析失败，直接显示原始文本
const displayContent = computed(() => {
  if (parsedContent.value.length > 0) return ''
  return submission.value?.content || ''
})

// 简单的 Markdown 渲染（处理标题、加粗、换行等）
const renderMarkdown = (text) => {
  if (!text) return ''
  let html = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
  // 标题
  html = html.replace(/^### (.+)$/gm, '<h5>$1</h5>')
  html = html.replace(/^## (.+)$/gm, '<h4>$1</h4>')
  html = html.replace(/^# (.+)$/gm, '<h3>$1</h3>')
  // 加粗
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  // 列表
  html = html.replace(/^- (.+)$/gm, '<li>$1</li>')
  html = html.replace(/^(\d+)\. (.+)$/gm, '<li>$2</li>')
  // 换行
  html = html.replace(/\n/g, '<br>')
  return html
}

const fetchSubmission = async () => {
  loading.value = true
  try {
    submission.value = await submissionAPI.getDetail(route.params.id)
    // 获取关联的实践方案
    if (submission.value.plan_id) {
      try {
        plan.value = await practiceAPI.getPlanDetail(submission.value.plan_id)
      } catch (e) {
        console.warn('获取方案详情失败', e)
      }
    }
  } catch (e) {
    ElMessage.error('获取提交详情失败')
  } finally {
    loading.value = false
  }
}

const submitReview = async () => {
  await reviewFormRef.value.validate()
  submitting.value = true
  try {
    await reviewAPI.create({
      submission_id: route.params.id,
      status: reviewForm.status,
      score: reviewForm.status === 'approved' ? reviewForm.score : null,
      comment: reviewForm.comment
    })
    ElMessage.success('审核完成')
    router.push('/teacher/review')
  } catch (e) {
    ElMessage.error('审核提交失败')
  } finally {
    submitting.value = false
  }
}

const toggleShowcase = async () => {
  try {
    const newState = !submission.value.is_showcased
    await submissionAPI.toggleShowcase(route.params.id, newState)
    submission.value.is_showcased = newState
    ElMessage.success(newState ? '已展示到优秀作品墙' : '已取消展示')
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

const getAISuggestion = async () => {
  aiLoading.value = true
  aiResult.value = null
  try {
    const res = await reviewAPI.getAISuggestion(route.params.id)
    if (res.error) {
      ElMessage.warning(res.error)
    } else {
      aiResult.value = res
    }
  } catch (e) {
    ElMessage.error('AI评分服务暂时不可用')
  } finally {
    aiLoading.value = false
  }
}

const adoptAISuggestion = () => {
  if (aiResult.value) {
    reviewForm.score = aiResult.value.suggested_score
    reviewForm.comment = aiResult.value.suggested_comment
    ElMessage.success('已采纳AI建议')
  }
}

const fetchAnnotations = async () => {
  try {
    const res = await annotationAPI.getList(route.params.id)
    annotations.value = res.items
  } catch (e) {
    console.error(e)
  }
}

const addAnnotation = async () => {
  if (!newAnnotation.value.trim()) return
  try {
    await annotationAPI.create({
      submission_id: route.params.id,
      content: newAnnotation.value
    })
    newAnnotation.value = ''
    await fetchAnnotations()
    ElMessage.success('批注已添加')
  } catch (e) {
    ElMessage.error('添加批注失败')
  }
}

const deleteAnnotation = async (id) => {
  try {
    await annotationAPI.delete(id)
    await fetchAnnotations()
    ElMessage.success('批注已删除')
  } catch (e) {
    ElMessage.error('删除失败')
  }
}

onMounted(() => {
  fetchSubmission()
  fetchAnnotations()
})
</script>

<style scoped>
.review-detail { width: 100%; }
.page-header { margin-bottom: 20px; }
.page-header h2 { font-size: 22px; color: #333; margin: 8px 0; }
.card-header-title { font-size: 16px; font-weight: bold; color: #333; }

/* ====== 格式化文本样式 ====== */
.formatted-text {
  font-family: 'SimSun', '宋体', 'Noto Serif SC', serif;
  font-size: 15px;
  color: #333;
  line-height: 2.0;
  text-indent: 2em;
  white-space: pre-wrap;
  word-break: break-word;
}
.formatted-text :deep(h3),
.formatted-text :deep(h4),
.formatted-text :deep(h5) {
  text-indent: 0;
  margin: 16px 0 8px;
  color: #1a1a2e;
}
.formatted-text :deep(h3) { font-size: 20px; }
.formatted-text :deep(h4) { font-size: 18px; }
.formatted-text :deep(h5) { font-size: 16px; }
.formatted-text :deep(li) {
  text-indent: 0;
  margin-left: 2em;
  line-height: 2.0;
}
.formatted-text :deep(strong) {
  color: #1a1a2e;
}

/* ====== 方案信息 ====== */
.plan-info { }
.plan-meta {
  display: flex; align-items: center; gap: 8px;
  margin-bottom: 12px; font-size: 14px; color: #555;
}
.plan-content {
  padding: 16px;
  background: #fafbfc;
  border-radius: 8px;
  border: 1px solid #f0f0f0;
}

/* ====== 步骤展示 ====== */
.task-section {
  padding: 20px 0;
  border-bottom: 1px solid #f0f0f0;
}
.task-section:last-child { border-bottom: none; }
.task-section:first-child { padding-top: 0; }
.task-header {
  display: flex; align-items: center; gap: 10px;
  margin-bottom: 12px;
}
.task-step-badge {
  background: #409eff; color: #fff; font-size: 12px;
  padding: 2px 12px; border-radius: 12px; white-space: nowrap;
  font-weight: bold;
}
.task-title { font-size: 16px; font-weight: bold; color: #1a1a2e; }
.task-description {
  font-size: 14px; color: #666; line-height: 1.7;
  padding: 12px 16px; background: #f5f7fa; border-radius: 6px;
  margin-bottom: 16px; border-left: 3px solid #409eff;
}
.task-content-list { display: flex; flex-direction: column; gap: 12px; }
.content-item {
  padding: 12px 16px;
  background: #fffdf5;
  border-radius: 6px;
  border: 1px solid #f0ecd8;
}
.req-label {
  display: flex; align-items: center; gap: 6px;
  font-size: 13px; font-weight: 500; color: #409eff;
  margin-bottom: 8px;
}
.empty-hint { font-size: 14px; color: #ccc; font-style: italic; }

/* ====== 附件文件 ====== */
.files-list { display: flex; flex-direction: column; gap: 16px; }
.file-block { }
.file-image {
  width: 100%;
  max-height: 500px;
  border-radius: 8px;
  border: 1px solid #eee;
}
.file-video {
  width: 100%;
  max-height: 500px;
  border-radius: 8px;
  background: #000;
}
.audio-block {
  display: flex; align-items: flex-start; gap: 12px;
  padding: 16px;
  background: #f5f7fa;
  border-radius: 8px;
}
.audio-info { flex: 1; }
.file-audio { width: 100%; margin-top: 8px; }
.file-name { font-size: 13px; color: #888; margin-top: 6px; }
.file-doc {
  display: flex; align-items: center; gap: 8px;
  padding: 12px 16px; background: #f5f7fa; border-radius: 6px;
  font-size: 14px;
}
.file-link { color: #409eff; text-decoration: none; }
.file-link:hover { text-decoration: underline; }
.file-size { font-size: 12px; color: #999; margin-left: auto; }

/* ====== 审核表单 ====== */
.review-form-card { position: sticky; top: 20px; }
.ai-result { background: #f0f9ff; border: 1px solid #b3d8ff; border-radius: 8px; padding: 12px; margin-bottom: 12px; }
.ai-result-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; font-weight: bold; color: #409eff; }
.ai-score { font-size: 14px; margin-bottom: 6px; }
.ai-comment { font-size: 13px; color: #555; margin-bottom: 10px; line-height: 1.6; }
.ai-dimensions { margin-bottom: 10px; }
.ai-dim-item { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; font-size: 13px; }
.dim-name { width: 80px; color: #666; }
.dim-score { width: 30px; text-align: right; font-weight: bold; color: #409eff; }
.ai-section { margin-bottom: 8px; }
.ai-section-title { font-size: 13px; font-weight: bold; color: #333; margin-bottom: 4px; }
.ai-tag-item { font-size: 13px; color: #555; line-height: 1.8; }

/* ====== 批注 ====== */
.add-annotation { margin-bottom: 12px; }
.annotation-item { padding: 12px 0; border-bottom: 1px solid #f0f0f0; }
.annotation-item:last-child { border-bottom: none; }
.annotation-header { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.annotation-author { font-weight: bold; font-size: 13px; color: #333; }
.annotation-time { font-size: 12px; color: #999; flex: 1; }
.annotation-quote { font-size: 13px; color: #888; padding: 6px 10px; background: #f5f7fa; border-left: 3px solid #409eff; margin-bottom: 6px; border-radius: 2px; }
.annotation-content { font-size: 14px; color: #555; line-height: 1.6; }
</style>
