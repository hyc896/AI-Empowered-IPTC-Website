<template>
  <div class="practice-type-select">
    <div class="page-header">
      <el-button text @click="$router.back()"><el-icon><ArrowLeft /></el-icon> 返回</el-button>
      <h2>选择实践类型</h2>
      <p>已选知识点：<strong>{{ kpName }}</strong></p>
    </div>

    <el-steps :active="currentTask?.status === 'generating' ? 3 : 2" finish-status="success" class="steps">
      <el-step title="选择知识点" />
      <el-step title="自定义详情" />
      <el-step title="选择实践类型" :description="currentTask?.status === 'generating' ? currentTask.text : ''" />
      <el-step title="查看方案" />
    </el-steps>

    <div class="tip">请选择 <strong>1种</strong> 实践类型，系统将为你生成个性化方案。<strong>悬停卡片</strong>可查看实践目标与转化渠道</div>

    <div class="types-container">
      <div class="type-grid">
        <div
          v-for="type in practiceTypes.slice(0, 6)"
          :key="type.value"
          class="flip-card"
          :class="{ selected: selected === type.value }"
          @click="selected = type.value"
        >
          <div class="flip-inner">
            <!-- 正面 -->
            <div class="flip-front">
              <div class="type-icon">{{ type.icon }}</div>
              <h3>{{ type.label }}</h3>
              <p class="type-desc">{{ type.desc }}</p>
              <div class="card-tags">
                <el-tag size="small" :type="type.tagType">{{ type.tag }}</el-tag>
                <el-tag v-if="type.channels && type.channels.length" size="small" type="warning" effect="plain" class="channel-tag">
                  {{ type.channels[0] }}
                </el-tag>
              </div>
            </div>
            <!-- 背面 -->
            <div class="flip-back">
              <h4>实践目标</h4>
              <p class="goal-text">{{ type.goal }}</p>
              <h4>转化渠道</h4>
              <div class="channel-list">
                <span v-for="(ch, ci) in type.channels" :key="ci" class="channel-item">{{ ch }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 自由申请类单独一行 -->
      <div class="free-type-row">
        <div
          class="flip-card free-card-wrapper"
          :class="{ selected: selected === 'free' }"
          @click="selected = 'free'"
        >
          <div class="flip-inner">
            <div class="flip-front free-front">
              <div class="type-icon">🌟</div>
              <div class="free-text">
                <h3>自由申请类</h3>
                <p>自主设计实践方案，填写申请内容，由教师审核通过后方可开展</p>
              </div>
              <el-tag size="small" type="info">自主填写</el-tag>
              <el-tag size="small" type="warning" effect="plain">需教师审批</el-tag>
            </div>
            <div class="flip-back free-back">
              <h4>实践目标</h4>
              <p class="goal-text">鼓励学生结合自身特点选择其他实践项目，实践内容和成果形式需提前向任课教师申请，获批后方可开展。</p>
              <h4>转化渠道</h4>
              <span class="channel-item">由教师根据具体方案建议</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="footer-bar">
      <el-button type="primary" :disabled="!selected" :loading="generating" @click="handleNext">
        <template v-if="selected === 'free'">
          填写自由申请方案 <el-icon><EditPen /></el-icon>
        </template>
        <template v-else>
          生成实践方案（约15秒）<el-icon><MagicStick /></el-icon>
        </template>
      </el-button>
    </div>

    <!-- 使用规则弹窗 -->
    <el-dialog v-model="showRulesDialog" title="" width="480px" :close-on-click-modal="false" :show-close="false" class="rules-dialog">
      <div class="notice-content">
        <div class="notice-header">
          <div class="notice-title">选择实践方案</div>
          <div class="notice-subtitle">了解两种方案类型的区别</div>
        </div>
        <div class="notice-sections">
          <div class="notice-section">
            <div class="section-left">
              <div class="section-num">01</div>
            </div>
            <div class="section-body">
              <h4>AI 智能生成</h4>
              <p>选择前 6 种类型，AI 根据知识点和难度自动生成完整方案，包含详细步骤与推荐场馆</p>
            </div>
          </div>
          <div class="notice-divider"></div>
          <div class="notice-section">
            <div class="section-left">
              <div class="section-num">02</div>
            </div>
            <div class="section-body">
              <h4>自由申请</h4>
              <p>自主设计实践内容并填写描述，提交后由教师审核，通过后方可开展</p>
            </div>
          </div>
        </div>
        <div class="notice-footer">
          <button :disabled="countdown > 0" @click="closeRulesDialog" class="ok-btn">
            <span v-if="countdown > 0">{{ countdown }} 秒后可关闭</span>
            <span v-else>知道了，开始选择</span>
          </button>
        </div>
      </div>
    </el-dialog>

    <!-- 安全须知弹窗 -->
    <el-dialog v-model="showSafetyDialog" title="" width="480px" :close-on-click-modal="false" :show-close="false" class="rules-dialog">
      <div class="notice-content">
        <div class="notice-header">
          <div class="notice-title">实践安全须知</div>
          <div class="notice-subtitle">请仔细阅读以下安全提示</div>
        </div>
        <div class="safety-body">
          <div class="safety-item">
            <span class="safety-num">1</span>
            <span>外出实践前须告知辅导员或指导教师，不得擅自前往偏远或危险地区</span>
          </div>
          <div class="safety-item">
            <span class="safety-num">2</span>
            <span>注意人身与财产安全，结伴出行，保持通讯畅通</span>
          </div>
          <div class="safety-item">
            <span class="safety-num">3</span>
            <span>遵守实践场所的规章制度，尊重当地风俗习惯</span>
          </div>
          <div class="safety-item">
            <span class="safety-num">4</span>
            <span>如遇突发情况，第一时间联系指导教师并拨打紧急电话</span>
          </div>
          <div class="safety-item">
            <span class="safety-num">5</span>
            <span>实践活动中不得从事违法违规行为，不得发表不当言论</span>
          </div>
        </div>
        <div class="safety-commitment">
          <el-checkbox v-model="safetyAgreed">我已认真阅读并承诺遵守以上安全须知</el-checkbox>
        </div>
        <div class="notice-footer">
          <button :disabled="safetyCountdown > 0 || !safetyAgreed" @click="closeSafetyDialog" class="ok-btn">
            <span v-if="safetyCountdown > 0">{{ safetyCountdown }} 秒后可确认</span>
            <span v-else-if="!safetyAgreed">请先勾选承诺</span>
            <span v-else>确认并继续</span>
          </button>
        </div>
      </div>
    </el-dialog>

    <!-- 生成中弹窗（可关闭） -->
    <el-dialog v-model="showProgress" title="" :close-on-click-modal="true" width="400px" class="generating-dialog">
      <div class="generating-content">
        <div class="loader"></div>
        <p class="generating-text">{{ currentTask?.text || '正在生成...' }}</p>
        <div class="generating-steps">
          <div v-for="(step, i) in progressSteps" :key="i" class="step-item" :class="{ active: i <= (currentTask?.step ?? -1) }">
            <span class="step-dot"></span>
            <span>{{ step }}</span>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="showProgress = false">后台生成，继续其他操作</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { practiceAPI } from '@/api'
import { ElMessage } from 'element-plus'
import { useTaskStore } from '@/stores/task'

const route = useRoute()
const router = useRouter()
const taskStore = useTaskStore()
const kpId = route.query.kpId
const kpName = route.query.kpName
const mode = route.query.mode || 'individual'
const groupDivision = route.query.groupDivision || ''
const difficulty = route.query.difficulty || 'easy'
const venueId = route.query.venueId || ''
const selected = ref('')
const generating = ref(false)
const showProgress = ref(false)
const currentTaskId = ref(null)
const showRulesDialog = ref(false)
const countdown = ref(5)
const showSafetyDialog = ref(false)
const safetyCountdown = ref(5)
const safetyAgreed = ref(false)

const currentTask = computed(() =>
  taskStore.generatingTasks.find(t => t.taskId === currentTaskId.value)
)

const progressSteps = [
  '分析知识点内容',
  '构建方案框架',
  'AI生成详细步骤',
  '整理推荐场馆',
  '方案即将完成',
  '最终检查'
]

const practiceTypes = [
  {
    value: 'writing', label: '写作设计类', icon: '✍️',
    desc: '撰写论文、调研报告、设计方案',
    tag: '独立完成', tagType: 'primary',
    goal: '围绕课程教材的理论知识点，结合自身实际，创新创业或设计创作，撰写完整的项目方案或学术论文。',
    channels: ['挑战杯', '互联网+创新大赛', '红色旅游创意策划大赛', '文创设计大赛']
  },
  {
    value: 'presentation', label: '宣传表达类', icon: '📢',
    desc: '演讲、辩论、制作短视频、海报',
    tag: '创意表达', tagType: 'success',
    goal: '围绕理论知识点宣传推广城市家乡、红色资源、民俗文化等，或开展辩论、理论宣讲活动。',
    channels: ['全国大学生讲解大赛', '大学生社区创课大赛', '高校理论宣讲微课程比赛', '尚法杯辩论赛']
  },
  {
    value: 'visit', label: '参观研学类', icon: '🏛️',
    desc: '参观博物馆、纪念馆、红色基地',
    tag: '需外出', tagType: 'warning',
    goal: '利用全国各地资源（如上海"红途"平台），参观红色场馆、习近平总书记足迹之地，撰写研学报告。',
    channels: ['红途平台打卡', '习近平足迹之地', '校级研学报告评选']
  },
  {
    value: 'performance', label: '表演体验类', icon: '🎭',
    desc: '情景剧、角色扮演、模拟演练',
    tag: '团队协作', tagType: 'danger',
    goal: '在模拟情境中沉浸式感悟习近平新时代中国特色社会主义思想，参与情景表演、节目活动、体验数字文创等。',
    channels: ['校园话剧展演', '数字文创体验活动', '红色情景剧比赛']
  },
  {
    value: 'interaction', label: '交往行动类', icon: '🤝',
    desc: '社会调研、法庭旁听、人物采访',
    tag: '社会实践', tagType: 'primary',
    goal: '通过社会交往了解国情、社情、民情，开展社会调研、法庭旁听、人物采访等，提升交往能力和分析能力。',
    channels: ['挑战杯红色专项', '知行杯社会实践', '从法杯调研大赛', '读懂中国活动']
  },
  {
    value: 'production', label: '生产改造类', icon: '🔧',
    desc: '志愿服务、建言献策、网络传播',
    tag: '动手实践', tagType: 'success',
    goal: '在实践中学习理论、检验理论，参加志愿服务、网络传播、建言献策、立法征询等，培养社会服务意识。',
    channels: ['奉献杯志愿服务大赛', '全国大学生网络文化节', '模拟政协提案大赛', '人民网建言献策']
  },
  {
    value: 'free', label: '自由申请类', icon: '🌟',
    desc: '自主设计实践方案，填写申请内容，由教师审核',
    tag: '自主填写', tagType: 'info',
    goal: '鼓励学生结合自身特点选择其他实践项目，实践内容和成果形式需提前向任课教师申请。',
    channels: ['由教师根据具体方案建议']
  }
]

// 每次进入都显示规则弹窗
onMounted(() => {
  showRulesDialog.value = true
  startCountdown()
})

const startCountdown = () => {
  const timer = setInterval(() => {
    countdown.value--
    if (countdown.value <= 0) {
      clearInterval(timer)
    }
  }, 1000)
}

const closeRulesDialog = () => {
  showRulesDialog.value = false
  showSafetyDialog.value = true
  startSafetyCountdown()
}

const startSafetyCountdown = () => {
  const timer = setInterval(() => {
    safetyCountdown.value--
    if (safetyCountdown.value <= 0) {
      clearInterval(timer)
    }
  }, 1000)
}

const closeSafetyDialog = () => {
  showSafetyDialog.value = false
}

const handleNext = () => {
  if (selected.value === 'free') {
    router.push({ name: 'FreeApply', query: { kpId, kpName, venueId: venueId || undefined } })
  } else {
    generate()
  }
}

const generate = async () => {
  generating.value = true
  try {
    const res = await practiceAPI.generatePlan({
      knowledge_point_id: kpId,
      practice_type: selected.value,
      venue_id: venueId || undefined,
      preferences: {
        location: '上海',
        mode,
        group_division: groupDivision || undefined,
        difficulty
      }
    })

    // 交给全局 taskStore 管理轮询
    const typeLabel = practiceTypes.find(t => t.value === selected.value)?.label || selected.value
    taskStore.addTask(res.task_id, `${kpName} - ${typeLabel}`, selected.value)
    currentTaskId.value = res.task_id
    showProgress.value = true
  } catch (e) {
    ElMessage.error(e.message || '提交失败，请重试')
  } finally {
    generating.value = false
  }
}

// 监听任务完成，自动关闭弹窗并跳转
watch(currentTask, (task) => {
  if (!task) {
    if (showProgress.value) {
      showProgress.value = false
    }
    return
  }
  if (task.status === 'success') {
    showProgress.value = false
    router.push(`/student/plan/${currentTaskId.value}`)
  } else if (task.status === 'failed') {
    showProgress.value = false
  }
}, { deep: true })
</script>

<style scoped>
.practice-type-select {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.page-header { margin-bottom: 16px; flex-shrink: 0; }
.page-header h2 { font-size: 22px; color: #333; margin: 8px 0 4px; }
.page-header p { color: #666; font-size: 14px; }
.steps { margin-bottom: 20px; flex-shrink: 0; }
.tip { background: #fff7e6; border: 1px solid #ffd591; border-radius: 6px; padding: 10px 16px; margin-bottom: 16px; color: #d46b08; font-size: 14px; flex-shrink: 0; }

.types-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 0;
  overflow: hidden;
}

.type-grid {
  flex: 2;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  grid-template-rows: repeat(2, 1fr);
  gap: 12px;
  min-height: 0;
}

/* === 翻转卡片 === */
.flip-card {
  perspective: 800px;
  cursor: pointer;
  min-height: 0;
}
.flip-inner {
  position: relative;
  width: 100%;
  height: 100%;
  transition: transform 0.5s ease;
  transform-style: preserve-3d;
}
.flip-card:hover .flip-inner {
  transform: rotateY(180deg);
}
.flip-card.selected .flip-front {
  border-color: #c0392b;
  background: #fff5f5;
}
.flip-card.selected .flip-back {
  border-color: #c0392b;
}
.flip-front, .flip-back {
  position: absolute;
  top: 0; left: 0;
  width: 100%;
  height: 100%;
  backface-visibility: hidden;
  border: 2px solid #eee;
  border-radius: 10px;
  overflow: hidden;
}
.flip-front {
  background: #fff;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 12px 10px;
  text-align: center;
  z-index: 2;
}
.flip-back {
  background: #fafafa;
  transform: rotateY(180deg);
  padding: 14px 16px;
  overflow-y: auto;
}

.type-icon { font-size: 26px; margin-bottom: 6px; }
.flip-front h3 { font-size: 14px; color: #333; margin-bottom: 3px; }
.type-desc { font-size: 11px; color: #888; margin-bottom: 6px; line-height: 1.3; }
.card-tags { display: flex; gap: 4px; flex-wrap: wrap; justify-content: center; }
.channel-tag { font-size: 11px !important; }

.flip-back h4 {
  font-size: 12px;
  color: #c0392b;
  margin: 0 0 6px;
  font-weight: 600;
}
.goal-text {
  font-size: 11px;
  color: #555;
  line-height: 1.5;
  margin: 0 0 10px;
}
.channel-list {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.channel-item {
  font-size: 10px;
  background: #fff7e6;
  color: #d46b08;
  padding: 2px 6px;
  border-radius: 3px;
  border: 1px solid #ffd591;
  white-space: nowrap;
}

/* === 自由申请类 === */
.free-type-row {
  flex: 1;
  min-height: 0;
}
.free-card-wrapper {
  height: 100%;
}
.free-card-wrapper .flip-inner:hover {
  transform: rotateY(180deg);
}
.free-front {
  flex-direction: row !important;
  gap: 16px;
  text-align: left !important;
  padding: 20px 28px !important;
  align-items: center !important;
}
.free-front .type-icon { margin-bottom: 0; font-size: 36px; }
.free-text { flex: 1; }
.free-text h3 { font-size: 17px; margin-bottom: 4px; }
.free-text p { font-size: 13px; color: #888; margin: 0; }
.free-back {
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 20px 28px !important;
}
.free-back h4 { font-size: 14px; }
.free-back .goal-text { font-size: 13px; }
.free-back .channel-item { font-size: 12px; }

.footer-bar {
  flex-shrink: 0;
  background: #fff;
  padding: 16px 0;
  margin-top: 12px;
  border-top: 1px solid #eee;
  display: flex;
  justify-content: flex-end;
}

/* 使用规则弹窗 */
.rules-dialog :deep(.el-dialog__header) { display: none; }
.rules-dialog :deep(.el-dialog__body) { padding: 0; }
.rules-dialog :deep(.el-dialog) { border-radius: 16px; overflow: hidden; }

.notice-content {
  padding: 36px 36px 32px;
}
.notice-header {
  margin-bottom: 28px;
}
.notice-title {
  font-size: 22px;
  font-weight: 700;
  color: #1a1a1a;
  letter-spacing: -0.3px;
  margin-bottom: 6px;
}
.notice-subtitle {
  font-size: 13px;
  color: #999;
}
.notice-sections {
  display: flex;
  flex-direction: column;
  gap: 0;
  margin-bottom: 28px;
  border: 1px solid #f0f0f0;
  border-radius: 12px;
  overflow: hidden;
}
.notice-section {
  display: flex;
  align-items: flex-start;
  gap: 18px;
  padding: 20px 22px;
  background: #fff;
}
.notice-divider {
  height: 1px;
  background: #f0f0f0;
}
.section-left {
  flex-shrink: 0;
}
.section-num {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: #1a1a1a;
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  letter-spacing: 0.5px;
}
.section-body h4 {
  font-size: 14px;
  font-weight: 600;
  color: #1a1a1a;
  margin: 0 0 6px;
  padding-top: 7px;
}
.section-body p {
  font-size: 13px;
  color: #888;
  line-height: 1.65;
  margin: 0;
}
.notice-footer {
  display: flex;
  justify-content: flex-end;
}
.ok-btn {
  padding: 11px 28px;
  background: #1a1a1a;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: opacity 0.15s, transform 0.15s;
  min-width: 140px;
}
.ok-btn:hover:not(:disabled) {
  opacity: 0.85;
  transform: translateY(-1px);
}
.ok-btn:disabled {
  background: #e8e8e8;
  color: #bbb;
  cursor: not-allowed;
  transform: none;
}

/* 生成弹窗 */
.generating-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 30px 20px 20px;
}
.loader {
  width: fit-content;
  font-size: 40px;
  font-family: monospace;
  font-weight: bold;
  text-transform: uppercase;
  color: #0000;
  -webkit-text-stroke: 1px #000;
  background: linear-gradient(90deg, #0000 33%, #000 0 67%, #0000 0) 100%/300%
    100% no-repeat text;
  animation: l12 4s steps(14) infinite;
}
.loader:before {
  content: "Loading";
}
@keyframes l12 {
  to {
    background-position: 0;
  }
}
.generating-text {
  margin-top: 20px;
  color: #333;
  font-size: 15px;
  font-weight: 500;
}
.generating-steps {
  margin-top: 24px;
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.step-item {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  color: #ccc;
  transition: color 0.3s;
}
.step-item.active {
  color: #333;
}
.step-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #ddd;
  transition: background 0.3s;
  flex-shrink: 0;
}
.step-item.active .step-dot {
  background: #67c23a;
}

/* 安全须知弹窗 */
.safety-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 20px;
  border: 1px solid #f0f0f0;
  border-radius: 12px;
  padding: 16px 20px;
  background: #fafafa;
}
.safety-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  font-size: 13px;
  color: #555;
  line-height: 1.6;
}
.safety-num {
  flex-shrink: 0;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #1a1a1a;
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 1px;
}
.safety-commitment {
  margin-bottom: 20px;
  padding: 12px 16px;
  background: #fff7e6;
  border: 1px solid #ffd591;
  border-radius: 8px;
}
</style>
