/**
 * 中国AI日报配置
 * 主题：红金中国风 - 中国红与金色搭配，庄重大气
 */

import type { ReportTypeConfig } from '../types'

export const chinaAiConfig: ReportTypeConfig = {
  type: 'china_ai',
  name: '中国AI日报',
  icon: '🇨🇳',
  description: '聚焦中国人工智能领域的政策动态、产业发展与技术突破',

  theme: {
    primary: '#dc2626',
    secondary: '#f59e0b',
    accent: '#fbbf24',
    bgGradient: 'linear-gradient(180deg, #7f1d1d 0%, #991b1b 50%, #b91c1c 100%)',
    bannerGradient: 'linear-gradient(135deg, rgba(127, 29, 29, 0.85) 0%, rgba(185, 28, 28, 0.85) 50%, rgba(180, 83, 9, 0.7) 100%)',
    glowColor: 'rgba(220, 38, 38, 0.4)',
    borderColor: 'rgba(245, 158, 11, 0.3)',
    textPrimary: '#ffffff',
    textSecondary: 'rgba(255, 255, 255, 0.8)',
    bannerImageKeywords: 'china,beijing,technology,skyline'
  },

  statCards: {
    total: {
      iconBg: 'rgba(245, 158, 11, 0.2)',
      iconColor: '#f59e0b',
      valueColor: '#fbbf24',
      valueShadow: '0 0 20px rgba(245, 158, 11, 0.6)'
    },
    governance: {
      iconBg: 'rgba(220, 38, 38, 0.2)',
      iconColor: '#dc2626',
      valueColor: '#f87171',
      valueShadow: '0 0 20px rgba(220, 38, 38, 0.6)'
    },
    research: {
      iconBg: 'rgba(251, 191, 36, 0.2)',
      iconColor: '#fbbf24',
      valueColor: '#fcd34d',
      valueShadow: '0 0 20px rgba(251, 191, 36, 0.6)'
    },
    industry: {
      iconBg: 'rgba(239, 68, 68, 0.2)',
      iconColor: '#ef4444',
      valueColor: '#fca5a5',
      valueShadow: '0 0 20px rgba(239, 68, 68, 0.6)'
    }
  },

  meta: {
    order: 5,
    enabled: true
  }
}
