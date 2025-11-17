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
      <div class="drawer-content">
        <!-- 加载状态 -->
        <div v-if="loading" class="loading-container">
          <el-skeleton :rows="10" animated />
        </div>

        <template v-else>
          <!-- 操作按钮栏（始终显示）-->
          <div class="action-bar">
            <el-button
              :icon="Refresh"
              size="small"
              @click="refreshReport"
              :loading="refreshing"
            >
              刷新
            </el-button>
            <el-button
              :icon="Download"
              size="small"
              type="primary"
              @click="handleGenerate"
              :loading="generating"
            >
              手动生成
            </el-button>
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

          <!-- 报告内容 -->
          <div v-if="currentReport" class="report-container">
          <!-- 报告头部 -->
          <div class="report-header">
            <div class="header-left">
              <h2 class="report-title">{{ formatReportDate(currentReport.report_date) }}</h2>
              <el-tag :type="getStatusTagType(currentReport.generation_status)" size="small">
                {{ getStatusText(currentReport.generation_status) }}
              </el-tag>
            </div>
            <div class="header-right">
              <el-date-picker
                v-model="selectedDate"
                type="date"
                placeholder="选择日期"
                size="small"
                value-format="YYYY-MM-DD"
                @change="handleDateChange"
              />
            </div>
          </div>

          <!-- 统计信息 -->
          <div class="report-stats">
            <div class="stat-card">
              <div class="stat-label">总消息数</div>
              <div class="stat-value">{{ currentReport.total_messages }}</div>
            </div>
            <div class="stat-card">
              <div class="stat-label">AI治理信息</div>
              <div class="stat-value governance">{{ currentReport.governance_count }}</div>
            </div>
            <div class="stat-card">
              <div class="stat-label">AI科研信息</div>
              <div class="stat-value research">{{ currentReport.research_count }}</div>
            </div>
            <div class="stat-card">
              <div class="stat-label">AI产业信息</div>
              <div class="stat-value industry">{{ currentReport.industry_count }}</div>
            </div>
          </div>

          <!-- Markdown内容 -->
          <div class="report-content">
            <MarkdownRenderer :content="currentReport.content" />
          </div>

          <!-- 元信息 -->
          <div class="report-meta">
            <span>生成时间：{{ formatDateTime(currentReport.generated_at) }}</span>
            <span>模型版本：{{ currentReport.model_version }}</span>
          </div>
        </div>

          <!-- 无数据提示 -->
          <el-empty v-else description="暂无AI日报数据" />
        </template>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Document, Refresh, Download } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import MarkdownRenderer from '@/components/common/MarkdownRenderer.vue'
import * as aiReportApi from '@/api/aiReport'
import type { AIDailyReport } from '@/api/aiReport'

const drawerVisible = ref(false)
const loading = ref(false)
const error = ref<string | null>(null)
const currentReport = ref<AIDailyReport | null>(null)
const selectedDate = ref<string>()
const refreshing = ref(false)
const generating = ref(false)

const openDrawer = async () => {
  drawerVisible.value = true
  await loadLatestReport()
}

const handleClose = () => {
  drawerVisible.value = false
}

const loadLatestReport = async () => {
  try {
    loading.value = true
    error.value = null

    currentReport.value = await aiReportApi.getLatestReport()
    selectedDate.value = currentReport.value.report_date

  } catch (err: any) {
    if (err.response?.status === 404) {
      error.value = '暂无可用的AI日报，请尝试手动生成'
    } else {
      error.value = err.message || '加载AI日报失败'
    }
  } finally {
    loading.value = false
  }
}

const handleDateChange = async (date: string) => {
  if (!date) return

  try {
    loading.value = true
    error.value = null

    currentReport.value = await aiReportApi.getReportByDate(date)

  } catch (err: any) {
    if (err.response?.status === 404) {
      error.value = `${date}的AI日报不存在`
    } else {
      error.value = err.message || '加载AI日报失败'
    }
    currentReport.value = null
  } finally {
    loading.value = false
  }
}

const refreshReport = async () => {
  refreshing.value = true
  await loadLatestReport()
  refreshing.value = false
  ElMessage.success('刷新成功')
}

const handleGenerate = async () => {
  try {
    generating.value = true

    const result = await aiReportApi.triggerReportGeneration()
    ElMessage.success(result.message)

    setTimeout(async () => {
      await loadLatestReport()
    }, 3000)

  } catch (err: any) {
    ElMessage.error(err.message || '触发生成失败')
  } finally {
    generating.value = false
  }
}

const formatReportDate = (dateStr: string): string => {
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    weekday: 'long'
  })
}

const formatDateTime = (dateStr: string): string => {
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const getStatusTagType = (status: string) => {
  switch (status) {
    case 'completed':
      return 'success'
    case 'pending':
      return 'warning'
    case 'failed':
      return 'danger'
    default:
      return 'info'
  }
}

const getStatusText = (status: string) => {
  switch (status) {
    case 'completed':
      return '已完成'
    case 'pending':
      return '生成中'
    case 'failed':
      return '失败'
    default:
      return '未知'
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
    padding: 20px;
  }

  .action-bar {
    display: flex;
    gap: 12px;
    padding: 16px;
    border-bottom: 1px solid #e5e7eb;
    background: #f9fafb;
    justify-content: flex-end;
  }

  .error-alert {
    margin: 16px;
  }

  .report-container {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow-y: auto;

    .report-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 20px;
      border-bottom: 1px solid #e0e0e0;
      background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);

      .header-left {
        display: flex;
        align-items: center;
        gap: 12px;

        .report-title {
          margin: 0;
          font-size: 20px;
          font-weight: 600;
          color: #1a1d3a;
        }
      }

      .header-right {
        display: flex;
        align-items: center;
        gap: 10px;
      }
    }

    .report-stats {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 16px;
      padding: 20px;
      background: #f9fafb;
      border-bottom: 1px solid #e0e0e0;

      .stat-card {
        background: white;
        padding: 16px;
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
        text-align: center;

        .stat-label {
          font-size: 12px;
          color: #666;
          margin-bottom: 8px;
        }

        .stat-value {
          font-size: 24px;
          font-weight: 700;
          color: #1a1d3a;

          &.governance {
            color: #10b981;
          }

          &.research {
            color: #f59e0b;
          }

          &.industry {
            color: #ef4444;
          }
        }
      }
    }

    .report-content {
      padding: 20px;
      background: white;
    }

    .report-meta {
      display: flex;
      justify-content: space-between;
      padding: 16px 20px;
      border-top: 1px solid #e0e0e0;
      background: #f9fafb;
      font-size: 12px;
      color: #666;
    }
  }
}
</style>
