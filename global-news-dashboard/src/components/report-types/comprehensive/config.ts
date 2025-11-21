/**
 * 综合日报配置
 * 主题：蓝紫科技风 - 全面、科技、未来感
 */

import type { ReportTypeConfig } from '../types'

export const comprehensiveConfig: ReportTypeConfig = {
  type: 'comprehensive',
  name: '综合日报',
  icon: '📊',
  description: '全面覆盖AI治理、科研、产业三大板块的深度分析报告',

  theme: {
    primary: '#00d4ff',
    secondary: '#a855f7',
    accent: '#f093fb',
    bgGradient: 'linear-gradient(180deg, #0a0e27 0%, #1a1b3d 50%, #2d1b69 100%)',
    bannerGradient: 'linear-gradient(135deg, rgba(30, 58, 138, 0.6) 0%, rgba(91, 33, 182, 0.6) 100%)',
    glowColor: 'rgba(0, 212, 255, 0.3)',
    borderColor: 'rgba(0, 212, 255, 0.2)',
    textPrimary: '#ffffff',
    textSecondary: 'rgba(255, 255, 255, 0.7)'
  },

  statCards: {
    total: {
      iconBg: 'rgba(0, 212, 255, 0.1)',
      iconColor: '#00d4ff',
      valueColor: '#ffffff',
      valueShadow: '0 0 20px rgba(0, 212, 255, 0.5)'
    },
    governance: {
      iconBg: 'rgba(16, 185, 129, 0.1)',
      iconColor: '#10b981',
      valueColor: '#10b981',
      valueShadow: '0 0 20px rgba(16, 185, 129, 0.5)'
    },
    research: {
      iconBg: 'rgba(245, 158, 11, 0.1)',
      iconColor: '#f59e0b',
      valueColor: '#f59e0b',
      valueShadow: '0 0 20px rgba(245, 158, 11, 0.5)'
    },
    industry: {
      iconBg: 'rgba(239, 68, 68, 0.1)',
      iconColor: '#ef4444',
      valueColor: '#ef4444',
      valueShadow: '0 0 20px rgba(239, 68, 68, 0.5)'
    }
  },

  meta: {
    order: 1,
    enabled: true
  }
}
