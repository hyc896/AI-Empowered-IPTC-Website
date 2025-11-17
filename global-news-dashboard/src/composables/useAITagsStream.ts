import { ref, onMounted, onUnmounted } from 'vue'
import axiosInstance from '@/api'

export interface AIMessage {
  message_id: string
  title: string
  summary: string
  ai_tag: 'AI治理信息' | 'AI科研信息' | 'AI产业信息'
  source_name: string
  timestamp: string
}

export interface AITagsData {
  'AI治理信息': AIMessage[]
  'AI科研信息': AIMessage[]
  'AI产业信息': AIMessage[]
}

export function useAITagsStream() {
  const messages = ref<AITagsData>({
    'AI治理信息': [],
    'AI科研信息': [],
    'AI产业信息': []
  })

  const isConnected = ref(false)
  const error = ref<string | null>(null)
  const isLoading = ref(false)
  const timeRange = ref<number>(24) // 默认24小时，0表示全部历史
  let reconnectTimer: number | null = null

  /**
   * 加载历史消息（根据时间范围）
   */
  const loadRecentMessages = async (hours?: number) => {
    try {
      isLoading.value = true
      const hoursParam = hours !== undefined ? hours : timeRange.value

      const response = await axiosInstance.get<AITagsData>('/api/v1/events/ai-tags/recent', {
        params: {
          limit: 100,
          hours: hoursParam || 0 // 0表示不限制时间
        }
      })

      // 直接替换为历史数据
      messages.value = response.data
      console.log(`已加载${hoursParam ? hoursParam + '小时内' : '所有'}AI标签消息:`, {
        治理: response.data['AI治理信息'].length,
        科研: response.data['AI科研信息'].length,
        产业: response.data['AI产业信息'].length
      })
    } catch (err) {
      console.error('加载历史AI标签消息失败:', err)
      error.value = '加载历史数据失败'
    } finally {
      isLoading.value = false
    }
  }

  /**
   * 切换时间范围
   */
  const switchTimeRange = async (hours: number) => {
    timeRange.value = hours
    await loadRecentMessages(hours)
  }

  /**
   * 启动轮询（替代SSE）
   */
  const startPolling = () => {
    // 每30秒轮询一次新消息
    const pollingInterval = setInterval(async () => {
      try {
        await loadRecentMessages()
        isConnected.value = true
        error.value = null
      } catch (err) {
        console.error('轮询失败:', err)
        isConnected.value = false
        error.value = '数据刷新失败'
      }
    }, 30000) // 30秒

    // 保存定时器以便清理
    reconnectTimer = pollingInterval as unknown as number
    isConnected.value = true
  }

  /**
   * 停止轮询
   */
  const stopPolling = () => {
    if (reconnectTimer !== null) {
      clearInterval(reconnectTimer)
      reconnectTimer = null
    }
    isConnected.value = false
  }

  // 保持connect和disconnect接口兼容性
  const connect = startPolling
  const disconnect = stopPolling


  // 生命周期管理
  onMounted(async () => {
    // 先加载历史数据
    await loadRecentMessages()
    // 启动轮询（每30秒刷新）
    connect()
  })

  onUnmounted(() => {
    // 停止轮询
    disconnect()
  })

  return {
    messages,
    isConnected,
    isLoading,
    error,
    timeRange,
    connect,
    disconnect,
    loadRecentMessages,
    switchTimeRange
  }
}
