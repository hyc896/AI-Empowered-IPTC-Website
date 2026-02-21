<template>
  <div class="collection-status">
    <div class="status-header">
      <h2>消息采集状况</h2>
      <div class="header-actions">
        <span class="last-update">最后更新: {{ lastUpdateTime }}</span>
        <base-button size="small" @click="refreshData" :loading="loading">
          刷新数据
        </base-button>
      </div>
    </div>

    <!-- 采集概览 -->
    <div class="overview-section">
      <div class="stat-card">
        <div class="stat-icon">📊</div>
        <div class="stat-content">
          <div class="stat-value">{{ collectionStatus.total_sources }}</div>
          <div class="stat-label">消息源总数</div>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon">✅</div>
        <div class="stat-content">
          <div class="stat-value">{{ collectionStatus.active_sources }}</div>
          <div class="stat-label">激活消息源</div>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon">📝</div>
        <div class="stat-content">
          <div class="stat-value">{{ formatNumber(collectionStatus.total_messages) }}</div>
          <div class="stat-label">消息总数</div>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon">🇨🇳</div>
        <div class="stat-content">
          <div class="stat-value">{{ formatNumber(collectionStatus.chinese_messages) }}</div>
          <div class="stat-label">中国来源消息</div>
        </div>
      </div>
    </div>

    <!-- 消息源详情 -->
    <div class="sources-section">
      <h3>消息源详情</h3>
      <div class="sources-table">
        <table>
          <thead>
            <tr>
              <th>消息源名称</th>
              <th>状态</th>
              <th>类型</th>
              <th>消息数量</th>
              <th>最近采集时间</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="source in collectionStatus.sources" :key="source.table">
              <td>{{ source.name }}</td>
              <td>
                <span :class="['status-badge', source.is_active ? 'active' : 'inactive']">
                  {{ source.is_active ? '激活' : '未激活' }}
                </span>
              </td>
              <td>
                <span :class="['type-badge', source.is_chinese ? 'chinese' : 'foreign']">
                  {{ source.is_chinese ? '🇨🇳 中国' : '🌍 国际' }}
                </span>
              </td>
              <td>{{ formatNumber(source.message_count) }}</td>
              <td>{{ formatTime(source.latest_crawled_at) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
import { getCollectionStatus } from '@/api';
import type { CollectionStatus } from '@/api/collection';
import BaseButton from '@/components/ui/BaseButton.vue';

const collectionStatus = ref<CollectionStatus>({
  total_sources: 0,
  active_sources: 0,
  total_messages: 0,
  chinese_messages: 0,
  sources: [],
  updated_at: ''
});

const loading = ref(false);
const lastUpdateTime = ref('');
let autoRefreshTimer: number | null = null;

// 格式化数字
const formatNumber = (num: number): string => {
  return num.toLocaleString();
};

// 格式化时间
const formatTime = (time: string | null): string => {
  if (!time) return '暂无数据';
  const date = new Date(time);
  return date.toLocaleString('zh-CN');
};

// 刷新数据
const refreshData = async () => {
  loading.value = true;
  try {
    collectionStatus.value = await getCollectionStatus();
    lastUpdateTime.value = new Date().toLocaleString('zh-CN');
  } catch (error) {
    console.error('刷新数据失败:', error);
  } finally {
    loading.value = false;
  }
};

// 设置自动刷新（每1小时）
const setupAutoRefresh = () => {
  // 每1小时刷新一次（1 * 60 * 60 * 1000 = 3600000ms）
  autoRefreshTimer = window.setInterval(() => {
    refreshData();
  }, 3600000);
};

// 清除自动刷新
const clearAutoRefresh = () => {
  if (autoRefreshTimer) {
    clearInterval(autoRefreshTimer);
    autoRefreshTimer = null;
  }
};

onMounted(() => {
  refreshData();
  setupAutoRefresh();
});

onUnmounted(() => {
  clearAutoRefresh();
});
</script>

<style scoped>
.collection-status {
  padding: var(--spacing-2xl);
}

.status-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-2xl);
}

.status-header h2 {
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-bold);
  color: var(--text-primary);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: var(--spacing-lg);
}

.last-update {
  color: var(--text-secondary);
  font-size: var(--font-size-sm);
}

/* 概览卡片 */
.overview-section {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--spacing-lg);
  margin-bottom: var(--spacing-3xl);
}

.stat-card {
  background: var(--bg-primary);
  border-radius: var(--border-radius-lg);
  padding: var(--spacing-xl);
  display: flex;
  align-items: center;
  gap: var(--spacing-lg);
  box-shadow: var(--shadow-light);
  transition: transform var(--transition-base);
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-medium);
}

.stat-icon {
  font-size: 2.5rem;
}

.stat-content {
  flex: 1;
}

.stat-value {
  font-size: var(--font-size-3xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-primary);
  margin-bottom: var(--spacing-xs);
}

.stat-label {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}

/* 调度器状态 */
.scheduler-section {
  background: var(--bg-primary);
  border-radius: var(--border-radius-lg);
  padding: var(--spacing-2xl);
  margin-bottom: var(--spacing-3xl);
  box-shadow: var(--shadow-light);
}

.scheduler-section h3 {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
  margin-bottom: var(--spacing-xl);
}

.scheduler-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: var(--spacing-xl);
}

.scheduler-card {
  background: var(--bg-secondary);
  border-radius: var(--border-radius-md);
  padding: var(--spacing-xl);
  transition: transform var(--transition-base);
}

.scheduler-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-medium);
}

.scheduler-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-lg);
}

.scheduler-icon {
  font-size: 2rem;
}

.scheduler-title {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
}

.scheduler-info {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.scheduler-interval {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  padding: var(--spacing-xs) var(--spacing-sm);
  background: var(--bg-tertiary);
  border-radius: var(--border-radius-sm);
  display: inline-block;
  width: fit-content;
}

.scheduler-countdown {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-md);
  background: linear-gradient(135deg, rgba(208, 48, 80, 0.1), rgba(208, 48, 80, 0.05));
  border-radius: var(--border-radius-md);
  border-left: 3px solid var(--color-primary);
}

.countdown-label {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}

.countdown-value {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-primary);
}

/* 匹配状态 */
.matching-section {
  background: var(--bg-primary);
  border-radius: var(--border-radius-lg);
  padding: var(--spacing-2xl);
  margin-bottom: var(--spacing-3xl);
  box-shadow: var(--shadow-light);
}

.matching-section h3 {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
  margin-bottom: var(--spacing-xl);
}

.progress-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: var(--spacing-xl);
  margin-bottom: var(--spacing-xl);
}

.progress-card {
  background: var(--bg-secondary);
  border-radius: var(--border-radius-md);
  padding: var(--spacing-lg);
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-md);
}

.progress-value {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-primary);
}

.progress-bar {
  height: 8px;
  background: var(--bg-tertiary);
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: var(--spacing-sm);
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--color-primary), var(--color-primary-dark));
  transition: width 0.3s ease;
}

.progress-fill.generation {
  background: linear-gradient(90deg, #10b981, #059669);
}

.progress-detail {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}

.cases-summary {
  display: flex;
  gap: var(--spacing-2xl);
  padding-top: var(--spacing-lg);
  border-top: 1px solid var(--border-color);
}

.summary-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.summary-label {
  color: var(--text-secondary);
}

.summary-value {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-primary);
}

/* 消息源表格 */
.sources-section {
  background: var(--bg-primary);
  border-radius: var(--border-radius-lg);
  padding: var(--spacing-2xl);
  box-shadow: var(--shadow-light);
}

.sources-section h3 {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
  margin-bottom: var(--spacing-xl);
}

.sources-table {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
}

thead {
  background: var(--bg-secondary);
}

th {
  padding: var(--spacing-md);
  text-align: left;
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
  border-bottom: 2px solid var(--border-color);
}

td {
  padding: var(--spacing-md);
  border-bottom: 1px solid var(--border-color);
  color: var(--text-secondary);
}

tbody tr:hover {
  background: var(--bg-secondary);
}

.status-badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-medium);
}

.status-badge.active {
  background: #d1fae5;
  color: #065f46;
}

.status-badge.inactive {
  background: #fee2e2;
  color: #991b1b;
}

.type-badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-medium);
}

.type-badge.chinese {
  background: #dbeafe;
  color: #1e40af;
}

.type-badge.foreign {
  background: #e0e7ff;
  color: #4338ca;
}

@media (max-width: 768px) {
  .collection-status {
    padding: var(--spacing-lg);
  }

  .status-header {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--spacing-md);
  }

  .overview-section {
    grid-template-columns: 1fr;
  }

  .progress-cards {
    grid-template-columns: 1fr;
  }

  .sources-table {
    font-size: var(--font-size-sm);
  }
}
</style>
