<template>
  <div class="ai-report-trigger">
    <!-- 触发按钮 -->
    <el-tooltip content="查看AI日报" placement="left">
      <el-button
        :icon="Document"
        type="primary"
        circle
        size="large"
        @click="openDrawer"
        class="trigger-button"
      >
      </el-button>
    </el-tooltip>

    <!-- 日报抽屉 -->
    <el-drawer
      v-model="drawerVisible"
      title="AI日报"
      direction="rtl"
      size="60%"
      :before-close="handleClose"
    >
      <div class="drawer-content" :style="drawerStyle">
        <!-- 加载状态 -->
        <div v-if="loading" class="loading-container">
          <div class="custom-loader">
            <div class="loader-ring" :style="loaderStyle"></div>
            <div class="loader-ring" :style="loaderStyleSecondary"></div>
            <div class="loader-ring" :style="loaderStyleTertiary"></div>
            <div class="loader-text" :style="{ color: currentTheme.primary }">LOADING</div>
          </div>
        </div>

        <template v-else>
          <!-- 操作按钮栏 -->
          <div class="action-bar" :style="actionBarStyle">
            <el-button
              :icon="Refresh"
              size="small"
              @click="refreshReport"
              :loading="refreshing"
              class="glass-button"
            >
              刷新
            </el-button>
            <el-button
              :icon="Download"
              size="small"
              type="primary"
              @click="handleGenerate"
              :loading="generating"
              class="glass-button"
            >
              手动生成
            </el-button>
            <el-button
              :icon="Picture"
              size="small"
              type="success"
              @click="downloadAsImage"
              :loading="downloading"
              :disabled="!currentReport"
              class="glass-button"
            >
              下载长图
            </el-button>
          </div>

          <!-- 日期选择器（始终显示，方便选择历史日期） -->
          <div class="date-selector-bar" :style="selectorStyle">
            <div class="selector-label">REPORT DATE</div>
            <el-date-picker
              v-model="selectedDate"
              type="date"
              placeholder="选择日期"
              size="default"
              value-format="YYYY-MM-DD"
              @change="handleDateChange"
              class="glass-date-picker"
            />
          </div>

          <!-- 错误提示 -->
          <el-alert
            v-if="error"
            type="warning"
            :title="error"
            show-icon
            :closable="false"
            class="error-alert"
          />

          <!-- 报告类型切换Tab -->
          <div class="report-tabs-container">
            <el-tabs
              v-model="currentReportType"
              @tab-change="handleTabChange"
              class="report-tabs"
            >
              <el-tab-pane
                v-for="type in enabledReportTypes"
                :key="type"
                :label="getReportTypeName(type)"
                :name="type"
              >
                <template #label>
                  <span class="tab-label" :class="`tab-${type}`">
                    <span class="tab-icon">{{ getReportTypeIcon(type) }}</span>
                    <span>{{ getReportTypeName(type) }}</span>
                  </span>
                </template>
              </el-tab-pane>
            </el-tabs>
          </div>

          <!-- 报告内容 - 动态组件 -->
          <div v-if="currentReport" class="report-container">
            <component
              :is="currentReportComponent"
              :config="currentReportConfig"
              :report="currentReport"
              ref="reportViewRef"
            />
          </div>

          <!-- 无数据提示 -->
          <el-empty v-else description="暂无AI日报数据" />
        </template>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { Document, Refresh, Download, Picture } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import * as aiReportApi from '@/api/aiReport'
import type { AIDailyReport } from '@/api/aiReport'
import { domToPng } from 'modern-screenshot'

// 导入报告类型注册系统
import {
  getReportRegistry,
  getReportConfig,
  getReportModule,
  getEnabledReportTypes,
  getReportTypeName as getTypeName,
  getReportTypeIcon as getTypeIcon,
  type ReportType
} from '@/components/report-types'

// 状态管理
const drawerVisible = ref(false)
const loading = ref(false)
const error = ref<string | null>(null)
const currentReport = ref<AIDailyReport | null>(null)
const selectedDate = ref<string>(new Date().toISOString().split('T')[0])
const refreshing = ref(false)
const generating = ref(false)
const downloading = ref(false)
const reportViewRef = ref<any>(null)
const currentReportType = ref<ReportType>('comprehensive')

// 获取已启用的报告类型列表
const enabledReportTypes = computed(() => getEnabledReportTypes())

// 当前报告类型的配置
const currentReportConfig = computed(() => {
  return getReportConfig(currentReportType.value)
})

// 当前报告类型的组件
const currentReportComponent = computed(() => {
  return getReportModule(currentReportType.value).component
})

// 当前主题
const currentTheme = computed(() => currentReportConfig.value.theme)

// Drawer 样式
const drawerStyle = computed(() => ({
  background: currentTheme.value.bgGradient
}))

// 操作栏样式
const actionBarStyle = computed(() => ({
  borderBottomColor: currentTheme.value.borderColor
}))

// 选择器样式
const selectorStyle = computed(() => ({
  borderBottomColor: currentTheme.value.borderColor
}))

// 加载器样式
const loaderStyle = computed(() => ({
  borderTopColor: currentTheme.value.primary
}))

const loaderStyleSecondary = computed(() => ({
  borderTopColor: currentTheme.value.secondary
}))

const loaderStyleTertiary = computed(() => ({
  borderTopColor: currentTheme.value.accent
}))

// 封装的工具函数
const getReportTypeName = (type: ReportType) => getTypeName(type)
const getReportTypeIcon = (type: ReportType) => getTypeIcon(type)

// 打开抽屉
const openDrawer = async () => {
  drawerVisible.value = true
  selectedDate.value = new Date().toISOString().split('T')[0]
  await handleDateChange(selectedDate.value)
}

// 关闭抽屉
const handleClose = () => {
  drawerVisible.value = false
}

// 加载最新报告
const loadLatestReport = async () => {
  try {
    loading.value = true
    error.value = null

    currentReport.value = await aiReportApi.getLatestReport(currentReportType.value)
    selectedDate.value = currentReport.value.report_date

  } catch (err: any) {
    if (err.response?.status === 404) {
      const reportTypeName = getReportTypeName(currentReportType.value)
      error.value = `暂无可用的${reportTypeName}，请点击"手动生成"按钮生成今天的报告`
    } else {
      error.value = err.message || '加载AI日报失败'
    }
  } finally {
    loading.value = false
  }
}

// 处理日期变化
const handleDateChange = async (date: string) => {
  if (!date) return

  try {
    loading.value = true
    error.value = null

    currentReport.value = await aiReportApi.getReportByDate(date, currentReportType.value)

  } catch (err: any) {
    if (err.response?.status === 404) {
      const reportTypeName = getReportTypeName(currentReportType.value)
      error.value = `${date} 暂无${reportTypeName}，请点击"手动生成"按钮生成报告`
    } else {
      error.value = err.message || '加载AI日报失败'
    }
    currentReport.value = null
  } finally {
    loading.value = false
  }
}

// 刷新报告
const refreshReport = async () => {
  refreshing.value = true
  await handleDateChange(selectedDate.value)
  refreshing.value = false
  ElMessage.success('刷新成功')
}

// 手动生成报告
const handleGenerate = async () => {
  try {
    generating.value = true

    const result = await aiReportApi.triggerReportGeneration(currentReportType.value, selectedDate.value)
    ElMessage.success(result.message)

    setTimeout(async () => {
      await handleDateChange(selectedDate.value)
    }, 3000)

  } catch (err: any) {
    ElMessage.error(err.message || '触发生成失败')
  } finally {
    generating.value = false
  }
}

// Tab切换
const handleTabChange = async (tabName: string) => {
  currentReportType.value = tabName as ReportType
  if (selectedDate.value) {
    await handleDateChange(selectedDate.value)
  } else {
    selectedDate.value = new Date().toISOString().split('T')[0]
  await handleDateChange(selectedDate.value)
  }
}

// 格式化报告日期
const formatReportDate = (dateStr: string): string => {
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    weekday: 'long'
  })
}

// 下载长图
const downloadAsImage = async () => {
  if (!reportViewRef.value?.exportRef || !currentReport.value) {
    ElMessage.warning('没有可下载的内容')
    return
  }

  try {
    downloading.value = true
    ElMessage.info('正在生成长图，请稍候...')

    const element = reportViewRef.value.exportRef
    const container = element.parentElement

    if (container) {
      container.style.overflow = 'visible'
      container.style.height = 'auto'
    }

    element.style.overflow = 'visible'
    element.style.height = 'auto'
    element.classList.add('export-mode')

    await new Promise(resolve => setTimeout(resolve, 300))

    // 获取当前主题的背景色（从渐变中提取第一个颜色）
    const bgMatch = currentTheme.value.bgGradient.match(/#[0-9a-fA-F]{6}/)
    const backgroundColor = bgMatch ? bgMatch[0] : '#0a0e27'

    const dataUrl = await domToPng(element, {
      quality: 1,
      scale: 2,
      backgroundColor,
      width: element.scrollWidth,
      height: element.scrollHeight,
      style: {
        margin: '0',
        padding: '0',
        overflow: 'visible',
        height: 'auto'
      }
    })

    element.classList.remove('export-mode')
    element.style.overflow = ''
    element.style.height = ''
    if (container) {
      container.style.overflow = ''
      container.style.height = ''
    }

    const link = document.createElement('a')
    const reportTypeName = getReportTypeName(currentReportType.value)
    const fileName = `${reportTypeName}_${currentReport.value?.report_date || new Date().toISOString().split('T')[0]}.png`

    link.href = dataUrl
    link.download = fileName
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)

    ElMessage.success('长图下载成功！')

  } catch (err: any) {
    console.error('下载长图失败:', err)
    ElMessage.error(err.message || '下载长图失败')
    if (reportViewRef.value?.exportRef) {
      const element = reportViewRef.value.exportRef
      element.classList.remove('export-mode')
      element.style.overflow = ''
      element.style.height = ''
      const container = element.parentElement
      if (container) {
        container.style.overflow = ''
        container.style.height = ''
      }
    }
  } finally {
    downloading.value = false
  }
}
</script>

<style scoped lang="scss">
.ai-report-trigger {
  .trigger-button {
    position: fixed;
    top: 80px;
    right: 20px;
    z-index: 1000;
    width: 56px;
    height: 56px;
    font-size: 24px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border: none;
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
    transition: all 0.3s;

    &:hover {
      transform: scale(1.05);
      box-shadow: 0 6px 16px rgba(102, 126, 234, 0.6);
    }
  }
}

.drawer-content {
  height: 100%;
  display: flex;
  flex-direction: column;

  .loading-container {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;

    .custom-loader {
      position: relative;
      width: 120px;
      height: 120px;
      display: flex;
      align-items: center;
      justify-content: center;

      .loader-ring {
        position: absolute;
        width: 100%;
        height: 100%;
        border: 2px solid transparent;
        border-radius: 50%;
        animation: spin 2s cubic-bezier(0.68, -0.55, 0.27, 1.55) infinite;

        &:nth-child(2) {
          width: 80%;
          height: 80%;
          animation-duration: 1.5s;
          animation-direction: reverse;
        }

        &:nth-child(3) {
          width: 60%;
          height: 60%;
          animation-duration: 1s;
        }
      }

      .loader-text {
        font-size: 14px;
        font-weight: 700;
        letter-spacing: 4px;
        animation: pulse-text 1.5s ease-in-out infinite;
      }
    }
  }

  .action-bar {
    display: flex;
    gap: 12px;
    padding: 16px 20px;
    background: rgba(10, 14, 39, 0.8);
    backdrop-filter: blur(10px);
    border-bottom: 1px solid;
    justify-content: flex-end;

    :deep(.glass-button) {
      background: rgba(255, 255, 255, 0.05);
      backdrop-filter: blur(10px);
      border: 1px solid rgba(255, 255, 255, 0.1);
      color: #ffffff;
      transition: all 0.3s;

      &:hover {
        background: rgba(0, 212, 255, 0.1);
        border-color: rgba(0, 212, 255, 0.3);
        box-shadow: 0 0 15px rgba(0, 212, 255, 0.3);
        transform: translateY(-2px);
      }
    }
  }

  .error-alert {
    margin: 16px 20px;
    background: rgba(239, 68, 68, 0.1);
    border: 1px solid rgba(239, 68, 68, 0.3);
    backdrop-filter: blur(10px);

    :deep(.el-alert__title) {
      color: #fca5a5;
    }
  }

  .report-tabs-container {
    padding: 20px 20px 0;
    background: rgba(10, 14, 39, 0.6);
    backdrop-filter: blur(10px);

    :deep(.report-tabs) {
      .el-tabs__header {
        margin: 0;
        border-bottom: 1px solid rgba(0, 212, 255, 0.2);
      }

      .el-tabs__nav-wrap::after {
        display: none;
      }

      .el-tabs__nav {
        display: flex;
        border: none;
      }

      .el-tabs__item {
        padding: 16px 32px;
        color: rgba(255, 255, 255, 0.6);
        border: none;
        border-bottom: 3px solid transparent;
        transition: all 0.3s;
        font-weight: 600;
        font-size: 15px;
        background: transparent;

        &:hover {
          color: #00d4ff;
          background: rgba(0, 212, 255, 0.05);
        }

        &.is-active {
          color: #ffffff;
          background: rgba(0, 212, 255, 0.1);
          border-bottom-color: #00d4ff;
        }

        // 综合日报
        &:has(.tab-comprehensive).is-active {
          border-bottom-color: #00d4ff;
          background: rgba(0, 212, 255, 0.1);
        }

        // 治理日报
        &:has(.tab-governance).is-active {
          border-bottom-color: #10b981;
          background: rgba(16, 185, 129, 0.1);

          .tab-label {
            color: #10b981;
          }
        }

        // 科研日报
        &:has(.tab-research).is-active {
          border-bottom-color: #3b82f6;
          background: rgba(59, 130, 246, 0.1);

          .tab-label {
            color: #3b82f6;
          }
        }

        // 产业日报
        &:has(.tab-industry).is-active {
          border-bottom-color: #f59e0b;
          background: rgba(245, 158, 11, 0.1);

          .tab-label {
            color: #f59e0b;
          }
        }

        // 中国AI日报（红金中国风）
        &:has(.tab-china_ai).is-active {
          border-bottom-color: #dc2626;
          background: linear-gradient(135deg, rgba(220, 38, 38, 0.15) 0%, rgba(245, 158, 11, 0.1) 100%);

          .tab-label {
            color: #fbbf24;
            text-shadow: 0 0 8px rgba(220, 38, 38, 0.5);
          }
        }

        // 上海周报（蓝色都市风）
        &:has(.tab-shanghai_weekly).is-active {
          border-bottom-color: #0ea5e9;
          background: linear-gradient(135deg, rgba(14, 165, 233, 0.15) 0%, rgba(56, 189, 248, 0.1) 100%);

          .tab-label {
            color: #7dd3fc;
            text-shadow: 0 0 8px rgba(14, 165, 233, 0.5);
          }
        }
      }

      .el-tabs__active-bar {
        display: none;
      }

      .el-tabs__content {
        display: none;
      }
    }

    .tab-label {
      display: flex;
      align-items: center;
      gap: 8px;
      transition: all 0.3s;

      .tab-icon {
        font-size: 18px;
        filter: grayscale(50%);
        transition: all 0.3s;
      }
    }

    .el-tabs__item.is-active .tab-label .tab-icon {
      filter: grayscale(0%);
      transform: scale(1.15);
    }
  }

  .report-container {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow-y: auto;
    padding: 0;

    &::-webkit-scrollbar {
      width: 8px;
    }

    &::-webkit-scrollbar-track {
      background: rgba(10, 14, 39, 0.5);
    }

    &::-webkit-scrollbar-thumb {
      background: rgba(0, 212, 255, 0.3);
      border-radius: 4px;

      &:hover {
        background: rgba(0, 212, 255, 0.5);
      }
    }
  }

  .date-selector-bar {
    padding: 12px 20px;
    display: flex;
    align-items: center;
    gap: 16px;
    background: rgba(255, 255, 255, 0.03);
    border-bottom: 1px solid;

    .selector-label {
      font-size: 11px;
      font-weight: 600;
      letter-spacing: 1.5px;
      color: rgba(255, 255, 255, 0.6);
    }

    :deep(.glass-date-picker) {
      .el-input__wrapper {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(0, 212, 255, 0.2);
        box-shadow: none;

        &:hover {
          border-color: rgba(0, 212, 255, 0.4);
        }

        .el-input__inner {
          color: #ffffff;
        }
      }
    }
  }
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@keyframes pulse-text {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}
</style>
