<template>
  <div class="monitor-view">
    <!-- 顶部状态栏 -->
    <div class="monitor-header">
      <div class="header-left">
        <h2>系统监控</h2>
        <el-tag :type="overallStatusType" size="large" effect="dark">
          {{ overallStatusText }}
        </el-tag>
        <span v-if="systemData?.uptime" class="uptime">
          运行时长: {{ systemData.uptime }}
        </span>
      </div>
      <div class="header-right">
        <span class="last-update">
          上次更新: {{ lastUpdateTime }}
        </span>
        <el-button
          type="primary"
          :icon="Refresh"
          :loading="loading"
          @click="fetchSystemStatus"
        >
          刷新
        </el-button>
        <el-switch
          v-model="autoRefresh"
          active-text="自动刷新"
          inactive-text=""
          @change="handleAutoRefreshChange"
        />
      </div>
    </div>

    <!-- 组件状态卡片 -->
    <div class="component-cards">
      <el-row :gutter="16">
        <!-- Redis状态 -->
        <el-col :xs="24" :sm="12" :md="8" :lg="4">
          <el-card class="component-card" :class="getStatusClass(systemData?.components?.redis?.status)">
            <div class="card-icon">
              <el-icon :size="32"><Connection /></el-icon>
            </div>
            <div class="card-content">
              <div class="card-title">Redis</div>
              <div class="card-status">
                <el-tag :type="getTagType(systemData?.components?.redis?.status)" size="small">
                  {{ getStatusText(systemData?.components?.redis?.status) }}
                </el-tag>
              </div>
              <div class="card-detail">
                Broker: {{ systemData?.components?.redis?.broker_connected ? 'OK' : 'X' }}
                | Backend: {{ systemData?.components?.redis?.backend_connected ? 'OK' : 'X' }}
              </div>
            </div>
          </el-card>
        </el-col>

        <!-- Worker状态 -->
        <el-col :xs="24" :sm="12" :md="8" :lg="4">
          <el-card class="component-card" :class="getStatusClass(systemData?.components?.celery_worker?.status)">
            <div class="card-icon">
              <el-icon :size="32"><Cpu /></el-icon>
            </div>
            <div class="card-content">
              <div class="card-title">Celery Worker</div>
              <div class="card-status">
                <el-tag :type="getTagType(systemData?.components?.celery_worker?.status)" size="small">
                  {{ getWorkerStatusText(systemData?.components?.celery_worker) }}
                </el-tag>
              </div>
              <div class="card-detail">
                {{ systemData?.components?.celery_worker?.count || 0 }} 个Worker
                | {{ systemData?.components?.celery_worker?.active_tasks || 0 }} 任务运行中
              </div>
            </div>
          </el-card>
        </el-col>

        <!-- Beat状态 -->
        <el-col :xs="24" :sm="12" :md="8" :lg="4">
          <el-card class="component-card" :class="getStatusClass(systemData?.components?.celery_beat?.status)">
            <div class="card-icon">
              <el-icon :size="32"><Timer /></el-icon>
            </div>
            <div class="card-content">
              <div class="card-title">Celery Beat</div>
              <div class="card-status">
                <el-tag :type="getTagType(systemData?.components?.celery_beat?.status)" size="small">
                  {{ getStatusText(systemData?.components?.celery_beat?.status) }}
                </el-tag>
              </div>
              <div class="card-detail">
                {{ systemData?.components?.celery_beat?.registered_tasks || 0 }} 个定时任务
              </div>
            </div>
          </el-card>
        </el-col>

        <!-- 数据库状态 -->
        <el-col :xs="24" :sm="12" :md="8" :lg="4">
          <el-card class="component-card" :class="getStatusClass(systemData?.components?.database?.status)">
            <div class="card-icon">
              <el-icon :size="32"><Coin /></el-icon>
            </div>
            <div class="card-content">
              <div class="card-title">MySQL</div>
              <div class="card-status">
                <el-tag :type="getTagType(systemData?.components?.database?.status)" size="small">
                  {{ getStatusText(systemData?.components?.database?.status) }}
                </el-tag>
              </div>
              <div class="card-detail">
                响应: {{ systemData?.components?.database?.response_ms || 0 }}ms
              </div>
            </div>
          </el-card>
        </el-col>

        <!-- ChromaDB状态 -->
        <el-col :xs="24" :sm="12" :md="8" :lg="4">
          <el-card class="component-card" :class="getStatusClass(systemData?.components?.chromadb?.status)">
            <div class="card-icon">
              <el-icon :size="32"><DataLine /></el-icon>
            </div>
            <div class="card-content">
              <div class="card-title">ChromaDB</div>
              <div class="card-status">
                <el-tag :type="getTagType(systemData?.components?.chromadb?.status)" size="small">
                  {{ getStatusText(systemData?.components?.chromadb?.status) }}
                </el-tag>
              </div>
              <div class="card-detail">
                {{ systemData?.components?.chromadb?.collections || 0 }} 个集合
                | {{ systemData?.components?.chromadb?.mode || 'unknown' }}模式
              </div>
            </div>
          </el-card>
        </el-col>

        <!-- 采集器统计概览 -->
        <el-col :xs="24" :sm="12" :md="8" :lg="4">
          <el-card class="component-card summary-card">
            <div class="card-icon">
              <el-icon :size="32"><TrendCharts /></el-icon>
            </div>
            <div class="card-content">
              <div class="card-title">采集器统计</div>
              <div class="card-status">
                <el-tag type="success" size="small">
                  {{ systemData?.summary?.healthy_collectors || 0 }}/{{ systemData?.summary?.total_collectors || 0 }} 健康
                </el-tag>
              </div>
              <div class="card-detail">
                成功: {{ systemData?.summary?.total_success || 0 }}
                | 失败: {{ systemData?.summary?.total_failures || 0 }}
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <!-- 采集器列表 -->
    <div class="collectors-section">
      <div class="section-header">
        <h3>采集器状态</h3>
        <!-- <span class="section-hint">点击"运行"可手动触发采集任务</span> -->
      </div>

      <el-table
        :data="systemData?.collectors || []"
        stripe
        style="width: 100%"
        :row-class-name="tableRowClassName"
      >
        <el-table-column prop="display_name" label="采集器名称" min-width="150">
          <template #default="{ row }">
            <div class="collector-name">
              <span>{{ row.display_name }}</span>
              <el-tag size="small" type="info">{{ row.category }}</el-tag>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="status" label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="getCollectorTagType(row.status)" size="small">
              {{ getCollectorStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="total_runs" label="运行次数" width="100" align="center">
          <template #default="{ row }">
            <span class="stat-number">{{ row.total_runs }}</span>
          </template>
        </el-table-column>

        <el-table-column label="成功/失败" width="120" align="center">
          <template #default="{ row }">
            <span class="success-count">{{ row.success_count }}</span>
            <span class="divider">/</span>
            <span class="failure-count">{{ row.failure_count }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="last_run_ago" label="最近运行" width="120" align="center">
          <template #default="{ row }">
            <span :class="{ 'text-warning': isRunLongAgo(row.last_run_at) }">
              {{ row.last_run_ago }}
            </span>
          </template>
        </el-table-column>

        <el-table-column prop="next_run_in" label="下次运行" width="120" align="center">
          <template #default="{ row }">
            <span class="next-run">{{ row.next_run_in || '-' }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="interval" label="间隔" width="80" align="center">
          <template #default="{ row }">
            {{ formatInterval(row.interval) }}
          </template>
        </el-table-column>

        <!-- 安全考虑：手动运行采集器仅在开发环境使用
        <el-table-column label="操作" width="100" align="center" fixed="right">
          <template #default="{ row }">
            <el-button
              type="primary"
              size="small"
              text
              :loading="triggeringCollector === row.name"
              @click="handleTriggerCollector(row.name)"
            >
              运行
            </el-button>
          </template>
        </el-table-column>
        -->
      </el-table>
    </div>

    <!-- 队列状态 -->
    <div class="queues-section">
      <div class="section-header">
        <h3>任务队列</h3>
      </div>

      <!-- 队列概览（始终显示任务详情） -->
      <div class="queue-cards">
        <div
          v-for="(info, queueName) in queueData?.queues"
          :key="queueName"
          class="queue-card"
          :class="{ 'has-tasks': info.pending_tasks > 0 }"
        >
          <div class="queue-header">
            <span class="queue-name">{{ formatQueueName(String(queueName)) }}</span>
            <el-badge
              :value="info.pending_tasks"
              :type="info.pending_tasks > 10 ? 'warning' : info.pending_tasks > 0 ? 'primary' : 'info'"
              class="queue-badge"
            />
            <!-- 安全考虑：清空队列按钮仅在开发环境使用
            <el-popconfirm
              v-if="info.pending_tasks > 0"
              :title="`确定清空 ${formatQueueName(String(queueName))} 中的 ${info.pending_tasks} 个任务？`"
              confirm-button-text="清空"
              cancel-button-text="取消"
              @confirm="handleClearQueue(String(queueName))"
            >
              <template #reference>
                <el-button
                  type="danger"
                  size="small"
                  text
                  :loading="clearingQueue === queueName"
                  class="clear-btn"
                >
                  <el-icon><Delete /></el-icon>
                </el-button>
              </template>
            </el-popconfirm>
            -->
          </div>

          <!-- 任务列表 -->
          <div class="queue-tasks" v-if="info.tasks?.length">
            <div
              v-for="task in info.tasks"
              :key="task.id"
              class="pending-task-item"
            >
              <el-icon class="task-icon"><Clock /></el-icon>
              <span class="task-display-name">{{ getTaskDisplayName(task) }}</span>
              <span class="task-args" v-if="task.args?.length">({{ task.args.join(', ') }})</span>
              <el-tag size="small" type="info" class="task-priority">P{{ task.priority }}</el-tag>
              <span v-if="task.time_limit" class="task-limit">{{ formatTimeLimit(task.time_limit) }}</span>
            </div>
            <div v-if="info.pending_tasks > info.tasks.length" class="more-hint">
              还有 {{ info.pending_tasks - info.tasks.length }} 个任务未显示
            </div>
          </div>
          <div v-else-if="info.pending_tasks === 0" class="queue-empty">
            暂无等待任务
          </div>
        </div>
      </div>

      <!-- 执行中的任务 -->
      <div v-if="queueData?.active_tasks?.length" class="task-list">
        <div class="task-list-header">
          <el-icon class="spinning"><Loading /></el-icon>
          <span>执行中 ({{ queueData.active_tasks.length }})</span>
        </div>
        <div
          v-for="task in queueData.active_tasks"
          :key="task.id"
          class="task-item running"
        >
          <el-icon class="task-icon spinning"><Loading /></el-icon>
          <span class="task-name">{{ task.name }}</span>
          <span class="task-args">{{ task.args.join(', ') }}</span>
          <span class="task-worker">@ {{ task.worker }}</span>
        </div>
      </div>

      <!-- 最近完成的任务 -->
      <div v-if="queueData?.recent_tasks?.length" class="task-list">
        <div class="task-list-header">
          <el-icon><Finished /></el-icon>
          <span>最近完成 ({{ queueData.recent_tasks.length }})</span>
        </div>
        <div
          v-for="(task, index) in queueData.recent_tasks"
          :key="index"
          class="task-item"
          :class="task.status"
        >
          <el-icon class="task-icon" :class="task.status">
            <SuccessFilled v-if="task.success" />
            <CircleCloseFilled v-else />
          </el-icon>
          <span class="task-name">{{ task.source }}</span>
          <span class="task-time">{{ formatTime(task.completed_at) }}</span>
          <el-tooltip v-if="task.error" :content="task.error" placement="top">
            <el-icon class="error-icon"><Warning /></el-icon>
          </el-tooltip>
        </div>
      </div>

      <!-- 空状态 -->
      <div
        v-if="!queueData?.active_tasks?.length && !queueData?.recent_tasks?.length"
        class="empty-state"
      >
        <el-icon :size="40"><Clock /></el-icon>
        <p>暂无任务记录</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Refresh,
  Connection,
  Cpu,
  Timer,
  Coin,
  DataLine,
  TrendCharts,
  Loading,
  Finished,
  SuccessFilled,
  CircleCloseFilled,
  Warning,
  Clock,
  Delete
} from '@element-plus/icons-vue'
import { monitorApi, type SystemMonitorResponse, type QueueStatus, type WorkerStatus, type PendingTask } from '@/api/monitor'

const loading = ref(false)
const autoRefresh = ref(true)
const systemData = ref<SystemMonitorResponse | null>(null)
const queueData = ref<QueueStatus | null>(null)
const lastUpdateTime = ref('')
const triggeringCollector = ref<string | null>(null)
const clearingQueue = ref<string | null>(null)

let refreshTimer: ReturnType<typeof setInterval> | null = null

const overallStatusType = computed(() => {
  const status = systemData.value?.overall_status
  if (status === 'healthy') return 'success'
  if (status === 'degraded') return 'warning'
  return 'danger'
})

const overallStatusText = computed(() => {
  const status = systemData.value?.overall_status
  if (status === 'healthy') return '系统正常'
  if (status === 'degraded') return '部分异常'
  return '系统异常'
})

function getStatusClass(status?: string): string {
  if (status === 'healthy') return 'status-healthy'
  if (status === 'degraded' || status === 'unknown') return 'status-warning'
  return 'status-error'
}

function getTagType(status?: string): 'success' | 'warning' | 'danger' | 'info' {
  if (status === 'healthy') return 'success'
  if (status === 'degraded' || status === 'unknown') return 'warning'
  if (status === 'unhealthy' || status === 'error') return 'danger'
  return 'info'
}

function getStatusText(status?: string): string {
  if (status === 'healthy') return '正常'
  if (status === 'degraded') return '降级'
  if (status === 'unhealthy') return '异常'
  if (status === 'error') return '错误'
  if (status === 'unknown') return '未知'
  return '未知'
}

function getWorkerStatusText(worker?: WorkerStatus): string {
  if (!worker) return '未知'
  if (worker.status === 'healthy') {
    if (worker.busy) return '执行中'  // Worker正忙于任务
    return '空闲'
  }
  if (worker.status === 'degraded') return '降级'
  if (worker.status === 'unhealthy') return '异常'
  if (worker.status === 'error') return '错误'
  return '未知'
}

function getCollectorTagType(status: string): 'success' | 'warning' | 'danger' {
  if (status === 'healthy') return 'success'
  if (status === 'degraded') return 'warning'
  return 'danger'
}

function getCollectorStatusText(status: string): string {
  if (status === 'healthy') return '正常'
  if (status === 'degraded') return '降级'
  return '异常'
}

function tableRowClassName({ row }: { row: { status: string } }) {
  if (row.status === 'unhealthy') return 'row-error'
  if (row.status === 'degraded') return 'row-warning'
  return ''
}

function formatInterval(seconds: number): string {
  if (seconds < 60) return `${seconds}秒`
  if (seconds < 3600) return `${Math.round(seconds / 60)}分钟`
  return `${Math.round(seconds / 3600)}小时`
}

function formatQueueName(name: string): string {
  const nameMap: Record<string, string> = {
    'default': '默认队列',
    'collector': '采集队列',
    'report': '日报队列'
  }
  return nameMap[name] || name
}

function getTaskDisplayName(task: PendingTask): string {
  const nameMap: Record<string, string> = {
    'run_collector': '采集任务',
    'generate_daily_report': '日报生成',
    'trigger_all_collectors': '启动触发'
  }
  return nameMap[task.name] || task.name
}

function formatTimeLimit(seconds: number): string {
  if (seconds < 60) return `${seconds}s`
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`
  return `${Math.round(seconds / 3600)}h`
}

function isRunLongAgo(lastRunAt: string | null): boolean {
  if (!lastRunAt) return true
  const lastRun = new Date(lastRunAt)
  const now = new Date()
  const diffHours = (now.getTime() - lastRun.getTime()) / (1000 * 60 * 60)
  return diffHours > 1
}

function formatTime(isoString: string): string {
  if (!isoString) return '-'
  const date = new Date(isoString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffSec = Math.floor(diffMs / 1000)
  const diffMin = Math.floor(diffSec / 60)

  if (diffSec < 60) return `${diffSec}秒前`
  if (diffMin < 60) return `${diffMin}分钟前`
  return date.toLocaleTimeString()
}

async function fetchSystemStatus() {
  loading.value = true
  try {
    const [sysData, queues] = await Promise.all([
      monitorApi.getSystemStatus(),
      monitorApi.getQueueStatus()
    ])
    systemData.value = sysData
    queueData.value = queues
    lastUpdateTime.value = new Date().toLocaleTimeString()
  } catch (error) {
    console.error('获取系统状态失败:', error)
  } finally {
    loading.value = false
  }
}

async function handleTriggerCollector(sourceName: string) {
  triggeringCollector.value = sourceName
  try {
    const result = await monitorApi.triggerCollector(sourceName)
    if (result.success) {
      ElMessage.success(`采集任务已提交: ${sourceName}`)
    }
  } catch (error) {
    ElMessage.error(`触发采集失败: ${sourceName}`)
  } finally {
    triggeringCollector.value = null
  }
}

async function handleClearQueue(queueName: string) {
  clearingQueue.value = queueName
  try {
    const result = await monitorApi.clearQueue(queueName)
    ElMessage.success(`已清空 ${result.cleared_tasks} 个任务`)
    await fetchSystemStatus()
  } catch (error) {
    ElMessage.error(`清空队列失败: ${queueName}`)
  } finally {
    clearingQueue.value = null
  }
}

function handleAutoRefreshChange(value: boolean) {
  if (value) {
    startAutoRefresh()
  } else {
    stopAutoRefresh()
  }
}

function startAutoRefresh() {
  if (refreshTimer) return
  refreshTimer = setInterval(fetchSystemStatus, 15000) // 15秒刷新一次
}

function stopAutoRefresh() {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
}

onMounted(() => {
  fetchSystemStatus()
  if (autoRefresh.value) {
    startAutoRefresh()
  }
})

onUnmounted(() => {
  stopAutoRefresh()
})
</script>

<style scoped lang="scss">
.monitor-view {
  padding: 20px;
  min-height: 100vh;
  background: var(--bg-secondary, #0a0a0f);
  color: var(--text-primary, #e0e0e0);
}

.monitor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding: 16px 20px;
  background: var(--bg-card, rgba(255, 255, 255, 0.05));
  border-radius: 8px;
  border: 1px solid var(--border-color, rgba(255, 255, 255, 0.1));

  .header-left {
    display: flex;
    align-items: center;
    gap: 16px;

    h2 {
      margin: 0;
      font-size: 20px;
      font-weight: 600;
    }

    .uptime {
      color: var(--text-secondary, #909399);
      font-size: 14px;
    }
  }

  .header-right {
    display: flex;
    align-items: center;
    gap: 16px;

    .last-update {
      color: var(--text-secondary, #909399);
      font-size: 13px;
    }
  }
}

.component-cards {
  margin-bottom: 24px;

  .component-card {
    height: 140px;
    margin-bottom: 16px;
    background: var(--bg-card, rgba(255, 255, 255, 0.05));
    border: 1px solid var(--border-color, rgba(255, 255, 255, 0.1));
    border-radius: 8px;
    transition: all 0.3s ease;
    display: flex;
    align-items: center;
    padding: 0 16px;

    &:hover {
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }

    &.status-healthy {
      border-left: 4px solid #67c23a;
    }

    &.status-warning {
      border-left: 4px solid #e6a23c;
    }

    &.status-error {
      border-left: 4px solid #f56c6c;
    }

    &.summary-card {
      border-left: 4px solid #409eff;
    }

    .card-icon {
      margin-right: 16px;
      color: var(--text-secondary, #909399);
    }

    .card-content {
      flex: 1;

      .card-title {
        font-size: 14px;
        font-weight: 600;
        margin-bottom: 8px;
        color: var(--text-primary, #e0e0e0);
      }

      .card-status {
        margin-bottom: 8px;
      }

      .card-detail {
        font-size: 12px;
        color: var(--text-secondary, #909399);
      }
    }
  }
}

.collectors-section {
  background: var(--bg-card, rgba(255, 255, 255, 0.05));
  border-radius: 8px;
  border: 1px solid var(--border-color, rgba(255, 255, 255, 0.1));
  padding: 20px;
  margin-bottom: 20px;

  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;

    h3 {
      margin: 0;
      font-size: 16px;
      font-weight: 600;
    }

    .section-hint {
      font-size: 12px;
      color: var(--text-secondary, #909399);
    }
  }

  :deep(.el-table) {
    --el-table-bg-color: transparent;
    --el-table-tr-bg-color: transparent;
    --el-table-header-bg-color: rgba(255, 255, 255, 0.02);
    --el-table-row-hover-bg-color: rgba(255, 255, 255, 0.05);
    --el-table-border-color: rgba(255, 255, 255, 0.08);

    .el-table__header th {
      color: var(--text-secondary, #909399);
      font-weight: 500;
    }

    .el-table__body td {
      color: var(--text-primary, #e0e0e0);
    }

    .row-error {
      background-color: rgba(245, 108, 108, 0.1) !important;
    }

    .row-warning {
      background-color: rgba(230, 162, 60, 0.1) !important;
    }
  }

  .collector-name {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .stat-number {
    font-weight: 600;
    color: var(--text-primary, #e0e0e0);
  }

  .success-count {
    color: #67c23a;
    font-weight: 600;
  }

  .failure-count {
    color: #f56c6c;
    font-weight: 600;
  }

  .divider {
    color: var(--text-secondary, #909399);
    margin: 0 4px;
  }

  .text-warning {
    color: #e6a23c;
  }

  .next-run {
    color: #409eff;
  }
}

.queues-section {
  background: var(--bg-card, rgba(255, 255, 255, 0.05));
  border-radius: 8px;
  border: 1px solid var(--border-color, rgba(255, 255, 255, 0.1));
  padding: 20px;

  .section-header {
    margin-bottom: 16px;

    h3 {
      margin: 0;
      font-size: 16px;
      font-weight: 600;
    }
  }

  .queue-cards {
    display: flex;
    gap: 16px;
    flex-wrap: wrap;
    margin-bottom: 20px;
    padding-bottom: 16px;
    border-bottom: 1px solid var(--border-color, rgba(255, 255, 255, 0.1));

    .queue-card {
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid var(--border-color, rgba(255, 255, 255, 0.1));
      border-radius: 8px;
      padding: 12px 16px;
      min-width: 200px;
      flex: 1;
      max-width: 400px;

      &.has-tasks {
        border-color: rgba(64, 158, 255, 0.3);
      }

      .queue-header {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 8px;

        .queue-name {
          font-size: 14px;
          font-weight: 500;
          color: var(--text-primary, #e0e0e0);
        }

        .clear-btn {
          margin-left: auto;
          padding: 4px 8px;
          opacity: 0.6;
          transition: opacity 0.2s;

          &:hover {
            opacity: 1;
          }
        }
      }

      .queue-tasks {
        .pending-task-item {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 6px 0;
          font-size: 12px;
          border-bottom: 1px dashed rgba(255, 255, 255, 0.05);

          &:last-child {
            border-bottom: none;
          }

          .task-icon {
            color: var(--text-secondary, #909399);
            flex-shrink: 0;
            font-size: 14px;
          }

          .task-display-name {
            font-weight: 500;
            color: var(--text-primary, #e0e0e0);
          }

          .task-args {
            color: #409eff;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 11px;
            max-width: 120px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
          }

          .task-priority {
            margin-left: auto;
            flex-shrink: 0;
          }

          .task-limit {
            color: var(--text-secondary, #909399);
            font-size: 11px;
            flex-shrink: 0;
          }
        }

        .more-hint {
          text-align: center;
          color: var(--text-secondary, #909399);
          font-size: 11px;
          padding: 6px 0;
          font-style: italic;
        }
      }

      .queue-empty {
        color: var(--text-secondary, #909399);
        font-size: 12px;
        text-align: center;
        padding: 8px 0;
      }
    }
  }

  .task-list {
    margin-bottom: 16px;

    .task-list-header {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 12px;
      font-size: 14px;
      font-weight: 500;
      color: var(--text-primary, #e0e0e0);
    }

    .task-item {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 10px 12px;
      margin-bottom: 8px;
      background: rgba(255, 255, 255, 0.02);
      border-radius: 6px;
      font-size: 13px;

      &.running {
        background: rgba(64, 158, 255, 0.1);
        border-left: 3px solid #409eff;
      }

      &.success {
        .task-icon {
          color: #67c23a;
        }
      }

      &.failed {
        background: rgba(245, 108, 108, 0.1);
        border-left: 3px solid #f56c6c;

        .task-icon {
          color: #f56c6c;
        }
      }

      .task-icon {
        font-size: 16px;
      }

      .task-name {
        font-weight: 500;
        color: var(--text-primary, #e0e0e0);
      }

      .task-args {
        color: #409eff;
        font-family: monospace;
      }

      .task-worker {
        color: var(--text-secondary, #909399);
        font-size: 12px;
      }

      .task-time {
        color: var(--text-secondary, #909399);
        margin-left: auto;
      }

      .error-icon {
        color: #e6a23c;
        cursor: pointer;
      }
    }
  }

  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 40px;
    color: var(--text-secondary, #909399);

    p {
      margin-top: 12px;
      font-size: 14px;
    }
  }

  .spinning {
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }
}
</style>
