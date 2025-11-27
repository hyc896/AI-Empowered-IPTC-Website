/**
 * 报告类型模块化架构 - 类型定义
 *
 * 设计理念：
 * - 每个报告类型（comprehensive/governance/research/industry）都是独立模块
 * - 配置驱动：主题色、样式、行为都由 config.ts 定义
 * - 自动注册：新增报告类型时自动识别和加载
 * - 类型安全：TypeScript 自动推断，防止拼写错误
 */

import type { Component } from 'vue'

/**
 * 报告类型标识
 */
export type ReportType = 'comprehensive' | 'governance' | 'research' | 'industry' | 'china_ai' | 'shanghai_weekly'

/**
 * 主题配色配置
 */
export interface ThemeColors {
  primary: string           // 主色（用于主要UI元素）
  secondary: string         // 辅色（用于次要元素）
  accent: string            // 强调色（用于高亮、悬浮状态）
  bgGradient: string        // 背景渐变（整体背景）
  bannerGradient: string    // 横幅渐变（顶部封面区域）
  glowColor: string         // 光晕颜色（阴影、发光效果）
  borderColor: string       // 边框颜色
  textPrimary?: string      // 主要文本颜色（可选，默认白色）
  textSecondary?: string    // 次要文本颜色（可选，默认半透明白色）
  bannerImageKeywords?: string  // Banner背景图Unsplash关键词（如"ai,technology"）
}

/**
 * 统计卡片配色
 */
export interface StatCardColors {
  iconBg: string            // 图标背景色
  iconColor: string         // 图标颜色
  valueColor: string        // 数值颜色
  valueShadow: string       // 数值阴影
}

/**
 * 报告类型完整配置
 */
export interface ReportTypeConfig {
  type: ReportType          // 报告类型标识
  name: string              // 显示名称
  icon: string              // emoji 图标或图标组件
  description: string       // 描述文案
  theme: ThemeColors        // 主题配色
  statCards: {              // 统计卡片专属配色
    total?: StatCardColors
    governance?: StatCardColors
    research?: StatCardColors
    industry?: StatCardColors
  }
  meta: {                   // 元信息
    order: number           // Tab 排序顺序
    enabled: boolean        // 是否启用
  }
}

/**
 * 报告类型模块（包含配置和组件）
 */
export interface ReportTypeModule {
  config: ReportTypeConfig
  component: Component      // Vue 组件
}

/**
 * 报告类型注册表
 */
export type ReportTypeRegistry = Record<ReportType, ReportTypeModule>

/**
 * 报告数据接口（从API返回）
 */
export interface AIDailyReport {
  id: string
  report_date: string
  report_type: ReportType
  content: string
  statistics: Record<string, any>
  governance_count: number
  research_count: number
  industry_count: number
  total_messages: number
  generation_status: 'pending' | 'completed' | 'failed'
  error_message?: string
  generated_at: string
  model_version: string
}
