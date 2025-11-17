import axiosInstance from './index'

export interface AIDailyReport {
  id: string
  report_date: string
  content: string
  statistics: {
    governance_count: number
    research_count: number
    industry_count: number
    total_messages: number
    region_distribution: Record<string, number>
    source_distribution: Record<string, number>
    industry_distribution: Record<string, number>
  }
  governance_count: number
  research_count: number
  industry_count: number
  total_messages: number
  generation_status: 'pending' | 'completed' | 'failed'
  error_message: string | null
  generated_at: string
  model_version: string
}

export interface AIDailyReportListResponse {
  items: AIDailyReport[]
  total: number
  limit: number
  offset: number
}

/**
 * 获取最新的AI日报
 */
export const getLatestReport = async (): Promise<AIDailyReport> => {
  const response = await axiosInstance.get<AIDailyReport>('/api/v1/ai-reports/latest')
  return response.data
}

/**
 * 根据日期获取AI日报
 */
export const getReportByDate = async (reportDate: string): Promise<AIDailyReport> => {
  const response = await axiosInstance.get<AIDailyReport>(`/api/v1/ai-reports/${reportDate}`)
  return response.data
}

/**
 * 获取AI日报列表
 */
export const listReports = async (params?: {
  limit?: number
  offset?: number
  status?: 'pending' | 'completed' | 'failed'
}): Promise<AIDailyReportListResponse> => {
  const response = await axiosInstance.get<AIDailyReportListResponse>('/api/v1/ai-reports', {
    params
  })
  return response.data
}

/**
 * 手动触发AI日报生成
 */
export const triggerReportGeneration = async (): Promise<{ message: string; timestamp: string }> => {
  const response = await axiosInstance.post<{ message: string; timestamp: string }>(
    '/api/v1/ai-reports/generate'
  )
  return response.data
}
