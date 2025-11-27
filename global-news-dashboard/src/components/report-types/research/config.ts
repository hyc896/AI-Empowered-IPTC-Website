/**
 * 科研日报配置
 * 主题：理性蓝风 - 理性、学术、探索精神
 */

import type { ReportTypeConfig } from '../types'

export const researchConfig: ReportTypeConfig = {
  type: 'research',
  name: '科研日报',
  icon: '🔬',
  description: '深度解读AI前沿论文、技术突破、学术趋势',

  theme: {
    primary: '#3b82f6',
    secondary: '#60a5fa',
    accent: '#93c5fd',
    bgGradient: 'linear-gradient(180deg, #0c1e3d 0%, #1e3a5f 50%, #1e40af 100%)',
    bannerGradient: 'linear-gradient(135deg, rgba(30, 58, 138, 0.7) 0%, rgba(37, 99, 235, 0.7) 100%)',
    glowColor: 'rgba(59, 130, 246, 0.3)',
    borderColor: 'rgba(59, 130, 246, 0.2)',
    textPrimary: '#ffffff',
    textSecondary: 'rgba(255, 255, 255, 0.75)',
    bannerImageKeywords: 'laboratory,research,science,experiment'
  },

  statCards: {
    total: {
      iconBg: 'rgba(59, 130, 246, 0.15)',
      iconColor: '#3b82f6',
      valueColor: '#ffffff',
      valueShadow: '0 0 20px rgba(59, 130, 246, 0.6)'
    },
    research: {
      iconBg: 'rgba(96, 165, 250, 0.2)',
      iconColor: '#60a5fa',
      valueColor: '#60a5fa',
      valueShadow: '0 0 20px rgba(96, 165, 250, 0.6)'
    }
  },

  meta: {
    order: 3,
    enabled: true
  }
}
