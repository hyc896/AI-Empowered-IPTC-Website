export interface GraphNode {
  id: string
  label: string
  type: 'knowledge_point' | 'case'
  meta?: {
    chapter?: string
    summary?: string
  }
}

export interface GraphEdge {
  source: string
  target: string
  type: 'RELATES_TO'
}

export interface GraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
}




