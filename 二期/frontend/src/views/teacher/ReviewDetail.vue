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
          <el-card>
            <template #header>
              <div style="display:flex;justify-content:space-between;align-items:center">
                <span>{{ submission.title }}</span>
                <el-tag>{{ typeLabel(submission.practice_type) }}</el-tag>
              </div>
            </template>

            <el-descriptions :column="2" border size="small" style="margin-bottom:16px">
              <el-descriptions-item label="学生">{{ submission.user_name }}</el-descriptions-item>
              <el-descriptions-item label="完成日期">{{ formatDate(submission.completion_date) }}</el-descriptions-item>
              <el-descriptions-item label="提交时间">{{ formatDate(submission.submitted_at) }}</el-descriptions-item>
              <el-descriptions-item label="实践类型">{{ typeLabel(submission.practice_type) }}</el-descriptions-item>
            </el-descriptions>

            <div class="content-section">
              <h4>实践描述</h4>
              <div class="content-text">{{ submission.content }}</div>
            </div>

            <div class="content-section" v-if="submission.reflection">
              <h4>实践感想</h4>
              <div class="content-text">{{ submission.reflection }}</div>
            </div>

            <!-- 附件 -->
            <div class="content-section" v-if="submission.files?.length">
              <h4>附件材料</h4>
              <div class="files-grid">
                <div v-for="file in submission.files" :key="file.path" class="file-item">
                  <el-image
                    v-if="isImage(file.type)"
                    :src="file.path"
                    :preview-src-list="imageUrls"
                    fit="cover"
                    class="file-image"
                  />
                  <div v-else class="file-doc">
                    <el-icon><Document /></el-icon>
                    <span>{{ file.filename }}</span>
                  </div>
                </div>
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
import { submissionAPI, reviewAPI, annotationAPI } from '@/api'
import { ElMessage } from 'element-plus'
import PageLoading from '@/components/PageLoading.vue'

const route = useRoute()
const router = useRouter()
const loading = ref(true)
const submitting = ref(false)
const submission = ref(null)
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
const isImage = (type) => type?.startsWith('image/')
const imageUrls = computed(() => submission.value?.files?.filter(f => isImage(f.type)).map(f => f.path) || [])

const fetchSubmission = async () => {
  loading.value = true
  try {
    submission.value = await submissionAPI.getDetail(route.params.id)
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
.content-section { margin-bottom: 20px; }
.content-section h4 { font-size: 15px; color: #333; margin-bottom: 10px; padding-bottom: 6px; border-bottom: 1px solid #f0f0f0; }
.content-text { font-size: 14px; color: #555; line-height: 1.8; white-space: pre-wrap; }
.files-grid { display: flex; flex-wrap: wrap; gap: 10px; }
.file-image { width: 120px; height: 90px; border-radius: 4px; }
.file-doc { display: flex; align-items: center; gap: 6px; padding: 8px 12px; background: #f5f7fa; border-radius: 4px; font-size: 13px; color: #666; }
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
.add-annotation { margin-bottom: 12px; }
.annotation-item { padding: 12px 0; border-bottom: 1px solid #f0f0f0; }
.annotation-item:last-child { border-bottom: none; }
.annotation-header { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.annotation-author { font-weight: bold; font-size: 13px; color: #333; }
.annotation-time { font-size: 12px; color: #999; flex: 1; }
.annotation-quote { font-size: 13px; color: #888; padding: 6px 10px; background: #f5f7fa; border-left: 3px solid #409eff; margin-bottom: 6px; border-radius: 2px; }
.annotation-content { font-size: 14px; color: #555; line-height: 1.6; }
</style>
