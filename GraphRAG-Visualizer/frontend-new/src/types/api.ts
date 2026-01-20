/**
 * API 相关类型定义
 * 定义与后端 API 交互的数据结构
 */
import type { Entity, Relation } from './index'

// ============ 文件上传相关 ============

/**
 * 文件上传响应
 */
export interface UploadResponse {
  file_id: string
  filename: string
  total_pages: number
  current_range: string
  text: string
  char_count: number
}

/**
 * 页面范围请求
 */
export interface PageRangeRequest {
  page_start: number
  page_end: number
}

// ============ 实体提取相关 ============

/**
 * 实体提取请求
 */
export interface ExtractRequest {
  file_id: string
  text: string
  language?: 'zh' | 'en'
}

/**
 * 实体提取响应
 */
export interface ExtractResponse {
  file_id: string
  entities: Entity[]
  relations: Relation[]
  stats: {
    entity_count: number
    relation_count: number
    processing_time: number
  }
}
