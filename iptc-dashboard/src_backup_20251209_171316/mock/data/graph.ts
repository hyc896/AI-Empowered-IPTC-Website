import type { GraphData, GraphNode, GraphEdge } from '@/types/graph'

/**
 * Mock知识图谱数据
 */

export const mockGraphNodes: GraphNode[] = [
  // 知识点节点
  { id: 'kp_001', label: '以人民为中心', type: 'knowledge_point', meta: { chapter: '第一章' } },
  { id: 'kp_002', label: '共建共治共享', type: 'knowledge_point', meta: { chapter: '第一章' } },
  { id: 'kp_003', label: '绿水青山就是金山银山', type: 'knowledge_point', meta: { chapter: '第二章' } },
  { id: 'kp_004', label: '乡村振兴战略', type: 'knowledge_point', meta: { chapter: '第二章' } },
  { id: 'kp_005', label: '新发展理念', type: 'knowledge_point', meta: { chapter: '第三章' } },
  { id: 'kp_006', label: '创新驱动发展', type: 'knowledge_point', meta: { chapter: '第三章' } },
  { id: 'kp_007', label: '精准扶贫', type: 'knowledge_point', meta: { chapter: '第四章' } },
  { id: 'kp_008', label: '共同富裕', type: 'knowledge_point', meta: { chapter: '第四章' } },
  { id: 'kp_009', label: '高质量发展', type: 'knowledge_point', meta: { chapter: '第五章' } },
  { id: 'kp_010', label: '生态文明建设', type: 'knowledge_point', meta: { chapter: '第二章' } },

  // 案例节点
  { id: 'case_001', label: '浙江老年食堂', type: 'case', meta: { summary: '以人民为中心的实践' } },
  { id: 'case_002', label: '三门若干清村', type: 'case', meta: { summary: '生态致富典范' } },
  { id: 'case_003', label: '深圳科技创新', type: 'case', meta: { summary: '创新驱动样板' } },
  { id: 'case_004', label: '贵州大数据扶贫', type: 'case', meta: { summary: '精准扶贫实践' } },
  { id: 'case_005', label: '雄安新区建设', type: 'case', meta: { summary: '新发展理念体现' } }
]

export const mockGraphEdges: GraphEdge[] = [
  // 案例001关联
  { source: 'case_001', target: 'kp_001', type: 'RELATES_TO' },
  { source: 'case_001', target: 'kp_002', type: 'RELATES_TO' },

  // 案例002关联
  { source: 'case_002', target: 'kp_003', type: 'RELATES_TO' },
  { source: 'case_002', target: 'kp_004', type: 'RELATES_TO' },
  { source: 'case_002', target: 'kp_010', type: 'RELATES_TO' },

  // 案例003关联
  { source: 'case_003', target: 'kp_005', type: 'RELATES_TO' },
  { source: 'case_003', target: 'kp_006', type: 'RELATES_TO' },
  { source: 'case_003', target: 'kp_009', type: 'RELATES_TO' },

  // 案例004关联
  { source: 'case_004', target: 'kp_007', type: 'RELATES_TO' },
  { source: 'case_004', target: 'kp_008', type: 'RELATES_TO' },

  // 案例005关联
  { source: 'case_005', target: 'kp_005', type: 'RELATES_TO' },
  { source: 'case_005', target: 'kp_009', type: 'RELATES_TO' },

  // 知识点之间的关联
  { source: 'kp_001', target: 'kp_002', type: 'RELATES_TO' },
  { source: 'kp_001', target: 'kp_008', type: 'RELATES_TO' },
  { source: 'kp_003', target: 'kp_010', type: 'RELATES_TO' },
  { source: 'kp_003', target: 'kp_004', type: 'RELATES_TO' },
  { source: 'kp_005', target: 'kp_006', type: 'RELATES_TO' },
  { source: 'kp_005', target: 'kp_009', type: 'RELATES_TO' },
  { source: 'kp_007', target: 'kp_008', type: 'RELATES_TO' }
]

export const mockGraphData: GraphData = {
  nodes: mockGraphNodes,
  edges: mockGraphEdges
}

// 根据案例ID获取关联图谱
export function getMockCaseRelations(caseId: string): GraphData {
  // 找到该案例的所有关联边
  const caseEdges = mockGraphEdges.filter(edge => edge.source === caseId)

  // 找到关联的知识点ID
  const relatedKpIds = caseEdges.map(edge => edge.target)

  // 找到知识点节点
  const relatedKpNodes = mockGraphNodes.filter(node =>
    relatedKpIds.includes(node.id)
  )

  // 找到案例节点
  const caseNode = mockGraphNodes.find(node => node.id === caseId)

  return {
    nodes: caseNode ? [caseNode, ...relatedKpNodes] : relatedKpNodes,
    edges: caseEdges
  }
}
