<template>
  <div class="ai-tags-observer" :class="{ collapsed: isCollapsed }">
    <el-card class="observer-card">
      <!-- 标题栏 -->
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <span class="title">AI标签实时观察</span>
            <!-- 时间范围切换 -->
            <el-segmented
              v-if="!isCollapsed"
              v-model="currentTimeRange"
              :options="timeRangeOptions"
              size="small"
              @change="handleTimeRangeChange"
              class="time-range-selector"
            />
            <el-badge
              v-if="!isCollapsed"
              :value="totalMessagesCount"
              :max="999"
              class="badge"
              type="primary"
            />
          </div>
          <div class="header-right">
            <!-- 连接状态指示器 -->
            <el-tooltip :content="connectionStatus" placement="top">
              <div
                class="connection-indicator"
                :class="{ connected: isConnected, disconnected: !isConnected }"
              >
                <span class="pulse-dot"></span>
              </div>
            </el-tooltip>
            <!-- 折叠/展开按钮 -->
            <el-button
              :icon="isCollapsed ? Expand : Fold"
              size="small"
              circle
              @click="toggleCollapse"
            />
          </div>
        </div>
      </template>

      <!-- 主体内容 -->
      <div v-show="!isCollapsed" class="observer-body">
        <!-- 错误提示 -->
        <el-alert
          v-if="error"
          type="error"
          :title="error"
          :closable="false"
          show-icon
          class="error-alert"
        />

        <!-- 标签页 -->
        <el-tabs v-model="activeTab" class="ai-tags-tabs" @tab-change="handleTabChange">
          <el-tab-pane
            v-for="tag in aiTags"
            :key="tag"
            :label="tag"
            :name="tag"
          >
            <template #label>
              <div class="tab-label">
                <span>{{ tag }}</span>
                <el-badge
                  :value="messages[tag].length"
                  :max="99"
                  :type="getTagBadgeType(tag)"
                  class="tab-badge"
                />
              </div>
            </template>

            <!-- 消息列表 -->
            <div class="message-list-container">
              <el-scrollbar v-if="messages[tag].length > 0" height="400px">
                <div class="message-list">
                  <div
                    v-for="message in messages[tag]"
                    :key="message.message_id"
                    class="message-item"
                  >
                    <div class="message-header">
                      <span class="source-name">{{ message.source_name }}</span>
                      <span class="timestamp">{{ formatTime(message.timestamp) }}</span>
                    </div>
                    <h5 class="message-title">{{ message.title }}</h5>
                    <p class="message-summary">{{ truncateText(message.summary, 80) }}</p>
                  </div>
                </div>
              </el-scrollbar>
              <el-empty v-else description="暂无数据" :image-size="80" />
            </div>
          </el-tab-pane>
        </el-tabs>

        <!-- 提示信息 -->
        <div class="footer-tip">
          <span>显示最近24小时内的AI标签消息（最多100条/类别）</span>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { Expand, Fold } from '@element-plus/icons-vue'
import { useAITagsStream } from '@/composables/useAITagsStream'
import type { AIMessage } from '@/composables/useAITagsStream'

const { messages, isConnected, error, timeRange, switchTimeRange } = useAITagsStream()

const isCollapsed = ref(false)
const activeTab = ref<'AI治理信息' | 'AI科研信息' | 'AI产业信息'>('AI治理信息')
const currentTimeRange = ref<number>(24)

const aiTags = ['AI治理信息', 'AI科研信息', 'AI产业信息'] as const

const timeRangeOptions = [
  { label: '24h', value: 24 },
  { label: '全部', value: 0 }
]

const totalMessagesCount = computed(() => {
  return messages.value['AI治理信息'].length +
    messages.value['AI科研信息'].length +
    messages.value['AI产业信息'].length
})

const connectionStatus = computed(() => {
  return isConnected.value ? '数据实时刷新中' : '数据刷新已停止'
})

const toggleCollapse = () => {
  isCollapsed.value = !isCollapsed.value
}

const handleTabChange = (tabName: string) => {
  console.log('切换到标签:', tabName)
}

const handleTimeRangeChange = (value: number) => {
  console.log('切换时间范围:', value === 0 ? '全部' : `${value}小时`)
  switchTimeRange(value)
}

const getTagBadgeType = (tag: string) => {
  switch (tag) {
    case 'AI治理信息':
      return 'success'
    case 'AI科研信息':
      return 'warning'
    case 'AI产业信息':
      return 'danger'
    default:
      return 'info'
  }
}

const formatTime = (timestamp: string): string => {
  const date = new Date(timestamp)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)

  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes}分钟前`
  if (hours < 24) return `${hours}小时前`

  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const truncateText = (text: string, maxLength: number): string => {
  if (!text) return ''
  return text.length > maxLength ? text.substring(0, maxLength) + '...' : text
}
</script>

<style scoped lang="scss">
.ai-tags-observer {
  position: fixed;
  bottom: 20px;
  left: 20px;
  z-index: 100;
  width: 450px;
  transition: all 0.3s ease;

  &.collapsed {
    width: auto;

    .observer-card {
      :deep(.el-card__body) {
        padding: 0;
      }
    }
  }

  .observer-card {
    background: rgba(255, 255, 255, 0.05);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.1);
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);

    :deep(.el-card__header) {
      background: transparent;
      border-bottom: 1px solid rgba(255, 255, 255, 0.1);
      padding: 12px 16px;
    }

    :deep(.el-card__body) {
      background: transparent;
      padding: 16px;
      max-height: 500px;
      overflow: hidden;
    }

    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;

      .header-left {
        display: flex;
        align-items: center;
        gap: 10px;

        .title {
          font-size: 14px;
          font-weight: 600;
          color: white;
          text-transform: uppercase;
          letter-spacing: 1px;
        }

        .time-range-selector {
          :deep(.el-segmented) {
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            padding: 2px;
          }

          :deep(.el-segmented__item) {
            color: rgba(255, 255, 255, 0.7);
            font-size: 12px;
            padding: 2px 8px;
            min-width: 40px;

            &.is-selected {
              background: rgba(102, 126, 234, 0.6);
              color: white;
            }

            &:hover {
              color: white;
            }
          }
        }

        .badge {
          :deep(.el-badge__content) {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border: none;
          }
        }
      }

      .header-right {
        display: flex;
        align-items: center;
        gap: 10px;

        .connection-indicator {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 24px;
          height: 24px;

          .pulse-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background-color: #ef4444;
            transition: all 0.3s;
          }

          &.connected .pulse-dot {
            background-color: #10b981;
            animation: pulse 2s infinite;
          }

          &.disconnected .pulse-dot {
            background-color: #ef4444;
          }
        }

        :deep(.el-button) {
          background: rgba(255, 255, 255, 0.1);
          border: 1px solid rgba(255, 255, 255, 0.2);
          color: white;

          &:hover {
            background: rgba(255, 255, 255, 0.2);
            border-color: rgba(255, 255, 255, 0.3);
          }
        }
      }
    }
  }

  .observer-body {
    .error-alert {
      margin-bottom: 16px;
      background: rgba(239, 68, 68, 0.1);
      border-color: rgba(239, 68, 68, 0.3);

      :deep(.el-alert__title) {
        color: #fca5a5;
      }
    }

    .ai-tags-tabs {
      :deep(.el-tabs__header) {
        margin-bottom: 16px;
      }

      :deep(.el-tabs__nav-wrap) {
        &::after {
          background-color: rgba(255, 255, 255, 0.1);
        }
      }

      :deep(.el-tabs__item) {
        color: rgba(255, 255, 255, 0.7);
        font-size: 13px;

        &:hover {
          color: rgba(255, 255, 255, 0.9);
        }

        &.is-active {
          color: white;
          font-weight: 600;
        }
      }

      :deep(.el-tabs__active-bar) {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
      }

      .tab-label {
        display: flex;
        align-items: center;
        gap: 8px;

        .tab-badge {
          :deep(.el-badge__content) {
            font-size: 10px;
            height: 16px;
            line-height: 16px;
            padding: 0 5px;
          }
        }
      }
    }

    .message-list-container {
      .message-list {
        .message-item {
          background: rgba(255, 255, 255, 0.05);
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 8px;
          padding: 12px;
          margin-bottom: 12px;
          transition: all 0.3s;
          cursor: pointer;

          &:hover {
            background: rgba(255, 255, 255, 0.1);
            border-color: rgba(255, 255, 255, 0.2);
            transform: translateX(4px);
          }

          &:last-child {
            margin-bottom: 0;
          }

          .message-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;

            .source-name {
              display: inline-block;
              background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
              color: white;
              font-size: 10px;
              padding: 3px 8px;
              border-radius: 10px;
              font-weight: 600;
            }

            .timestamp {
              font-size: 11px;
              color: rgba(255, 255, 255, 0.5);
            }
          }

          .message-title {
            font-size: 13px;
            font-weight: 600;
            color: white;
            margin-bottom: 6px;
            line-height: 1.4;
          }

          .message-summary {
            font-size: 12px;
            color: rgba(255, 255, 255, 0.7);
            line-height: 1.5;
            margin: 0;
          }
        }
      }

      :deep(.el-empty) {
        padding: 40px 0;

        .el-empty__description p {
          color: rgba(255, 255, 255, 0.5);
        }

        .el-empty__image svg {
          fill: rgba(255, 255, 255, 0.3);
        }
      }
    }

    .footer-tip {
      margin-top: 12px;
      padding-top: 12px;
      border-top: 1px solid rgba(255, 255, 255, 0.1);
      text-align: center;
      font-size: 11px;
      color: rgba(255, 255, 255, 0.5);
    }
  }
}

@keyframes pulse {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7);
  }
  50% {
    box-shadow: 0 0 0 6px rgba(16, 185, 129, 0);
  }
}
</style>
