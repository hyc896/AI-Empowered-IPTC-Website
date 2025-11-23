<template>
  <div class="report-view" :style="rootStyle" ref="exportRef">
    <!-- 星空背景层 -->
    <div class="starfield">
      <div class="stars"></div>
      <div class="stars"></div>
      <div class="stars"></div>
    </div>

    <!-- AI风格顶部横幅 -->
    <div class="ai-banner" :style="bannerStyle">
      <!-- 粒子背景 -->
      <div class="banner-particles"></div>

      <!-- 扫描线 -->
      <div class="scan-line" :style="scanLineStyle"></div>

      <!-- 网格背景 -->
      <div class="grid-bg" :style="gridStyle"></div>

      <div class="banner-content">
        <!-- 3D神经网络图标 -->
        <div class="banner-icon">
          <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
            <!-- 神经网络节点 -->
            <circle cx="50" cy="20" r="4" :fill="theme.primary" class="node node-1">
              <animate attributeName="opacity" values="0.3;1;0.3" dur="2s" repeatCount="indefinite"/>
            </circle>
            <circle cx="30" cy="50" r="4" :fill="theme.primary" class="node node-2">
              <animate attributeName="opacity" values="0.3;1;0.3" dur="2.5s" repeatCount="indefinite"/>
            </circle>
            <circle cx="50" cy="50" r="6" :fill="theme.secondary" class="node node-3">
              <animate attributeName="opacity" values="0.5;1;0.5" dur="2s" repeatCount="indefinite"/>
            </circle>
            <circle cx="70" cy="50" r="4" :fill="theme.primary" class="node node-4">
              <animate attributeName="opacity" values="0.3;1;0.3" dur="3s" repeatCount="indefinite"/>
            </circle>
            <circle cx="50" cy="80" r="4" :fill="theme.primary" class="node node-5">
              <animate attributeName="opacity" values="0.3;1;0.3" dur="2.2s" repeatCount="indefinite"/>
            </circle>

            <!-- 连接线 -->
            <line x1="50" y1="20" x2="30" y2="50" :stroke="theme.primary" stroke-width="1" opacity="0.6"/>
            <line x1="50" y1="20" x2="50" y2="50" :stroke="theme.primary" stroke-width="1.5" opacity="0.8"/>
            <line x1="50" y1="20" x2="70" y2="50" :stroke="theme.primary" stroke-width="1" opacity="0.6"/>
            <line x1="30" y1="50" x2="50" y2="80" :stroke="theme.primary" stroke-width="1" opacity="0.6"/>
            <line x1="50" y1="50" x2="50" y2="80" :stroke="theme.primary" stroke-width="1.5" opacity="0.8"/>
            <line x1="70" y1="50" x2="50" y2="80" :stroke="theme.primary" stroke-width="1" opacity="0.6"/>
          </svg>

          <!-- 脉冲光环 -->
          <div class="pulse-ring" :style="pulseRingStyle"></div>
          <div class="pulse-ring" :style="pulseRingStyle"></div>
        </div>

        <!-- 标题信息 -->
        <div class="banner-info">
          <h1 class="banner-title">{{ config.name.toUpperCase() }} INTELLIGENCE REPORT</h1>
          <div class="banner-subtitle">{{ config.description }}</div>

          <div class="banner-meta">
            <div class="meta-item" :style="metaItemStyle">
              <div class="meta-icon" :style="{ color: theme.primary }">
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                  <rect x="2" y="3" width="12" height="11" rx="1" stroke="currentColor" stroke-width="1.5"/>
                  <path d="M2 6h12M5 1v2M11 1v2" stroke="currentColor" stroke-width="1.5"/>
                </svg>
              </div>
              <span class="meta-label">GENERATED</span>
              <span class="meta-value">{{ formatDateTime(report.generated_at) }}</span>
            </div>
            <div class="meta-item" :style="metaItemStyle">
              <div class="meta-icon" :style="{ color: theme.primary }">
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                  <circle cx="8" cy="8" r="6" stroke="currentColor" stroke-width="1.5"/>
                  <path d="M8 4v4l3 2" stroke="currentColor" stroke-width="1.5"/>
                </svg>
              </div>
              <span class="meta-label">DATA SOURCE</span>
              <span class="meta-value">{{ getDataSourceTimeRange(report.generated_at) }}</span>
            </div>
          </div>
        </div>

        <!-- 状态指示器 -->
        <div class="banner-status">
          <div class="status-indicator" :style="statusIndicatorStyle">
            <div class="status-dot" :style="{ background: theme.primary }"></div>
            <span>SYSTEM ACTIVE</span>
          </div>
          <div class="status-code">{{ report.report_date }}</div>
        </div>
      </div>

      <!-- 数据流边框 -->
      <div class="data-flow-border top" :style="borderFlowStyle"></div>
      <div class="data-flow-border bottom" :style="borderFlowStyle"></div>
    </div>

    <!-- 统计信息卡片 -->
    <div class="report-stats">
      <div
        v-for="card in statCards"
        :key="card.key"
        class="stat-card"
        :style="getStatCardStyle(card.key)"
      >
        <div class="card-glow" :style="{ background: `radial-gradient(circle at 50% 0%, ${theme.glowColor}, transparent 70%)` }"></div>
        <div class="stat-icon" :style="card.iconStyle">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
            <path :d="card.iconPath" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
          </svg>
        </div>
        <div class="stat-label">{{ card.label }}</div>
        <div class="stat-value" :style="card.valueStyle">{{ card.value }}</div>
        <div class="stat-bar">
          <div class="stat-bar-fill" :style="{ width: card.percentage, ...card.barStyle }"></div>
        </div>
      </div>
    </div>

    <!-- 日期选择器 - 玻璃风格 -->
    <div class="date-selector-container" :style="selectorStyle">
      <div class="selector-label">REPORT DATE</div>
      <div class="selector-info">{{ formatReportDate(report.report_date) }}</div>
      <div class="selector-badge" :style="badgeStyle">
        <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
          <rect x="2" y="3" width="12" height="11" rx="1" stroke="currentColor" stroke-width="1.5"/>
          <path d="M2 6h12M5 1v2M11 1v2" stroke="currentColor" stroke-width="1.5"/>
        </svg>
        <span>{{ report.report_date }}</span>
      </div>
    </div>

    <!-- Markdown内容 -->
    <div class="report-content" :style="contentStyle">
      <!-- 数据流装饰 -->
      <div class="data-stream left" :style="dataStreamStyle"></div>
      <div class="content-glow" :style="{ background: `radial-gradient(ellipse at top, ${theme.glowColor.replace('0.3', '0.05')}, transparent)` }"></div>

      <MarkdownRenderer :content="report.content" />

      <!-- 底部扫描线 -->
      <div class="bottom-scan-line" :style="scanLineStyle"></div>
    </div>

    <!-- 元信息 -->
    <div class="report-meta" :style="metaStyle">
      <div class="meta-grid">
        <div class="meta-cell">
          <span class="meta-key">GENERATED</span>
          <span class="meta-val">{{ formatDateTime(report.generated_at) }}</span>
        </div>
        <div class="meta-cell">
          <span class="meta-key">MODEL</span>
          <span class="meta-val">{{ report.model_version }}</span>
        </div>
        <div class="meta-cell">
          <span class="meta-key">STATUS</span>
          <span class="meta-val status-active" :style="{ color: theme.primary }">
            <span class="status-dot" :style="{ background: theme.primary }"></span>
            已完成
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { ReportTypeConfig } from './types'
import type { AIDailyReport } from '@/api/aiReport'
import MarkdownRenderer from '@/components/common/MarkdownRenderer.vue'

const props = defineProps<{
  config: ReportTypeConfig
  report: AIDailyReport
}>()

const exportRef = ref<HTMLElement | null>(null)
const theme = computed(() => props.config.theme)

// 根元素样式
const rootStyle = computed(() => ({
  background: theme.value.bgGradient,
  '--theme-primary': theme.value.primary,
  '--theme-secondary': theme.value.secondary,
  '--theme-accent': theme.value.accent,
  '--theme-glow': theme.value.glowColor,
  '--theme-border': theme.value.borderColor
}))

// Banner样式
const bannerStyle = computed(() => ({
  background: theme.value.bannerGradient
}))

// 扫描线样式
const scanLineStyle = computed(() => ({
  background: `linear-gradient(90deg, transparent, ${theme.value.primary}, transparent)`,
  boxShadow: `0 0 10px ${theme.value.primary}`
}))

// 网格样式
const gridStyle = computed(() => ({
  backgroundImage: `
    linear-gradient(${theme.value.borderColor} 1px, transparent 1px),
    linear-gradient(90deg, ${theme.value.borderColor} 1px, transparent 1px)
  `
}))

// 脉冲光环样式
const pulseRingStyle = computed(() => ({
  border: `2px solid ${theme.value.borderColor.replace('0.2', '0.3')}`
}))

// Meta项样式
const metaItemStyle = computed(() => ({
  background: theme.value.borderColor.replace('0.2', '0.05'),
  borderColor: theme.value.borderColor
}))

// 状态指示器样式
const statusIndicatorStyle = computed(() => ({
  background: theme.value.glowColor.replace('0.3', '0.1'),
  borderColor: theme.value.borderColor.replace('0.2', '0.3'),
  color: theme.value.primary
}))

// 边框流动样式
const borderFlowStyle = computed(() => ({
  background: `linear-gradient(90deg,
    transparent,
    ${theme.value.borderColor.replace('0.2', '0.5')} 20%,
    ${theme.value.primary}40 50%,
    ${theme.value.borderColor.replace('0.2', '0.5')} 80%,
    transparent
  )`
}))

// 数据流样式
const dataStreamStyle = computed(() => ({
  background: `linear-gradient(180deg, transparent, ${theme.value.borderColor.replace('0.2', '0.3')}, transparent)`
}))

// 选择器样式
const selectorStyle = computed(() => ({
  background: theme.value.borderColor.replace('0.2', '0.03'),
  borderBottomColor: theme.value.borderColor
}))

// 日期徽章样式
const badgeStyle = computed(() => ({
  background: theme.value.glowColor.replace('0.3', '0.15'),
  borderColor: theme.value.borderColor,
  color: theme.value.primary
}))

// 内容区样式
const contentStyle = computed(() => ({
  '--theme-h1-border': theme.value.primary,
  '--theme-h2-border': theme.value.secondary,
  '--theme-h3-border': theme.value.borderColor.replace('0.2', '0.6'),
  '--theme-code-bg': theme.value.glowColor.replace('0.3', '0.15'),
  '--theme-code-color': theme.value.primary,
  '--theme-link-color': theme.value.primary,
  '--theme-link-hover': theme.value.secondary
}))

// Meta区样式
const metaStyle = computed(() => ({
  borderTopColor: theme.value.borderColor
}))

// 统计卡片数据
const statCards = computed(() => {
  const cards = []
  const total = props.report.total_messages

  // Total卡片
  if (props.config.statCards.total) {
    cards.push({
      key: 'total',
      label: 'TOTAL MESSAGES',
      value: total,
      percentage: '100%',
      iconPath: 'M9 2L3 8l6 6M15 2l6 6-6 6M12 12v10',
      iconStyle: props.config.statCards.total,
      valueStyle: {
        color: props.config.statCards.total.valueColor,
        textShadow: props.config.statCards.total.valueShadow
      },
      barStyle: {
        background: `linear-gradient(90deg, ${theme.value.primary}, ${theme.value.secondary})`
      }
    })
  }

  // Governance卡片
  if (props.config.statCards.governance) {
    const count = props.report.governance_count
    cards.push({
      key: 'governance',
      label: 'AI GOVERNANCE',
      value: count,
      percentage: total > 0 ? `${Math.round((count / total) * 100)}%` : '0%',
      iconPath: 'M3 3h18v18H3zM9 12l2 2 4-4',
      iconStyle: props.config.statCards.governance,
      valueStyle: {
        color: props.config.statCards.governance.valueColor,
        textShadow: props.config.statCards.governance.valueShadow
      },
      barStyle: {
        background: props.config.statCards.governance.iconColor
      }
    })
  }

  // Research卡片
  if (props.config.statCards.research) {
    const count = props.report.research_count
    cards.push({
      key: 'research',
      label: 'AI RESEARCH',
      value: count,
      percentage: total > 0 ? `${Math.round((count / total) * 100)}%` : '0%',
      iconPath: 'M12 12m-9 0a9 9 0 1 0 18 0a9 9 0 1 0 -18 0M12 6v6l4 2',
      iconStyle: props.config.statCards.research,
      valueStyle: {
        color: props.config.statCards.research.valueColor,
        textShadow: props.config.statCards.research.valueShadow
      },
      barStyle: {
        background: props.config.statCards.research.iconColor
      }
    })
  }

  // Industry卡片
  if (props.config.statCards.industry) {
    const count = props.report.industry_count
    cards.push({
      key: 'industry',
      label: 'AI INDUSTRY',
      value: count,
      percentage: total > 0 ? `${Math.round((count / total) * 100)}%` : '0%',
      iconPath: 'M2 20h20M4 20V10l6-6 6 6v10M10 12h4',
      iconStyle: props.config.statCards.industry,
      valueStyle: {
        color: props.config.statCards.industry.valueColor,
        textShadow: props.config.statCards.industry.valueShadow
      },
      barStyle: {
        background: props.config.statCards.industry.iconColor
      }
    })
  }

  return cards
})

// 获取统计卡片样式
const getStatCardStyle = (key: string) => {
  return {
    borderColor: theme.value.borderColor
  }
}

// 格式化日期时间
const formatDateTime = (dateStr: string): string => {
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// 格式化报告日期（长格式）
const formatReportDate = (dateStr: string): string => {
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    weekday: 'long'
  })
}

// 获取数据源时间范围
const getDataSourceTimeRange = (generatedAtStr: string): string => {
  const generatedAt = new Date(generatedAtStr)
  const endTime = new Date(generatedAt)
  const startTime = new Date(generatedAt.getTime() - 24 * 60 * 60 * 1000)

  const formatOptions: Intl.DateTimeFormatOptions = {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  }

  const start = startTime.toLocaleString('zh-CN', formatOptions).replace(/\//g, '-')
  const end = endTime.toLocaleString('zh-CN', formatOptions).replace(/\//g, '-')

  return `${start} ~ ${end}`
}

// 暴露导出引用（用于长图下载）
defineExpose({
  exportRef
})
</script>

<style scoped lang="scss">
.report-view {
  position: relative;
  min-height: 100%;
  overflow-y: auto;
  color: var(--theme-primary);

  &::-webkit-scrollbar {
    width: 8px;
  }

  &::-webkit-scrollbar-track {
    background: rgba(10, 14, 39, 0.5);
  }

  &::-webkit-scrollbar-thumb {
    background: var(--theme-glow);
    border-radius: 4px;

    &:hover {
      background: var(--theme-border);
    }
  }
}

.starfield {
  position: absolute;
  inset: 0;
  overflow: hidden;
  pointer-events: none;

  .stars {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background-image:
      radial-gradient(2px 2px at 20px 30px, #ffffff, transparent),
      radial-gradient(2px 2px at 60px 70px, #ffffff, transparent),
      radial-gradient(1px 1px at 50px 50px, #ffffff, transparent),
      radial-gradient(1px 1px at 130px 80px, #ffffff, transparent),
      radial-gradient(2px 2px at 90px 10px, #ffffff, transparent);
    background-size: 200px 200px;
    background-repeat: repeat;
    opacity: 0.5;
    animation: twinkle 3s ease-in-out infinite;

    &:nth-child(2) {
      background-image:
        radial-gradient(1px 1px at 40px 60px, var(--theme-primary), transparent),
        radial-gradient(2px 2px at 110px 90px, var(--theme-primary), transparent);
      animation-duration: 4s;
      animation-delay: 1s;
    }

    &:nth-child(3) {
      background-image:
        radial-gradient(1px 1px at 80px 10px, var(--theme-secondary), transparent),
        radial-gradient(2px 2px at 150px 60px, var(--theme-secondary), transparent);
      animation-duration: 5s;
      animation-delay: 2s;
    }
  }
}

.ai-banner {
  position: relative;
  padding: 60px 40px;
  overflow: hidden;
  border-bottom: 1px solid var(--theme-border);
  min-height: 280px;

  .banner-particles {
    position: absolute;
    inset: 0;
    background-image:
      radial-gradient(circle at 10% 20%, var(--theme-glow), transparent 50%),
      radial-gradient(circle at 90% 80%, var(--theme-glow), transparent 50%);
    animation: particles-float 20s ease-in-out infinite;
  }

  .scan-line {
    position: absolute;
    left: 0;
    right: 0;
    height: 2px;
    animation: scan 4s linear infinite;
    opacity: 0.6;
  }

  .grid-bg {
    position: absolute;
    inset: 0;
    background-size: 50px 50px;
    opacity: 0.2;
  }

  .banner-content {
    position: relative;
    display: flex;
    align-items: flex-start;
    gap: 32px;
    z-index: 1;
  }

  .banner-icon {
    position: relative;
    width: 100px;
    height: 100px;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;

    svg {
      width: 80%;
      height: 80%;
      filter: drop-shadow(0 0 20px var(--theme-glow));
      animation: float-3d 4s ease-in-out infinite;
    }

    .pulse-ring {
      position: absolute;
      inset: 0;
      border-radius: 50%;
      animation: pulse-ring 3s cubic-bezier(0, 0, 0.2, 1) infinite;

      &:nth-child(3) {
        animation-delay: 1.5s;
      }
    }
  }

  .banner-info {
    flex: 1;
    color: white;

    .banner-title {
      margin: 0 0 8px 0;
      font-size: 32px;
      font-weight: 800;
      letter-spacing: 3px;
      background: linear-gradient(135deg, #ffffff 0%, var(--theme-primary) 50%, var(--theme-secondary) 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
      filter: drop-shadow(0 0 20px var(--theme-glow));
    }

    .banner-subtitle {
      margin: 0 0 24px 0;
      font-size: 14px;
      color: rgba(255, 255, 255, 0.7);
      letter-spacing: 2px;
    }

    .banner-meta {
      display: flex;
      flex-direction: column;
      gap: 12px;

      .meta-item {
        display: flex;
        align-items: center;
        gap: 12px;
        font-size: 13px;
        padding: 10px 16px;
        border-radius: 8px;
        border: 1px solid;
        backdrop-filter: blur(10px);
        transition: all 0.3s;

        &:hover {
          transform: translateX(4px);
        }

        .meta-label {
          font-weight: 600;
          color: rgba(255, 255, 255, 0.6);
          letter-spacing: 1px;
          font-size: 11px;
        }

        .meta-value {
          font-weight: 600;
          color: #ffffff;
          font-family: 'Courier New', monospace;
          font-size: 13px;
        }
      }
    }
  }

  .banner-status {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 16px;

    .status-indicator {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px 16px;
      border: 1px solid;
      border-radius: 20px;
      font-size: 12px;
      font-weight: 600;
      letter-spacing: 1px;

      .status-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        animation: pulse-dot 2s ease-in-out infinite;
      }
    }

    .status-code {
      font-family: 'Courier New', monospace;
      font-size: 14px;
      color: rgba(255, 255, 255, 0.5);
      letter-spacing: 2px;
    }
  }

  .data-flow-border {
    position: absolute;
    left: 0;
    right: 0;
    height: 1px;

    &.top {
      top: 0;
    }

    &.bottom {
      bottom: 0;
    }
  }
}

.report-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
  padding: 30px 20px;
  background: transparent;

  .stat-card {
    position: relative;
    background: rgba(255, 255, 255, 0.05);
    backdrop-filter: blur(20px) saturate(180%);
    border: 1px solid;
    border-radius: 16px;
    padding: 24px 20px;
    text-align: center;
    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    overflow: hidden;

    &:hover {
      transform: perspective(1000px) rotateY(5deg) translateY(-8px);
      box-shadow: 0 20px 40px var(--theme-glow);

      .card-glow {
        opacity: 1;
      }
    }

    .card-glow {
      position: absolute;
      inset: 0;
      opacity: 0;
      transition: opacity 0.4s;
    }

    .stat-icon {
      width: 48px;
      height: 48px;
      margin: 0 auto 16px;
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: 12px;

      svg {
        width: 24px;
        height: 24px;
      }
    }

    .stat-label {
      font-size: 11px;
      font-weight: 600;
      letter-spacing: 1.5px;
      color: rgba(255, 255, 255, 0.6);
      margin-bottom: 12px;
    }

    .stat-value {
      font-size: 36px;
      font-weight: 800;
      font-family: 'Courier New', monospace;
      margin-bottom: 12px;
    }

    .stat-bar {
      width: 100%;
      height: 4px;
      background: rgba(255, 255, 255, 0.1);
      border-radius: 2px;
      overflow: hidden;

      .stat-bar-fill {
        height: 100%;
        border-radius: 2px;
        transition: width 1s ease-out;
        animation: shimmer 2s infinite;
      }
    }
  }
}

.date-selector-container {
  padding: 24px 40px;
  display: flex;
  align-items: center;
  gap: 24px;
  border-bottom: 1px solid;
  backdrop-filter: blur(10px);
  transition: all 0.3s;

  &:hover {
    background: rgba(255, 255, 255, 0.02);
  }

  .selector-label {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 2px;
    color: rgba(255, 255, 255, 0.5);
    text-transform: uppercase;
  }

  .selector-info {
    flex: 1;
    font-size: 16px;
    color: #ffffff;
    font-weight: 600;
    letter-spacing: 0.5px;
  }

  .selector-badge {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 16px;
    border-radius: 20px;
    border: 1px solid;
    backdrop-filter: blur(10px);
    font-size: 12px;
    font-weight: 600;
    font-family: 'Courier New', monospace;
    letter-spacing: 1px;
    transition: all 0.3s;

    svg {
      width: 14px;
      height: 14px;
    }

    &:hover {
      transform: translateY(-2px);
      box-shadow: 0 4px 12px var(--theme-glow);
    }
  }
}

.report-content {
  position: relative;
  padding: 40px;
  background: rgba(255, 255, 255, 0.03);
  font-size: 16px;
  line-height: 1.9;
  color: #ffffff;

  .data-stream {
    position: absolute;
    top: 0;
    bottom: 0;
    width: 1px;

    &.left {
      left: 20px;
    }
  }

  .content-glow {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 200px;
    pointer-events: none;
  }

  .bottom-scan-line {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    height: 1px;
    animation: scan-horizontal 3s linear infinite;
  }

  :deep(.markdown-content) {
    color: #ffffff !important;

    p, li, td, th, span, div {
      color: #ffffff !important;
    }
  }

  :deep(h1) {
    position: relative;
    color: #ffffff;
    font-weight: 800;
    font-size: 28px;
    padding: 20px 0 20px 24px;
    margin: 32px 0 20px 0;
    border-left: 4px solid var(--theme-h1-border);
    border-top: 1px solid var(--theme-border);
    border-bottom: 1px solid var(--theme-border);
    background: linear-gradient(90deg, var(--theme-glow), transparent);
    box-shadow: -4px 0 12px var(--theme-glow);
  }

  :deep(h2) {
    position: relative;
    color: #ffffff;
    font-weight: 700;
    font-size: 22px;
    padding: 16px 0 16px 20px;
    margin: 28px 0 16px 0;
    border-left: 3px solid var(--theme-h2-border);
    border-bottom: 1px dashed var(--theme-border);
    background: linear-gradient(90deg, var(--theme-glow), transparent 80%);
  }

  :deep(h3) {
    position: relative;
    color: #ffffff;
    font-weight: 600;
    font-size: 18px;
    padding: 12px 0 12px 16px;
    margin: 24px 0 12px 0;
    border-left: 2px solid var(--theme-h3-border);
    background: rgba(255, 255, 255, 0.02);
  }

  :deep(a) {
    color: var(--theme-link-color);
    text-decoration: none;
    transition: all 0.3s;
    font-weight: 500;

    &:hover {
      color: var(--theme-link-hover);
      text-shadow: 0 0 10px var(--theme-glow);
    }
  }

  :deep(code) {
    background: var(--theme-code-bg);
    color: var(--theme-code-color);
    padding: 3px 8px;
    border-radius: 4px;
    font-family: 'Courier New', monospace;
    font-size: 0.95em;
  }
}

.report-meta {
  padding: 24px 40px;
  background: rgba(255, 255, 255, 0.02);
  border-top: 1px solid;

  .meta-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 24px;

    .meta-cell {
      display: flex;
      flex-direction: column;
      gap: 8px;

      .meta-key {
        font-size: 10px;
        font-weight: 600;
        letter-spacing: 1.5px;
        color: rgba(255, 255, 255, 0.5);
      }

      .meta-val {
        font-size: 13px;
        color: #ffffff;
        font-family: 'Courier New', monospace;

        &.status-active {
          display: flex;
          align-items: center;
          gap: 6px;

          .status-dot {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            animation: pulse-dot 2s ease-in-out infinite;
          }
        }
      }
    }
  }
}

@keyframes twinkle {
  0%, 100% {
    opacity: 0.3;
  }
  50% {
    opacity: 0.8;
  }
}

@keyframes particles-float {
  0%, 100% {
    transform: translate(0, 0);
  }
  33% {
    transform: translate(20px, -20px);
  }
  66% {
    transform: translate(-20px, 20px);
  }
}

@keyframes scan {
  0% {
    top: 0;
  }
  100% {
    top: 100%;
  }
}

@keyframes float-3d {
  0%, 100% {
    transform: translateY(0) rotate(0deg);
  }
  50% {
    transform: translateY(-10px) rotate(5deg);
  }
}

@keyframes pulse-ring {
  0% {
    transform: scale(1);
    opacity: 0.8;
  }
  100% {
    transform: scale(1.5);
    opacity: 0;
  }
}

@keyframes pulse-dot {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.5;
    transform: scale(1.2);
  }
}

@keyframes shimmer {
  0% {
    background-position: -100% 0;
  }
  100% {
    background-position: 200% 0;
  }
}

@keyframes scan-horizontal {
  0% {
    transform: translateX(-100%);
  }
  100% {
    transform: translateX(100%);
  }
}
</style>
