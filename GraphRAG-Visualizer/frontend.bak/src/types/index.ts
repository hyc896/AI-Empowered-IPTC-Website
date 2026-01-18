/**
 * 类型定义文件
 * 定义前端应用中使用的所有 TypeScript 类型
 */

// 文件上传响应
export interface UploadResponse {
  file_id: string
  filename: string
  total_pages: number
  current_range: string
  text: string
  char_count: number
}

// 实体类型
export interface Entity {
  name: string
  type: string
  aliases: string[]
  attributes: Record<string, any>
  mention_count: number
}

// 关系类型
export interface Relation {
  source: string
  target: string
  type: string
  properties: Record<string, any>
}

// 实体提取请求
export interface ExtractRequest {
  file_id: string
  text: string
  language: string
  page_range: string
}

// 实体提取响应
export interface ExtractResponse {
  entities: Entity[]
  relations: Relation[]
  stats: {
    entities_created: number
    relations_created: number
  }
}
