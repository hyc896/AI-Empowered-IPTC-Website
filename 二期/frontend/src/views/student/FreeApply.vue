<template>
  <div class="free-apply">
    <div class="page-header">
      <el-button text @click="$router.back()"><el-icon><ArrowLeft /></el-icon> 返回</el-button>
      <h2>自由申请实践方案</h2>
      <p>已选知识点：<strong>{{ kpName }}</strong></p>
    </div>

    <el-steps :active="3" finish-status="success" class="steps">
      <el-step title="选择知识点" />
      <el-step title="设置参数" />
      <el-step title="选择实践类型" />
      <el-step title="填写方案" />
    </el-steps>

    <el-form :model="form" :rules="rules" ref="formRef" label-width="110px">
      <!-- 基本信息 -->
      <el-card class="section-card">
        <template #header><span>📋 基本信息</span></template>

        <el-form-item label="方案标题" prop="title">
          <el-input
            v-model="form.title"
            placeholder="请输入你的实践方案标题，要具体生动（不超过50字）"
            maxlength="50"
            show-word-limit
          />
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

        <el-form-item label="预计完成日期">
          <el-date-picker v-model="form.completion_date" type="date" placeholder="选择日期" style="width:100%" value-format="YYYY-MM-DD" />
        </el-form-item>

        <el-form-item label="实践场馆">
          <el-input
            :value="selectedVenueName || '随机生成（AI推荐）'"
            readonly
            @click="showVenueDialog = true"
          >
            <template #suffix>
              <el-icon @click.stop="clearVenue" v-if="form.venue_id" style="cursor:pointer"><CircleClose /></el-icon>
              <el-icon v-else><Location /></el-icon>
            </template>
          </el-input>
        </el-form-item>
      </el-card>

      <!-- 方案内容 -->
      <el-card class="section-card">
        <template #header><span>📝 方案内容</span></template>

        <el-form-item label="方案描述" prop="description">
          <el-input
            v-model="form.description"
            type="textarea"
            :autosize="{ minRows: 5, maxRows: 15 }"
            placeholder="请详细描述你的实践方案：&#10;- 你打算做什么？&#10;- 为什么选择这种方式？&#10;- 如何与知识点建立联系？&#10;- 具体的实施步骤是什么？"
            maxlength="2000"
            show-word-limit
          />
          <div class="hint">至少200字，描述越详细越好</div>
        </el-form-item>

        <el-form-item label="预期成果">
          <el-input
            v-model="form.expected_outcome"
            type="textarea"
            :autosize="{ minRows: 3, maxRows: 8 }"
            placeholder="你预计会产出什么成果？例如：一份调研报告、一段视频、一件手工作品..."
            maxlength="500"
            show-word-limit
          />
        </el-form-item>
      </el-card>

      <div class="footer-bar">
        <el-button @click="$router.back()">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submit">
          提交并开始实践
        </el-button>
      </div>
    </el-form>

    <!-- 场馆选择弹窗 -->
    <VenueSelect
      v-model="showVenueDialog"
      :current-venue-id="form.venue_id"
      :knowledge-point-id="kpId"
      @select="handleVenueSelect"
    />
  </div>
</template>

<script setup>
import { ref, reactive, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { practiceAPI } from '@/api'
import { useUserStore } from '@/stores/user'
import { ElMessage } from 'element-plus'
import VenueSelect from '@/components/VenueSelect.vue'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const formRef = ref(null)
const submitting = ref(false)
const showVenueDialog = ref(false)
const selectedVenueName = ref('')
const resultFormArr = ref([])

const kpId = route.query.kpId
const kpName = route.query.kpName
const venueId = route.query.venueId || ''

const form = reactive({
  title: '',
  description: '',
  expected_outcome: '',
  result_form: '',
  class_name_id: '',
  showcase_preference: 'original',
  instructor_name: '',
  completion_date: null,
  venue_id: venueId
})

watch(resultFormArr, (arr) => {
  form.result_form = arr.join(',')
}, { deep: true })

// 自动填充班级姓名学号
if (userStore.user) {
  const u = userStore.user
  if (u.class_name && u.real_name && u.username) {
    form.class_name_id = `${u.class_name} ${u.real_name} ${u.username}`
  }
}

const rules = {
  title: [
    { required: true, message: '请输入方案标题', trigger: 'blur' },
    { min: 5, message: '标题至少5个字', trigger: 'blur' }
  ],
  description: [
    { required: true, message: '请填写方案描述', trigger: 'blur' },
    { min: 200, message: '描述至少200字', trigger: 'blur' }
  ],
  class_name_id: [{ required: true, message: '请输入班级姓名学号', trigger: 'blur' }],
  instructor_name: [{ required: true, message: '请输入任课教师姓名', trigger: 'blur' }]
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

const submit = async () => {
  try {
    await formRef.value.validate()
  } catch {
    return
  }
  submitting.value = true
  try {
    const res = await practiceAPI.createFreePlan({
      knowledge_point_id: kpId,
      title: form.title,
      description: form.description,
      expected_outcome: form.expected_outcome || undefined,
      result_form: form.result_form || undefined,
      class_name_id: form.class_name_id || undefined,
      showcase_preference: form.showcase_preference,
      instructor_name: form.instructor_name || undefined,
      completion_date: form.completion_date || undefined,
      venue_id: form.venue_id || undefined
    })
    ElMessage.success('方案已创建，请继续提交实践成果')
    router.push({ name: 'PracticeSubmit', params: { planId: res.id } })
  } catch (e) {
    ElMessage.error(e.message || '提交失败，请重试')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.free-apply { width: 100%; max-width: 800px; margin: 0 auto; }
.page-header { margin-bottom: 20px; }
.page-header h2 { font-size: 22px; color: #333; margin: 8px 0 4px; }
.page-header p { color: #666; font-size: 14px; }
.steps { margin-bottom: 24px; }
.section-card { margin-bottom: 20px; }
.hint { font-size: 12px; color: #999; margin-top: 6px; }
.footer-bar {
  position: sticky; bottom: 0; background: #fff;
  padding: 16px 20px; margin-top: 24px;
  border-top: 1px solid #eee; display: flex;
  justify-content: flex-end; gap: 12px; border-radius: 8px;
}
</style>
