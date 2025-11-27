/**
 * 治理日报配置
 * 主题：翠绿权威风 - 规范、稳健、政策导向
 */

import type { ReportTypeConfig } from '../types'

export const governanceConfig: ReportTypeConfig = {
  type: 'governance',
  name: '治理日报',
  icon: '🏛️',
  description: '聚焦AI政策法规、监管动态、伦理讨论的专业分析',

  theme: {
    primary: '#10b981',
    secondary: '#34d399',
    accent: '#6ee7b7',
    bgGradient: 'linear-gradient(180deg, #064e3b 0%, #065f46 50%, #047857 100%)',
    bannerGradient: 'linear-gradient(135deg, rgba(6, 78, 59, 0.7) 0%, rgba(4, 120, 87, 0.7) 100%)',
    glowColor: 'rgba(16, 185, 129, 0.3)',
    borderColor: 'rgba(16, 185, 129, 0.2)',
    textPrimary: '#ffffff',
    textSecondary: 'rgba(255, 255, 255, 0.75)',
    bannerImageKeywords: 'government,policy,conference,law'
  },

  statCards: {
    total: {
      iconBg: 'rgba(16, 185, 129, 0.15)',
      iconColor: '#10b981',
      valueColor: '#ffffff',
      valueShadow: '0 0 20px rgba(16, 185, 129, 0.6)'
    },
    governance: {
      iconBg: 'rgba(52, 211, 153, 0.2)',
      iconColor: '#34d399',
      valueColor: '#34d399',
      valueShadow: '0 0 20px rgba(52, 211, 153, 0.6)'
    }
  },

  meta: {
    order: 2,
    enabled: true
  }
}
