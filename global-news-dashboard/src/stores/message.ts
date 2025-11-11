import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { MessageSource, Message, MessageStats } from '@/types/models'
import type { MessageState } from '@/types/store'
import * as messageApi from '@/api/message'
import type { GetMessagesParams } from '@/api/message'

export const useMessageStore = defineStore('message', () => {
  const sources = ref<MessageSource[]>([])
  const messages = ref<Message[]>([])
  const total = ref<number>(0)
  const currentSourceId = ref<string | null>(null)
  const currentFilter = ref<MessageState['currentFilter']>({})
  const stats = ref<MessageStats>({
    total_messages: 0,
    total_sources: 0,
    active_sources: 0
  })

  const currentSource = computed(() => {
    if (!currentSourceId.value) return null
    return sources.value.find((s) => s.id === currentSourceId.value) || null
  })

  async function fetchMessageSources(): Promise<void> {
    try {
      sources.value = await messageApi.getMessageSources()
    } catch (error) {
      console.error('Failed to fetch message sources:', error)
      throw error
    }
  }

  async function fetchMessageSource(sourceId: string): Promise<MessageSource> {
    try {
      const source = await messageApi.getMessageSource(sourceId)
      const index = sources.value.findIndex((s) => s.id === sourceId)
      if (index !== -1) {
        sources.value[index] = source
      } else {
        sources.value.push(source)
      }
      return source
    } catch (error) {
      console.error('Failed to fetch message source:', error)
      throw error
    }
  }

  async function createMessageSource(
    data: Parameters<typeof messageApi.createMessageSource>[0]
  ): Promise<MessageSource> {
    try {
      const source = await messageApi.createMessageSource(data)
      sources.value.push(source)
      return source
    } catch (error) {
      console.error('Failed to create message source:', error)
      throw error
    }
  }

  async function updateMessageSource(
    sourceId: string,
    data: Parameters<typeof messageApi.updateMessageSource>[1]
  ): Promise<void> {
    try {
      const updated = await messageApi.updateMessageSource(sourceId, data)
      const index = sources.value.findIndex((s) => s.id === sourceId)
      if (index !== -1) {
        sources.value[index] = updated
      }
    } catch (error) {
      console.error('Failed to update message source:', error)
      throw error
    }
  }

  async function deleteMessageSource(sourceId: string): Promise<void> {
    try {
      await messageApi.deleteMessageSource(sourceId)
      sources.value = sources.value.filter((s) => s.id !== sourceId)
      if (currentSourceId.value === sourceId) {
        currentSourceId.value = null
      }
    } catch (error) {
      console.error('Failed to delete message source:', error)
      throw error
    }
  }

  async function fetchMessages(params?: GetMessagesParams): Promise<void> {
    try {
      const response = await messageApi.getMessages(params)
      messages.value = response.items
      total.value = response.total
    } catch (error) {
      console.error('Failed to fetch messages:', error)
      throw error
    }
  }

  async function fetchMessageStats(): Promise<void> {
    try {
      stats.value = await messageApi.getMessageStats()
    } catch (error) {
      console.error('Failed to fetch message stats:', error)
      throw error
    }
  }

  function setCurrentSource(sourceId: string | null): void {
    currentSourceId.value = sourceId
  }

  function setFilter(filter: MessageState['currentFilter']): void {
    currentFilter.value = filter
  }

  return {
    sources,
    messages,
    total,
    currentSourceId,
    currentSource,
    currentFilter,
    stats,
    fetchMessageSources,
    fetchMessageSource,
    createMessageSource,
    updateMessageSource,
    deleteMessageSource,
    fetchMessages,
    fetchMessageStats,
    setCurrentSource,
    setFilter
  }
})
