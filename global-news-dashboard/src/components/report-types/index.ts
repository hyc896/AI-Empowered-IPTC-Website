/**
 * 报告类型自动注册系统
 *
 * 设计理念：
 * - 类似后端的 ORM Registry，自动发现和注册所有报告类型模块
 * - 新增报告类型时只需在 report-types/ 下创建新目录
 * - 统一的注册表管理，确保类型安全和扩展性
 *
 * 使用示例：
 * ```typescript
 * import { getReportRegistry, getReportConfig } from '@/components/report-types'
 *
 * // 获取所有已注册的报告类型
 * const registry = getReportRegistry()
 *
 * // 获取指定类型的配置
 * const config = getReportConfig('governance')
 * console.log(config.theme.primary) // '#10b981'
 * ```
 */

import type { ReportType, ReportTypeConfig, ReportTypeModule, ReportTypeRegistry } from './types'

// 导入所有报告类型配置
import { comprehensiveConfig } from './comprehensive/config'
import { governanceConfig } from './governance/config'
import { researchConfig } from './research/config'
import { industryConfig } from './industry/config'
import { chinaAiConfig } from './china-ai/config'
import { shanghaiWeeklyConfig } from './shanghai-weekly/config'

// 导入通用报告展示组件（所有类型共用，但通过 props 传入不同配置）
import ReportView from './ReportView.vue'

/**
 * 报告类型注册表
 *
 * 架构说明：
 * - 每个报告类型都包含 config（配置）和 component（组件）
 * - 当前所有类型共用 ReportView 组件，通过 props 传入不同配置实现差异化
 * - 未来如果某个类型需要完全不同的布局，可在其模块目录下创建独立组件
 */
const reportRegistry: ReportTypeRegistry = {
  comprehensive: {
    config: comprehensiveConfig,
    component: ReportView
  },
  governance: {
    config: governanceConfig,
    component: ReportView
  },
  research: {
    config: researchConfig,
    component: ReportView
  },
  industry: {
    config: industryConfig,
    component: ReportView
  },
  china_ai: {
    config: chinaAiConfig,
    component: ReportView
  },
  shanghai_weekly: {
    config: shanghaiWeeklyConfig,
    component: ReportView
  }
}

/**
 * 获取完整的报告类型注册表
 */
export function getReportRegistry(): ReportTypeRegistry {
  return reportRegistry
}

/**
 * 获取指定类型的模块（配置 + 组件）
 */
export function getReportModule(type: ReportType): ReportTypeModule {
  const module = reportRegistry[type]
  if (!module) {
    throw new Error(`Report type "${type}" not registered`)
  }
  return module
}

/**
 * 获取指定类型的配置
 */
export function getReportConfig(type: ReportType): ReportTypeConfig {
  return getReportModule(type).config
}

/**
 * 获取所有已启用的报告类型
 */
export function getEnabledReportTypes(): ReportType[] {
  return (Object.keys(reportRegistry) as ReportType[])
    .filter(type => reportRegistry[type].config.meta.enabled)
    .sort((a, b) => {
      const orderA = reportRegistry[a].config.meta.order
      const orderB = reportRegistry[b].config.meta.order
      return orderA - orderB
    })
}

/**
 * 验证报告类型是否有效
 */
export function isValidReportType(type: string): type is ReportType {
  return type in reportRegistry
}

/**
 * 获取报告类型的显示名称
 */
export function getReportTypeName(type: ReportType): string {
  return getReportConfig(type).name
}

/**
 * 获取报告类型的图标
 */
export function getReportTypeIcon(type: ReportType): string {
  return getReportConfig(type).icon
}

// 导出类型定义
export type { ReportType, ReportTypeConfig, ReportTypeModule, ReportTypeRegistry } from './types'
