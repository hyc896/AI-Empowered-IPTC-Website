/**
 * 类型定义文件
 * 定义项目中使用的所有 TypeScript 类型
 */

// ============ 实体相关类型 ============

/**
 * 实体类型枚举
 */
export type EntityType =
  | 'Company'
  | 'Person'
  | 'Technology'
  | 'Product'
  | 'Organization'
  | 'Event'
  | 'Concept'
  | 'Location'

/**
 * 实体接口
 */
export interface Entity {
  name: string
  type: EntityType
  aliases?: string[]
  attributes?: Record<string, any>
  mention_count?: number
}

// ============ 关系相关类型 ============

/**
 * 关系类型枚举
 */
export type RelationType =
  | 'WORKS_AT'
  | 'INVESTS_IN'
  | 'DEVELOPS'
  | 'COMPETES_WITH'
  | 'PARTNERS_WITH'
  | 'BASED_ON'
  | 'LOCATED_IN'

/**
 * 关系接口
 */
export interface Relation {
  source: string
  target: string
  type: RelationType
  properties?: Record<string, any>
}
