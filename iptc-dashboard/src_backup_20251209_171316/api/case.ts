import type { CaseItem, CaseListParams, PaginatedResponse } from '@/types/case'
import request from './index'
import { env } from '@/config/env'
import { mockCaseService } from '@/mock/services/case'

/**
 * 真实API服务
 */
class RealCaseAPI {
  getCases(params: CaseListParams): Promise<PaginatedResponse<CaseItem>> {
    return request.get('/api/v1/iptc/cases', { params })
  }

  getCaseDetail(id: string): Promise<CaseItem> {
    return request.get(`/api/v1/iptc/cases/${id}`)
  }

  searchCases(query: string, top_k = 10): Promise<CaseItem[]> {
    return request.post('/api/v1/iptc/cases/search', { query, top_k })
  }
}

/**
 * API适配器：根据环境自动选择Mock或真实API
 */
class CaseAPIAdapter {
  private realAPI = new RealCaseAPI()
  private mockAPI = mockCaseService

  getCases(params: CaseListParams): Promise<PaginatedResponse<CaseItem>> {
    if (env.useMock) {
      console.log('📦 [Mock] 获取案例列表', params)
      return this.mockAPI.getCases(params)
    }
    return this.realAPI.getCases(params)
  }

  getCaseDetail(id: string): Promise<CaseItem> {
    if (env.useMock) {
      console.log('📦 [Mock] 获取案例详情', id)
      return this.mockAPI.getCaseDetail(id)
    }
    return this.realAPI.getCaseDetail(id)
  }

  searchCases(query: string, top_k = 10): Promise<CaseItem[]> {
    if (env.useMock) {
      console.log('📦 [Mock] 搜索案例', query, top_k)
      return this.mockAPI.searchCases(query, top_k)
    }
    return this.realAPI.searchCases(query, top_k)
  }
}

// 导出单例
export const caseAPI = new CaseAPIAdapter()

