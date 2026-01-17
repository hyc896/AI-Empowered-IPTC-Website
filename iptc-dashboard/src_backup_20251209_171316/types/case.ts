export interface CaseItem {
  id: string
  title: string
  content: string
  summary: string
  source_url: string
  tags: string[]
  related_knowledge_points: Array<{
    id: string
    name: string
    similarity: number
  }>
  source_message_ids: string[]
  published_at: string
  created_at: string
}

export interface CaseListParams {
  page: number
  size: number
  keyword?: string
  knowledge_point_id?: string
  sort?: 'latest' | 'popular'
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  size: number
  pages: number
}




