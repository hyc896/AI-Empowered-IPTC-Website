import type { GraphData, GraphNode } from '@/types/graph'
import { mockGraphData, getMockCaseRelations } from '../data/graph'

/**
 * Mock图谱服务
 * 模拟真实API的行为
 */

export class MockGraphService {
  /**
   * 获取完整图谱
   */
  async getFullGraph(): Promise<GraphData> {
    // 模拟网络延迟
    await this.delay(500)

    return mockGraphData
  }

  /**
   * 获取案例关联图谱
   */
  async getCaseRelations(caseId: string): Promise<GraphData> {
    await this.delay(300)

    return getMockCaseRelations(caseId)
  }

  /**
   * 模拟网络延迟
   */
  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms))
  }
}

export const mockGraphService = new MockGraphService()
