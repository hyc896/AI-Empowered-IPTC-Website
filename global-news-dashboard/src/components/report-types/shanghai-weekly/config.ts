/**
 * 上海周报配置
 * 主题：蓝色都市风 - 现代科技蓝与都市灰，国际化、现代感
 */

import type { ReportTypeConfig } from '../types'

export const shanghaiWeeklyConfig: ReportTypeConfig = {
  type: 'shanghai_weekly',
  name: '上海周报',
  icon: '🏙️',
  description: '聚焦上海区域的科技创新、产业发展与政策动态周度汇总',

  theme: {
    primary: '#0ea5e9',
    secondary: '#38bdf8',
    accent: '#7dd3fc',
    bgGradient: 'linear-gradient(180deg, #0c4a6e 0%, #075985 50%, #0369a1 100%)',
    bannerGradient: 'linear-gradient(135deg, rgba(12, 74, 110, 0.85) 0%, rgba(3, 105, 161, 0.85) 50%, rgba(14, 165, 233, 0.7) 100%)',
    glowColor: 'rgba(14, 165, 233, 0.4)',
    borderColor: 'rgba(56, 189, 248, 0.3)',
    textPrimary: '#ffffff',
    textSecondary: 'rgba(255, 255, 255, 0.8)',
    bannerImageKeywords: 'shanghai,pudong,oriental-pearl,modern-city'
  },

  statCards: {
    total: {
      iconBg: 'rgba(14, 165, 233, 0.2)',
      iconColor: '#0ea5e9',
      valueColor: '#7dd3fc',
      valueShadow: '0 0 20px rgba(14, 165, 233, 0.6)'
    },
    governance: {
      iconBg: 'rgba(56, 189, 248, 0.2)',
      iconColor: '#38bdf8',
      valueColor: '#7dd3fc',
      valueShadow: '0 0 20px rgba(56, 189, 248, 0.6)'
    },
    research: {
      iconBg: 'rgba(125, 211, 252, 0.2)',
      iconColor: '#7dd3fc',
      valueColor: '#bae6fd',
      valueShadow: '0 0 20px rgba(125, 211, 252, 0.6)'
    },
    industry: {
      iconBg: 'rgba(2, 132, 199, 0.2)',
      iconColor: '#0284c7',
      valueColor: '#38bdf8',
      valueShadow: '0 0 20px rgba(2, 132, 199, 0.6)'
    }
  },

  meta: {
    order: 6,
    enabled: true
  }
}
