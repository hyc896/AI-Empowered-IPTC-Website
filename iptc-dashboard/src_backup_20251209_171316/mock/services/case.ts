import type { CaseItem, CaseListParams, PaginatedResponse } from '@/types/case'
import { getMockCasesPaginated, getMockCaseById, searchMockCases, mockCases } from '../data/cases'

/**
 * Mock案例服务
 * 模拟真实API的行为
 */

export class MockCaseService {
  /**
   * 获取案例列表
   */
  async getCases(params: CaseListParams): Promise<PaginatedResponse<CaseItem>> {
    // 模拟网络延迟
    await this.delay(300)

    let filteredCases = [...mockCases]

    // 关键词搜索
    if (params.keyword) {
      filteredCases = searchMockCases(params.keyword)
    }

    // 知识点筛选
    if (params.knowledge_point_id) {
      filteredCases = filteredCases.filter(c =>
        c.related_knowledge_points.some(kp => kp.id === params.knowledge_point_id)
      )
    }

    // 排序
    if (params.sort === 'popular') {
      // 模拟按热度排序（这里简单按关联知识点数量）
      filteredCases.sort((a, b) =>
        b.related_knowledge_points.length - a.related_knowledge_points.length
      )
    } else {
      // 默认按最新排序
      filteredCases.sort((a, b) =>
        new Date(b.published_at).getTime() - new Date(a.published_at).getTime()
      )
    }

    // 分页
    const start = (params.page - 1) * params.size
    const end = start + params.size
    const items = filteredCases.slice(start, end)

    return {
      items,
      total: filteredCases.length,
      page: params.page,
      size: params.size,
      pages: Math.ceil(filteredCases.length / params.size)
    }
  }

  /**
   * 获取案例详情
   */
  async getCaseDetail(id: string): Promise<CaseItem> {
    await this.delay(200)

    const caseItem = getMockCaseById(id)

    if (!caseItem) {
      throw new Error('案例不存在')
    }

    return caseItem
  }

  /**
   * 语义搜索案例
   */
  async searchCases(query: string, top_k = 10): Promise<CaseItem[]> {
    await this.delay(400)

    // 模拟语义搜索（实际上还是关键词搜索）
    const results = searchMockCases(query)
    return results.slice(0, top_k)
  }

  /**
   * 模拟网络延迟
   */
  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms))
  }
}

export const mockCaseService = new MockCaseService()
