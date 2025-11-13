/**
 * 地理统计API
 *
 * 提供按地区聚合的消息统计和查询功能
 */

import axiosInstance from './index'

/**
 * 地理统计响应接口
 */
export interface GeoStatistics {
  statistics: Record<string, number>  // 中文国家名 → 消息数量
  total_messages: number
  total_countries: number
  filters_applied: {
    source_id?: string
    start_date?: string
    end_date?: string
    industry_tags?: string
  }
}

/**
 * 地理统计请求参数
 */
export interface GeoStatisticsParams {
  source_id?: string      // 消息源ID筛选
  start_date?: string     // 开始日期 YYYY-MM-DD
  end_date?: string       // 结束日期 YYYY-MM-DD
  industry_tags?: string  // 行业标签，逗号分隔
}

/**
 * 地区消息项接口
 */
export interface RegionMessage {
  id: string
  title: string
  content: string
  summary?: string
  source_name: string
  source_id: string
  published_at?: string
  url?: string
  region?: string
  industry_tags?: string
}

/**
 * 地区消息列表请求参数
 */
export interface RegionMessagesParams {
  source_id?: string
  start_date?: string
  end_date?: string
  industry_tags?: string
  limit?: number
  offset?: number
}

/**
 * 地区消息列表响应接口
 */
export interface RegionMessagesResponse {
  items: RegionMessage[]
  total: number
  limit: number
  offset: number
  region: string
}

/**
 * 行业标签响应接口
 */
export interface IndustryTagsResponse {
  tags: string[]
  total: number
}

/**
 * 获取地理统计数据
 *
 * @param params - 筛选参数
 * @returns 各国家的消息数量统计（中文国家名作为key）
 *
 * @example
 * const stats = await getGeoStatistics({
 *   source_id: 'uuid',
 *   start_date: '2025-01-01',
 *   industry_tags: '人工智能,半导体'
 * })
 * // stats.statistics = { "中国": 256, "美国": 145, ... }
 */
export async function getGeoStatistics(params?: GeoStatisticsParams): Promise<GeoStatistics> {
  const response = await axiosInstance.get<GeoStatistics>('/api/v1/messages/statistics/by-region', { params })
  return response.data
}

/**
 * 获取指定地区的消息列表
 *
 * @param region - 地区名（中文），如"中国"、"美国"
 * @param params - 筛选和分页参数
 * @returns 该地区的消息列表
 *
 * @example
 * const response = await getMessagesByRegion('中国', {
 *   industry_tags: '人工智能',
 *   limit: 50,
 *   offset: 0
 * })
 * // response.items = [{ title, content, source_name, url, ... }, ...]
 */
export async function getMessagesByRegion(
  region: string,
  params?: RegionMessagesParams
): Promise<RegionMessagesResponse> {
  const response = await axiosInstance.get<RegionMessagesResponse>(
    `/api/v1/messages/by-region/${encodeURIComponent(region)}`,
    { params }
  )
  return response.data
}

/**
 * 获取所有可用的行业标签
 *
 * @returns 行业标签数组
 *
 * @example
 * const response = await getAllIndustryTags()
 * // response.tags = ["人工智能", "半导体", "新能源", ...]
 */
export async function getAllIndustryTags(): Promise<IndustryTagsResponse> {
  const response = await axiosInstance.get<IndustryTagsResponse>('/api/v1/messages/industry-tags')
  return response.data
}
