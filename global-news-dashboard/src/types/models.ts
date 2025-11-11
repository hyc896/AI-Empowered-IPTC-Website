export interface MessageSource {
  id: string
  name: string
  adapter_name: string
  category?: string
  display_name?: string
  config?: Record<string, unknown>
  schedule?: string
  is_active: boolean
  last_crawled_at?: string
  created_at: string
  updated_at: string
}

export interface Message {
  id: string
  source_id?: string
  title: string
  content: string
  summary?: string
  url?: string
  author?: string
  provider?: string
  published_at?: string
  crawled_at?: string
  source_name?: string
  source?: string
  similarity?: number
  distance?: number
  rrf_score?: number
}

export interface MessageStats {
  sources?: Record<string, number>
  messages?: Record<string, number>
  recent_messages?: Record<string, number>
  total_sources: number
  total_messages: number
  recent_total?: number
  active_sources?: number
  last_crawled_at?: string
}
