import request from './index'
import type { GraphData } from '@/types/graph'
import { env } from '@/config/env'
import { mockGraphService } from '@/mock/services/graph'

/**
 * 真实API服务
 */
class RealGraphAPI {
  getFullGraph(): Promise<GraphData> {
    return request.get('/api/v1/iptc/graph/full')
  }

  getCaseRelations(caseId: string): Promise<GraphData> {
    return request.get(`/api/v1/iptc/graph/case/${caseId}`)
  }
}

/**
 * API适配器：根据环境自动选择Mock或真实API
 */
class GraphAPIAdapter {
  private realAPI = new RealGraphAPI()
  private mockAPI = mockGraphService

  getFullGraph(): Promise<GraphData> {
    if (env.useMock) {
      console.log('📦 [Mock] 获取完整图谱')
      return this.mockAPI.getFullGraph()
    }
    return this.realAPI.getFullGraph()
  }

  getCaseRelations(caseId: string): Promise<GraphData> {
    if (env.useMock) {
      console.log('📦 [Mock] 获取案例关联图谱', caseId)
      return this.mockAPI.getCaseRelations(caseId)
    }
    return this.realAPI.getCaseRelations(caseId)
  }
}

// 导出单例
export const graphAPI = new GraphAPIAdapter()

