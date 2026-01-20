/**
 * G6 图谱相关类型定义
 */
import type { EntityType, RelationType } from './index'

/**
 * G6 节点数据
 */
export interface G6Node {
  id: string
  label: string
  type: EntityType
  style?: {
    fill?: string
    stroke?: string
    lineWidth?: number
  }
  [key: string]: any
}

/**
 * G6 边数据
 */
export interface G6Edge {
  source: string
  target: string
  label: RelationType
  style?: {
    stroke?: string
    lineWidth?: number
  }
  [key: string]: any
}

/**
 * G6 图数据
 */
export interface G6GraphData {
  nodes: G6Node[]
  edges: G6Edge[]
}

/**
 * 图谱可视化响应
 */
export interface GraphVisualizeResponse {
  file_id: string
  page_range: string
  graph_data: G6GraphData
  stats: {
    node_count: number
    edge_count: number
  }
}
