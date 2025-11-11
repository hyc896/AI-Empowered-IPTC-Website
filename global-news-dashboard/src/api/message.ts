import axiosInstance from './index'
import type { MessageSource, Message, MessageStats } from '@/types/models'
import type { PaginatedResponse, PaginationParams } from '@/types/api'

export interface GetMessagesParams extends PaginationParams {
  source_id?: string
  keyword?: string
  start_date?: string
  end_date?: string
}

// 修改API路径，从/api/message改为/api/v1
export async function getMessageSources(): Promise<MessageSource[]> {
  const response = await axiosInstance.get<MessageSource[]>('/api/v1/sources')
  return response.data
}

export async function getMessageSource(sourceId: string): Promise<MessageSource> {
  const response = await axiosInstance.get<MessageSource>(`/api/v1/sources/${sourceId}`)
  return response.data
}

export async function createMessageSource(data: {
  name: string
  adapter_name: string
  category?: string
  display_name?: string
  config?: Record<string, unknown>
  schedule?: string
  is_active?: boolean
}): Promise<MessageSource> {
  const response = await axiosInstance.post<MessageSource>('/api/v1/sources', data)
  return response.data
}

export async function updateMessageSource(
  sourceId: string,
  data: {
    name?: string
    display_name?: string
    config?: Record<string, unknown>
    schedule?: string
    is_active?: boolean
  }
): Promise<MessageSource> {
  const response = await axiosInstance.put<MessageSource>(`/api/v1/sources/${sourceId}`, data)
  return response.data
}

export async function deleteMessageSource(sourceId: string): Promise<void> {
  await axiosInstance.delete(`/api/v1/sources/${sourceId}`)
}

export async function getMessages(
  params?: GetMessagesParams
): Promise<PaginatedResponse<Message>> {
  const response = await axiosInstance.get<Message[]>('/api/v1/search/messages', { params })
  const items = response.data

  // 从响应头读取总数
  const total = parseInt(response.headers['x-total-count'] || '0', 10)

  return {
    items,
    total,
    limit: params?.limit ?? 50,
    offset: params?.offset ?? 0
  }
}

export async function getMessageStats(): Promise<MessageStats> {
  const response = await axiosInstance.get<MessageStats>('/api/v1/stats/overview')
  return response.data
}

export interface SearchMessagesRequest {
  source_type?: string
  query: string
  time_range?: {
    hours?: number
    start_date?: string
    end_date?: string
  }
  limit?: number
}

export interface SearchMessagesResponse {
  results: Message[]
  total: number
  query: string
  search_time: number
}

export async function searchMessages(request: SearchMessagesRequest): Promise<SearchMessagesResponse> {
  const response = await axiosInstance.post<SearchMessagesResponse>('/api/v1/search/messages', request)
  return response.data
}

export async function activateMessageSource(sourceId: string): Promise<void> {
  await axiosInstance.post(`/api/v1/sources/${sourceId}/activate`)
}

export async function deactivateMessageSource(sourceId: string): Promise<void> {
  await axiosInstance.post(`/api/v1/sources/${sourceId}/deactivate`)
}

export async function getMessageSourceStatus(sourceId: string): Promise<Record<string, unknown>> {
  const response = await axiosInstance.get(`/api/v1/sources/${sourceId}/status`)
  return response.data
}

export async function getAvailableSources(): Promise<string[]> {
  const response = await axiosInstance.get<string[]>('/api/v1/search/sources')
  return response.data
}
