<template>
  <div class="practice-submit">
    <div class="page-header">
      <el-button text @click="$router.back()"><el-icon><ArrowLeft /></el-icon> 返回</el-button>
      <h2>提交实践成果</h2>
    </div>

    <PageLoading v-if="loading" />

    <el-form v-else :model="form" :rules="rules" ref="formRef" label-width="110px">
      <!-- 基本信息 -->
      <el-card class="section-card">
        <template #header><span>📋 基本信息</span></template>

        <el-form-item label="实践类别">
          <el-input :value="practiceTypeLabel" disabled />
        </el-form-item>

        <el-form-item label="实践题目" prop="title">
          <el-input v-model="form.title" placeholder="请输入实践题目" />
        </el-form-item>

        <el-form-item label="成果形式" prop="result_form">
          <el-checkbox-group v-model="resultFormArr">
            <el-checkbox value="文本图片">文本图片</el-checkbox>
            <el-checkbox value="音频视频">音频视频</el-checkbox>
            <el-checkbox value="实物">实物</el-checkbox>
            <el-checkbox value="其他">其他</el-checkbox>
          </el-checkbox-group>
        </el-form-item>

        <el-form-item label="班级姓名学号" prop="class_name_id">
          <el-input v-model="form.class_name_id" placeholder="例：2450 马智楠 24073101094" />
        </el-form-item>

        <el-form-item label="公众号展示" prop="showcase_preference">
          <el-radio-group v-model="form.showcase_preference">
            <el-radio value="none">不展示</el-radio>
            <el-radio value="original">原样展示</el-radio>
            <el-radio value="anonymous">匿名展示</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="任课教师" prop="instructor_name">
          <el-input v-model="form.instructor_name" placeholder="请输入任课教师姓名" />
        </el-form-item>

        <el-form-item label="提交日期">
          <el-date-picker v-model="form.completion_date" type="date" placeholder="选择日期" style="width:100%" value-format="YYYY-MM-DD" />
        </el-form-item>

        <el-form-item label="实践场馆">
          <div class="venue-selector">
            <el-input
              :value="selectedVenueName"
              placeholder="点击选择实践场馆（可选）"
              readonly
              @click="showVenueDialog = true"
            >
              <template #suffix>
                <el-icon @click.stop="clearVenue" v-if="form.venue_id" style="cursor:pointer"><CircleClose /></el-icon>
                <el-icon v-else><Location /></el-icon>
              </template>
            </el-input>
          </div>
        </el-form-item>
      </el-card>

      <!-- 场馆选择弹窗 -->
      <VenueSelect
        v-model="showVenueDialog"
        :current-venue-id="form.venue_id"
        :knowledge-point-id="plan?.knowledge_point_id || ''"
        @select="handleVenueSelect"
      />

      <!-- 实践步骤提交 -->
      <el-card v-for="(task, index) in plan?.tasks || []" :key="index" class="section-card task-card">
        <template #header>
          <div class="task-header">
            <div class="task-step-badge">步骤 {{ index + 1 }}</div>
            <span class="task-title">{{ task.task }}</span>
          </div>
        </template>

        <div class="task-description">{{ task.description }}</div>

        <!-- 动态渲染提交要求 -->
        <div class="task-requirements">
          <div v-for="(req, reqIndex) in task.submission_requirements || []" :key="reqIndex" class="requirement-block">
            <div class="requirement-label">
              <el-icon>
                <Upload v-if="isMediaType(req.type)" />
                <EditPen v-else />
              </el-icon>
              <span>{{ req.description || getRequirementLabel(req.type) }}</span>
              <span class="required-mark">*必填</span>
            </div>

            <div class="requirement-input">
              <!-- 媒体类型：文件上传 -->
              <template v-if="isMediaType(req.type)">
                <el-upload
                  v-model:file-list="taskFiles[index][reqIndex]"
                  action="#"
                  :auto-upload="false"
                  :accept="getMediaAccept(req.type)"
                  multiple
                  drag
                  class="upload-drag"
                >
                  <el-icon class="el-icon--upload"><Upload /></el-icon>
                  <div class="el-upload__text">拖拽文件到此处，或<em>点击上传</em></div>
                  <template #tip>
                    <div class="el-upload__tip">{{ getMediaTip(req.type) }}</div>
                  </template>
                </el-upload>
              </template>
              <!-- 文本类型：文字输入 -->
              <template v-else>
                <el-input
                  v-model="taskSubmissions[index][reqIndex]"
                  type="textarea"
                  :autosize="{ minRows: 4, maxRows: 30 }"
                  :placeholder="getTextPlaceholder(req)"
                  show-word-limit
                  :maxlength="req.max_words || 5000"
                />
                <div v-if="req.min_words" class="word-hint">最少{{ req.min_words }}字</div>
              </template>
            </div>
          </div>

          <!-- 没有提交要求时，提供通用文本区域 -->
          <div v-if="!task.submission_requirements || task.submission_requirements.length === 0" class="requirement-block">
            <div class="requirement-label">
              <el-icon><EditPen /></el-icon>
              <span>实践内容描述</span>
            </div>
            <div class="requirement-input">
              <el-input
                v-model="taskSubmissions[index][0]"
                type="textarea"
                :autosize="{ minRows: 4, maxRows: 30 }"
                placeholder="请描述你完成本步骤的详细过程和成果..."
                show-word-limit
                :maxlength="5000"
              />
            </div>
          </div>
        </div>
      </el-card>

      <!-- 附件上传 -->
      <el-card class="section-card">
        <template #header><span>📎 附件上传（可选）</span></template>
        <p class="attachment-tip">可上传实践过程中的照片、视频、文档等作为辅助材料</p>
        <el-upload
          v-model:file-list="attachmentFiles"
          action="#"
          :auto-upload="false"
          accept="image/*,video/*,audio/*,.pdf,.doc,.docx"
          multiple
          drag
          class="upload-drag"
        >
          <el-icon class="el-icon--upload"><Upload /></el-icon>
          <div class="el-upload__text">拖拽文件到此处，或<em>点击上传</em></div>
          <template #tip>
            <div class="el-upload__tip">支持图片、视频、音频、PDF、Word 文档，单个文件不超过 50MB</div>
          </template>
        </el-upload>
      </el-card>

      <!-- 学生建议 -->
      <el-card class="section-card">
        <template #header><span>💬 学生建议</span></template>
        <el-form-item label="实践建议" prop="reflection">
          <el-input
            v-model="form.reflection"
            type="textarea"
            :autosize="{ minRows: 4, maxRows: 20 }"
            placeholder="对本次实践模式有什么建议？（可选）比如：任务难度是否合适、实践形式是否有趣、有哪些可以改进的地方..."
            show-word-limit
            maxlength="1000"
          />
        </el-form-item>
      </el-card>

      <!-- 操作按钮 -->
      <div class="footer-bar">
        <el-button @click="saveDraft" :loading="saving">保存草稿</el-button>
        <el-button type="success" @click="generateReport" :loading="generatingReport" :disabled="!canGenerateReport">
          <el-icon><Document /></el-icon> 一键生成报告
        </el-button>
        <el-button type="primary" @click="submitForReview" :loading="submitting">提交审核</el-button>
      </div>
    </el-form>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { submissionAPI, practiceAPI } from '@/api'
import { useUserStore } from '@/stores/user'
import { ElMessage, ElMessageBox } from 'element-plus'
import PageLoading from '@/components/PageLoading.vue'
import VenueSelect from '@/components/VenueSelect.vue'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const formRef = ref(null)
const loading = ref(true)
const saving = ref(false)
const submitting = ref(false)
const generatingReport = ref(false)
const submissionId = ref(null)
const plan = ref(null)
const taskSubmissions = ref([])
const taskFiles = ref([])  // 2D: taskFiles[taskIndex][reqIndex] = FileList[]
const attachmentFiles = ref([])
const resultFormArr = ref([])
const showVenueDialog = ref(false)
const selectedVenueName = ref('')

const practiceTypeMap = {
  writing: '写作设计类',
  presentation: '宣传表达类',
  visit: '参观研学类',
  performance: '表演体验类',
  interaction: '交往行动类',
  production: '生产改造类',
  free: '自由申请类'
}

const practiceTypeLabel = computed(() => {
  return practiceTypeMap[plan.value?.practice_type] || plan.value?.practice_type || ''
})

const form = reactive({
  title: '',
  reflection: '',
  completion_date: null,
  class_name_id: '',
  showcase_preference: 'original',
  instructor_name: '',
  result_form: '',
  venue_id: ''
})

// 同步 resultFormArr <-> form.result_form（逗号分隔存储）
watch(resultFormArr, (arr) => {
  form.result_form = arr.join(',')
}, { deep: true })

const rules = {
  title: [{ required: true, message: '请输入实践题目', trigger: 'blur' }],
  class_name_id: [{ required: true, message: '请输入班级姓名学号', trigger: 'blur' }],
  instructor_name: [{ required: true, message: '请输入任课教师姓名', trigger: 'blur' }]
}

const canGenerateReport = computed(() => {
  if (!form.title || !form.class_name_id) return false
  return taskSubmissions.value.some(subs =>
    subs.some(v => typeof v === 'string' && v.trim().length > 0)
  ) || taskFiles.value.some(slots => slots.some(files => files.length > 0))
})

const getRequirementLabel = (type) => {
  const labels = {
    photo: '照片说明',
    video: '视频说明',
    audio: '音频说明',
    document: '文档内容',
    text: '文字说明',
    url: '链接'
  }
  return labels[type] || '内容描述'
}

const getTextPlaceholder = (req) => {
  if (req.description) return req.description
  const placeholders = {
    photo: '请描述你拍摄的照片内容，包括地点、时间和你的观察感受...',
    video: '请描述视频内容，包括拍摄主题、主要画面和你想表达的内容...',
    audio: '请描述音频内容，包括录制主题和主要内容...',
    document: '请输入你的文档内容...',
    text: '请输入文字内容...',
    url: '请输入相关链接并描述其内容...'
  }
  return placeholders[req.type] || '请输入内容...'
}

const isMediaType = (type) => ['photo', 'video', 'audio'].includes(type)

const getMediaAccept = (type) => {
  if (type === 'photo') return 'image/*'
  if (type === 'video') return 'video/*'
  if (type === 'audio') return 'audio/*'
  return 'image/*,video/*,audio/*'
}

const getMediaTip = (type) => {
  if (type === 'photo') return '支持 JPG、PNG、GIF、WebP 等图片格式，单个文件不超过 50MB'
  if (type === 'video') return '支持 MP4、MOV、AVI 等视频格式，单个文件不超过 500MB'
  if (type === 'audio') return '支持 MP3、WAV、M4A 等音频格式，单个文件不超过 100MB'
  return '支持图片、视频、音频，单个文件不超过 500MB'
}

const handleVenueSelect = (venue) => {
  if (venue) {
    form.venue_id = venue.id
    selectedVenueName.value = venue.name
  } else {
    form.venue_id = ''
    selectedVenueName.value = ''
  }
}

const clearVenue = () => {
  form.venue_id = ''
  selectedVenueName.value = ''
}

const fetchPlan = async () => {
  loading.value = true
  try {
    plan.value = await practiceAPI.getPlanDetail(route.params.planId)
    form.title = plan.value.title

    // 初始化taskSubmissions结构 —— 全部使用文本输入
    taskSubmissions.value = (plan.value.tasks || []).map(task => {
      const reqs = task.submission_requirements || []
      if (reqs.length > 0) {
        return reqs.map(() => '')
      }
      return ['']
    })

    // 初始化taskFiles结构 —— 媒体类型槽位的文件列表
    taskFiles.value = (plan.value.tasks || []).map(task => {
      const reqs = task.submission_requirements || []
      if (reqs.length > 0) {
        return reqs.map(() => [])
      }
      return [[]]
    })

    // 尝试从 userStore 自动填充一些字段
    if (userStore.user) {
      const u = userStore.user
      if (u.class_name && u.real_name && u.username) {
        form.class_name_id = `${u.class_name} ${u.real_name} ${u.username}`
      }
    }
  } catch (e) {
    ElMessage.error('获取方案失败')
  } finally {
    loading.value = false
  }
}

const buildSubmitData = () => {
  return {
    plan_id: route.params.planId,
    practice_type: plan.value.practice_type,
    title: form.title,
    content: JSON.stringify(taskSubmissions.value),
    reflection: form.reflection || null,
    completion_date: form.completion_date || null,
    result_form: form.result_form || null,
    class_name_id: form.class_name_id || null,
    showcase_preference: form.showcase_preference || 'original',
    instructor_name: form.instructor_name || null,
    venue_id: form.venue_id || null
  }
}

const saveDraft = async () => {
  saving.value = true
  try {
    if (!submissionId.value) {
      const res = await submissionAPI.create(buildSubmitData())
      submissionId.value = res.id
    } else {
      await submissionAPI.update(submissionId.value, buildSubmitData())
    }

    // 上传附件 + 各步骤媒体文件
    const allFiles = [
      ...attachmentFiles.value.filter(f => f.raw).map(f => f.raw),
      ...taskFiles.value.flat().flat().filter(f => f.raw).map(f => f.raw)
    ]
    if (allFiles.length > 0 && submissionId.value) {
      await submissionAPI.uploadFiles(submissionId.value, allFiles)
    }

    ElMessage.success('草稿已保存')
  } catch (e) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

const validateMaterials = () => {
  const missing = []
  const tasks = plan.value?.tasks || []
  tasks.forEach((task, taskIndex) => {
    const reqs = task.submission_requirements || []
    if (reqs.length > 0) {
      reqs.forEach((req, reqIndex) => {
        if (isMediaType(req.type)) {
          const files = taskFiles.value[taskIndex]?.[reqIndex] || []
          if (files.length === 0) {
            missing.push(`步骤${taskIndex + 1}「${task.task}」的${req.description || getRequirementLabel(req.type)}（请上传文件）`)
          }
        } else {
          const value = taskSubmissions.value[taskIndex]?.[reqIndex]
          if (!value || !value.trim()) {
            missing.push(`步骤${taskIndex + 1}「${task.task}」的${req.description || getRequirementLabel(req.type)}`)
          } else if (req.min_words && value.trim().length < req.min_words) {
            missing.push(`步骤${taskIndex + 1}「${task.task}」的${req.description || '文字说明'}（至少${req.min_words}字）`)
          }
        }
      })
    } else {
      const value = taskSubmissions.value[taskIndex]?.[0]
      if (!value || !value.trim()) {
        missing.push(`步骤${taskIndex + 1}「${task.task}」的实践内容描述`)
      }
    }
  })
  return missing
}

const submitForReview = async () => {
  try {
    await formRef.value.validate()
  } catch (error) {
    return
  }

  // 校验材料完整性
  const missing = validateMaterials()
  if (missing.length > 0) {
    ElMessageBox.alert(
      `<div style="max-height:300px;overflow:auto"><p style="margin-bottom:8px;font-weight:bold">以下材料尚未提交：</p><ul style="padding-left:20px">${missing.map(m => `<li style="margin:4px 0;color:#e6a23c">${m}</li>`).join('')}</ul></div>`,
      '材料不完整',
      { dangerouslyUseHTMLString: true, type: 'warning', confirmButtonText: '去补充' }
    )
    return
  }

  try {
    await ElMessageBox.confirm('提交后不能修改，确认提交审核？', '确认提交', { type: 'warning' })
  } catch {
    return
  }

  submitting.value = true
  try {
    // 先保存
    if (!submissionId.value) {
      const res = await submissionAPI.create(buildSubmitData())
      submissionId.value = res.id
    } else {
      await submissionAPI.update(submissionId.value, buildSubmitData())
    }

    // 上传附件 + 各步骤媒体文件
    const allFiles = [
      ...attachmentFiles.value.filter(f => f.raw).map(f => f.raw),
      ...taskFiles.value.flat().flat().filter(f => f.raw).map(f => f.raw)
    ]
    if (allFiles.length > 0 && submissionId.value) {
      await submissionAPI.uploadFiles(submissionId.value, allFiles)
    }

    // 正式提交
    await submissionAPI.submit(submissionId.value)
    ElMessage.success('提交成功！等待教师审核')
    router.push('/student/my-practices')
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('提交失败，请重试')
  } finally {
    submitting.value = false
  }
}

const generateReport = async () => {
  generatingReport.value = true
  try {
    // 先保存当前数据
    if (!submissionId.value) {
      const res = await submissionAPI.create(buildSubmitData())
      submissionId.value = res.id
    } else {
      await submissionAPI.update(submissionId.value, buildSubmitData())
    }

    // 调用报告生成接口
    const response = await submissionAPI.generateReport(submissionId.value)

    // 下载生成的 Word 文档
    const blob = new Blob([response], { type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${form.title || '实践报告'}.docx`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url)

    ElMessage.success('报告已生成并下载')
  } catch (e) {
    ElMessage.error(e.message || '报告生成失败，请确保已填写必要内容')
  } finally {
    generatingReport.value = false
  }
}

onMounted(fetchPlan)
</script>

<style scoped>
.practice-submit { width: 100%; max-width: 900px; margin: 0 auto; }
.page-header { margin-bottom: 20px; }
.page-header h2 { font-size: 22px; color: #333; margin: 8px 0; }

.section-card { margin-top: 20px; }
.section-card:first-child { margin-top: 0; }

/* 任务卡片 */
.task-card :deep(.el-card__header) { background: #fafbfc; }
.task-header { display: flex; align-items: center; gap: 10px; }
.task-step-badge {
  background: #409eff; color: #fff; font-size: 12px;
  padding: 2px 10px; border-radius: 12px; white-space: nowrap;
}
.task-title { font-size: 15px; font-weight: bold; color: #333; }
.task-description {
  font-size: 14px; color: #666; line-height: 1.7;
  padding: 14px 16px; background: #f5f7fa; border-radius: 6px;
  margin-bottom: 20px;
}

/* 提交要求区域 */
.task-requirements { display: flex; flex-direction: column; gap: 24px; }
.requirement-block {
  padding: 16px 0;
  border-top: 1px dashed #e8e8e8;
}
.requirement-block:first-child { border-top: none; padding-top: 0; }
.requirement-label {
  display: flex; align-items: center; gap: 6px;
  font-size: 14px; font-weight: 500; color: #333;
  margin-bottom: 12px;
}
.requirement-label .el-icon { color: #409eff; font-size: 16px; }
.required-mark { font-size: 11px; color: #f56c6c; margin-left: 4px; }
.requirement-input { padding-left: 22px; }

/* 附件上传 */
.attachment-tip {
  font-size: 13px; color: #999; margin: 0 0 12px;
}
.upload-drag { width: 100%; }
.upload-drag :deep(.el-upload-dragger) {
  padding: 30px 0;
  width: 100%;
}

.word-hint { font-size: 12px; color: #999; margin-top: 6px; }

.venue-selector { width: 100%; }
.venue-selector .el-input { cursor: pointer; }
.venue-selector :deep(.el-input__inner) { cursor: pointer; }

.footer-bar {
  position: sticky; bottom: 0; background: #fff;
  padding: 16px 20px; margin-top: 24px;
  border-top: 1px solid #eee; display: flex;
  justify-content: flex-end; gap: 12px; border-radius: 8px;
  box-shadow: 0 -2px 8px rgba(0,0,0,0.04);
}
</style>
