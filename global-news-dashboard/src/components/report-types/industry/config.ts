/**
 * 产业日报配置
 * 主题：金黄商业风 - 活力、商业、增长
 */

import type { ReportTypeConfig } from '../types'

export const industryConfig: ReportTypeConfig = {
  type: 'industry',
  name: '产业日报',
  icon: '💼',
  description: '剖析AI企业动态、投融资、商业模式、市场竞争',

  theme: {
    primary: '#f59e0b',
    secondary: '#fbbf24',
    accent: '#fcd34d',
    bgGradient: 'linear-gradient(180deg, #451a03 0%, #78350f 50%, #92400e 100%)',
    bannerGradient: 'linear-gradient(135deg, rgba(69, 26, 3, 0.7) 0%, rgba(146, 64, 14, 0.7) 100%)',
    glowColor: 'rgba(245, 158, 11, 0.3)',
    borderColor: 'rgba(245, 158, 11, 0.2)',
    textPrimary: '#ffffff',
    textSecondary: 'rgba(255, 255, 255, 0.75)',
    bannerImageKeywords: 'business,industry,startup,innovation'
  },

  statCards: {
    total: {
      iconBg: 'rgba(245, 158, 11, 0.15)',
      iconColor: '#f59e0b',
      valueColor: '#ffffff',
      valueShadow: '0 0 20px rgba(245, 158, 11, 0.6)'
    },
    industry: {
      iconBg: 'rgba(251, 191, 36, 0.2)',
      iconColor: '#fbbf24',
      valueColor: '#fbbf24',
      valueShadow: '0 0 20px rgba(251, 191, 36, 0.6)'
    }
  },

  meta: {
    order: 4,
    enabled: true
  }
}
