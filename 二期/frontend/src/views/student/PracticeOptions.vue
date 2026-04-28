<template>
  <div class="practice-options">
    <div class="page-header">
      <el-button text @click="$router.back()"><el-icon><ArrowLeft /></el-icon> 返回</el-button>
      <h2>自定义详情</h2>
      <p>已选知识点：<strong>{{ kpName }}</strong></p>
    </div>

    <el-steps :active="1" finish-status="success" class="steps">
      <el-step title="选择知识点" />
      <el-step title="自定义详情" />
      <el-step title="选择实践类型" />
      <el-step title="查看方案" />
    </el-steps>

    <div class="content-wrapper">
      <!-- 左侧：完成方式 -->
      <el-card class="option-card left-card">
        <template #header><span>完成方式</span></template>
        <div class="mode-grid">
          <div
            class="mode-item"
            :class="{ selected: mode === 'individual' }"
            @click="mode = 'individual'"
          >
            <div class="mode-icon"><el-icon :size="32"><User /></el-icon></div>
            <div class="mode-label">个人完成</div>
            <div class="mode-desc">独立完成全部任务，自主安排时间</div>
          </div>
          <div
            class="mode-item"
            :class="{ selected: mode === 'group' }"
            @click="mode = 'group'"
          >
            <div class="mode-icon"><el-icon :size="32"><UserFilled /></el-icon></div>
            <div class="mode-label">集体完成</div>
            <div class="mode-desc">团队协作，分工合作完成任务</div>
          </div>
        </div>

        <!-- 集体分工 -->
        <div v-if="mode === 'group'" class="group-division">
          <el-divider />
          <div class="division-label">团队成员与分工 <span class="required">*</span></div>
          <el-table :data="groupMembers" border style="width: 100%" size="small">
            <el-table-column label="姓名" width="120">
              <template #default="{ row }">
                <el-input v-model="row.name" placeholder="成员姓名" size="small" />
              </template>
            </el-table-column>
            <el-table-column label="学号" width="140">
              <template #default="{ row }">
                <el-input v-model="row.studentId" placeholder="学号" size="small" />
              </template>
            </el-table-column>
            <el-table-column label="负责内容">
              <template #default="{ row }">
                <el-input v-model="row.task" placeholder="负责的具体任务" size="small" />
              </template>
            </el-table-column>
            <el-table-column label="操作" width="60" align="center">
              <template #default="{ $index }">
                <el-button v-if="groupMembers.length > 2" type="danger" link size="small" @click="groupMembers.splice($index, 1)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-button size="small" style="margin-top: 8px" @click="groupMembers.push({ name: '', studentId: '', task: '' })">+ 添加成员</el-button>
        </div>
      </el-card>

      <!-- 右侧：难度选择 -->
      <el-card class="option-card right-card">
        <template #header><span>任务难度</span></template>
        <div class="difficulty-grid">
          <div
            v-for="d in difficulties"
            :key="d.value"
            class="difficulty-item"
            :class="[{ selected: difficulty === d.value }, d.value]"
            @click="difficulty = d.value"
          >
            <div class="diff-icon">{{ d.icon }}</div>
            <div class="diff-label">{{ d.label }}</div>
            <div class="diff-hours">预计 {{ d.hours }}</div>
            <ul class="diff-features">
              <li v-for="f in d.features" :key="f">{{ f }}</li>
            </ul>
            <el-tag :type="d.tagType" size="small" class="diff-tag">{{ d.recommend }}</el-tag>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 场馆选择 -->
    <el-card class="venue-option-card">
      <template #header><span>实践场馆（可选）</span></template>
      <div class="venue-option-body">
        <div class="venue-option-desc">可以预先选择实践场馆，AI将根据场馆特点生成更具针对性的方案</div>
        <el-input
          :value="selectedVenueName || '随机生成（AI推荐）'"
          readonly
          class="venue-input"
          @click="showVenueDialog = true"
        >
          <template #suffix>
            <el-icon @click.stop="clearVenue" v-if="selectedVenueId" style="cursor:pointer"><CircleClose /></el-icon>
            <el-icon v-else><Location /></el-icon>
          </template>
        </el-input>
      </div>
    </el-card>

    <!-- 场馆选择弹窗 -->
    <VenueSelect
      v-model="showVenueDialog"
      :current-venue-id="selectedVenueId"
      :knowledge-point-id="kpId"
      @select="handleVenueSelect"
    />

    <div class="footer-bar">
      <el-button type="primary" :disabled="!canNext" @click="goNext">
        下一步：选择实践类型 <el-icon><ArrowRight /></el-icon>
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import VenueSelect from '@/components/VenueSelect.vue'

const route = useRoute()
const router = useRouter()
const kpId = route.query.kpId
const kpName = route.query.kpName

const mode = ref('individual')
const groupMembers = reactive([
  { name: '', studentId: '', task: '' },
  { name: '', studentId: '', task: '' }
])
const difficulty = ref('easy')
const showVenueDialog = ref(false)
const selectedVenueId = ref('')
const selectedVenueName = ref('')

const difficulties = [
  {
    value: 'easy',
    label: '基础',
    icon: 'I',
    hours: '2-3小时',
    tagType: 'success',
    recommend: '推荐个人',
    features: ['步骤清晰简洁', '材料易获取', '无需外出', '适合入门']
  },
  {
    value: 'medium',
    label: '进阶',
    icon: 'II',
    hours: '4-6小时',
    tagType: 'warning',
    recommend: '个人/团队均可',
    features: ['需要一定调研', '可能需要外出', '有一定深度要求', '适合大多数同学']
  },
  {
    value: 'hard',
    label: '挑战',
    icon: 'III',
    hours: '8小时以上',
    tagType: 'danger',
    recommend: '推荐团队',
    features: ['深度调研分析', '多方资源整合', '成果要求高', '适合有经验的同学']
  }
]

const canNext = computed(() => {
  if (mode.value === 'group') {
    return groupMembers.some(m => m.name.trim() && m.task.trim())
  }
  return true
})

const handleVenueSelect = (venue) => {
  if (venue) {
    selectedVenueId.value = venue.id
    selectedVenueName.value = venue.name
  } else {
    selectedVenueId.value = ''
    selectedVenueName.value = ''
  }
}

const clearVenue = () => {
  selectedVenueId.value = ''
  selectedVenueName.value = ''
}

const goNext = () => {
  if (!canNext.value) {
    ElMessage.warning('请至少填写一位团队成员的姓名和负责内容')
    return
  }
  const groupDivisionStr = mode.value === 'group'
    ? groupMembers.filter(m => m.name.trim()).map(m => `${m.name}（${m.studentId}）：${m.task}`).join('；')
    : undefined
  router.push({
    name: 'PracticeTypeSelect',
    query: {
      kpId,
      kpName,
      mode: mode.value,
      groupDivision: groupDivisionStr,
      difficulty: difficulty.value,
      venueId: selectedVenueId.value || undefined,
      venueName: selectedVenueName.value || undefined
    }
  })
}
</script>

<style scoped>
.practice-options {
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

.content-wrapper {
  flex: 1;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  min-height: 0;
  overflow: hidden;
}

.option-card {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.option-card :deep(.el-card__header) {
  flex-shrink: 0;
  font-size: 16px;
  font-weight: 600;
}

.option-card :deep(.el-card__body) {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

/* 完成方式 */
.mode-grid { display: grid; grid-template-columns: 1fr; gap: 12px; }
.mode-item {
  border: 2px solid #eee;
  border-radius: 10px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.2s;
  text-align: center;
}
.mode-item:hover { border-color: #c0392b; transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
.mode-item.selected { border-color: #c0392b; background: #fff5f5; }
.mode-icon { font-size: 32px; margin-bottom: 10px; color: #666; }
.mode-label { font-size: 16px; font-weight: bold; color: #333; margin-bottom: 6px; }
.mode-desc { font-size: 13px; color: #888; }

.group-division { margin-top: 16px; }
.division-label { font-size: 14px; font-weight: 500; color: #333; margin-bottom: 10px; }
.required { color: #f56c6c; }

/* 难度选择 */
.difficulty-grid { display: flex; flex-direction: column; gap: 12px; }
.difficulty-item {
  border: 2px solid #eee;
  border-radius: 10px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.2s;
  display: grid;
  grid-template-columns: auto 1fr auto;
  grid-template-rows: auto auto;
  gap: 8px 12px;
  align-items: center;
}
.difficulty-item:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
.difficulty-item.selected.easy { border-color: #67c23a; background: #f0f9eb; }
.difficulty-item.selected.medium { border-color: #e6a23c; background: #fdf6ec; }
.difficulty-item.selected.hard { border-color: #f56c6c; background: #fef0f0; }

.diff-icon { font-size: 18px; font-weight: 800; grid-row: 1 / 3; color: #999; letter-spacing: 1px; font-family: serif; }
.diff-label { font-size: 16px; font-weight: bold; color: #333; }
.diff-tag { grid-row: 1 / 3; justify-self: end; }
.diff-hours { font-size: 12px; color: #999; grid-column: 2; }
.diff-features {
  list-style: none;
  padding: 0;
  margin: 8px 0 0;
  grid-column: 1 / -1;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.diff-features li {
  font-size: 12px;
  color: #666;
  background: #f5f5f5;
  padding: 4px 8px;
  border-radius: 4px;
}

/* 场馆选择 */
.venue-option-card {
  flex-shrink: 0;
  margin-top: 16px;
}
.venue-option-body {
  display: flex;
  align-items: center;
  gap: 16px;
}
.venue-option-desc {
  font-size: 13px;
  color: #888;
  flex-shrink: 0;
}
.venue-input {
  flex: 1;
  cursor: pointer;
}
.venue-input :deep(.el-input__inner) { cursor: pointer; }

.footer-bar {
  flex-shrink: 0;
  background: #fff;
  padding: 16px 0;
  margin-top: 16px;
  border-top: 1px solid #eee;
  display: flex;
  justify-content: flex-end;
}
</style>
