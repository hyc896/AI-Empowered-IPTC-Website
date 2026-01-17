<template>
  <div class="cases-view">
    <div class="container">
      <!-- 英雄区域 - 革命标题 -->
      <div class="hero-section">
        <div class="hero-content">
          <h1 class="hero-title">
            <span class="title-line">思想政治理论课</span>
            <span class="title-highlight">教学案例库</span>
          </h1>
          <p class="hero-subtitle">传承红色基因 · 铸就时代新人</p>
          <div class="hero-stats">
            <div class="stat-item">
              <div class="stat-number">{{ caseStore.total }}</div>
              <div class="stat-label">案例总数</div>
            </div>
            <div class="stat-divider"></div>
            <div class="stat-item">
              <div class="stat-number">{{ knowledgePointCount }}</div>
              <div class="stat-label">知识点</div>
            </div>
            <div class="stat-divider"></div>
            <div class="stat-item">
              <div class="stat-number">{{ lastUpdateTime }}</div>
              <div class="stat-label">最近更新</div>
            </div>
          </div>
        </div>
      </div>

      <!-- 搜索区 -->
      <div class="search-section">
        <div class="search-bar">
          <div class="search-icon">🔍</div>
          <input
            v-model="keyword"
            type="text"
            placeholder="搜索革命精神、时代楷模、理论要点..."
            class="search-input"
            @keyup.enter="handleSearch"
          />
          <button class="search-button" @click="handleSearch">
            <span>搜索</span>
            <div class="button-shine"></div>
          </button>
        </div>

        <!-- 筛选器 -->
        <div class="filters-section" v-if="selectedKnowledgePoints.length > 0">
          <div class="filter-label">已选知识点：</div>
          <div class="filter-tags">
            <span
              v-for="kp in selectedKnowledgePoints"
              :key="kp"
              class="filter-tag"
              @click="removeKnowledgePoint(kp)"
            >
              {{ kp }}
              <span class="tag-close">×</span>
            </span>
          </div>
        </div>
      </div>

      <!-- 加载状态 -->
      <div v-if="caseStore.loading" class="loading-section">
        <div class="loading-animation">
          <div class="flag-wave"></div>
          <div class="loading-text">加载中...</div>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-else-if="caseStore.isEmpty" class="empty-state">
        <div class="empty-icon">📚</div>
        <div class="empty-title">暂无案例</div>
        <div class="empty-description">尝试调整搜索条件或稍后再来</div>
      </div>

      <!-- 案例网格 -->
      <div v-else class="cases-grid">
        <div
          v-for="(caseItem, index) in caseStore.cases"
          :key="caseItem.id"
          class="case-card"
          :style="{ animationDelay: `${index * 0.05}s` }"
          @click="navigateToDetail(caseItem.id)"
        >
          <!-- 红色装饰条 -->
          <div class="card-accent"></div>

          <!-- 知识点标签 -->
          <div class="case-tags">
            <span
              v-for="kp in caseItem.knowledgePoints.slice(0, 2)"
              :key="kp"
              class="case-tag"
            >
              {{ kp }}
            </span>
          </div>

          <!-- 案例内容 -->
          <h3 class="case-title">{{ caseItem.title }}</h3>
          <p class="case-summary">{{ caseItem.summary }}</p>

          <!-- 底部元信息 -->
          <div class="case-footer">
            <div class="case-date">
              <span class="date-icon">📅</span>
              {{ formatDate(caseItem.publishDate) }}
            </div>
            <div class="case-arrow">→</div>
          </div>

          <!-- 悬停光效 -->
          <div class="card-glow"></div>
        </div>
      </div>

      <!-- 分页 -->
      <div v-if="!caseStore.isEmpty" class="pagination">
        <button
          class="pagination-button"
          :disabled="caseStore.searchParams.page === 1"
          @click="prevPage"
        >
          <span>← 上一页</span>
        </button>
        <div class="page-info">
          <span class="current-page">{{ caseStore.searchParams.page }}</span>
          <span class="page-separator">/</span>
          <span class="total-pages">{{ caseStore.totalPages }}</span>
        </div>
        <button
          class="pagination-button"
          :disabled="!caseStore.hasMore"
          @click="nextPage"
        >
          <span>下一页 →</span>
        </button>
      </div>

      <!-- 自动刷新指示器 -->
      <div class="refresh-indicator">
        <div class="refresh-icon">🔄</div>
        <div class="refresh-text">每小时自动更新</div>
        <div class="refresh-progress" :style="{ width: `${refreshProgress}%` }"></div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue';
import { useRouter } from 'vue-router';
import { useCaseStore } from '@/stores';
import { formatDate } from '@/utils';

const router = useRouter();
const caseStore = useCaseStore();

const keyword = ref('');
const selectedKnowledgePoints = ref<string[]>([]);
const refreshProgress = ref(0);
const knowledgePointCount = ref(61);
const lastUpdateTime = ref('刚刚');

let refreshInterval: number | null = null;
let progressInterval: number | null = null;

onMounted(() => {
  caseStore.fetchCases();
  startAutoRefresh();
  startProgressAnimation();
  updateLastUpdateTime();
});

onUnmounted(() => {
  stopAutoRefresh();
  stopProgressAnimation();
});

const handleSearch = () => {
  caseStore.search(keyword.value);
};

const removeKnowledgePoint = (kp: string) => {
  selectedKnowledgePoints.value = selectedKnowledgePoints.value.filter((k) => k !== kp);
  caseStore.updateFilters({ knowledgePoints: selectedKnowledgePoints.value });
};

const navigateToDetail = (id: string) => {
  router.push(`/cases/${id}`);
};

const prevPage = () => {
  if (caseStore.searchParams.page > 1) {
    caseStore.changePage(caseStore.searchParams.page - 1);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }
};

const nextPage = () => {
  if (caseStore.hasMore) {
    caseStore.changePage(caseStore.searchParams.page + 1);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }
};

// 自动刷新功能
const startAutoRefresh = () => {
  refreshInterval = window.setInterval(() => {
    caseStore.fetchCases();
    updateLastUpdateTime();
    refreshProgress.value = 0;
  }, 3600000); // 每小时刷新一次
};

const stopAutoRefresh = () => {
  if (refreshInterval) {
    clearInterval(refreshInterval);
  }
};

// 进度条动画
const startProgressAnimation = () => {
  progressInterval = window.setInterval(() => {
    refreshProgress.value = (refreshProgress.value + 0.028) % 100;
  }, 1000); // 每秒更新进度
};

const stopProgressAnimation = () => {
  if (progressInterval) {
    clearInterval(progressInterval);
  }
};

// 更新最后更新时间
const updateLastUpdateTime = () => {
  const now = new Date();
  const hours = now.getHours().toString().padStart(2, '0');
  const minutes = now.getMinutes().toString().padStart(2, '0');
  lastUpdateTime.value = `${hours}:${minutes}`;
};
</script>

<style scoped>
/* ========== 全局容器 ========== */
.cases-view {
  min-height: 100vh;
  position: relative;
  overflow-x: hidden;
}

.container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 80px 24px 60px;
  position: relative;
}

/* ========== 英雄区域 ========== */
.hero-section {
  text-align: center;
  margin-bottom: 60px;
  animation: heroFadeIn 1s ease-out;
}

@keyframes heroFadeIn {
  from {
    opacity: 0;
    transform: translateY(-30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.hero-content {
  padding: 60px 40px;
}

.hero-title {
  font-size: 56px;
  font-weight: 900;
  color: #ffffff;
  margin-bottom: 20px;
  text-shadow:
    2px 2px 4px rgba(0, 0, 0, 0.5),
    0 0 20px rgba(255, 215, 0, 0.6);
  line-height: 1.2;
}

.title-line {
  display: block;
  font-size: 36px;
  letter-spacing: 8px;
}

.title-highlight {
  display: block;
  color: #FFD700;
}

.hero-subtitle {
  font-size: 24px;
  color: rgba(255, 255, 255, 0.95);
  margin-bottom: 40px;
  letter-spacing: 4px;
  text-shadow: 1px 1px 3px rgba(0, 0, 0, 0.5);
}

.hero-stats {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 40px;
  flex-wrap: wrap;
}

.stat-item {
  text-align: center;
}

.stat-number {
  font-size: 48px;
  font-weight: 800;
  color: #FFD700;
  text-shadow: 0 0 15px rgba(255, 215, 0, 0.8);
  margin-bottom: 8px;
}

.stat-label {
  font-size: 16px;
  color: rgba(255, 255, 255, 0.85);
  letter-spacing: 2px;
}

.stat-divider {
  width: 2px;
  height: 60px;
  background: linear-gradient(to bottom, transparent, rgba(255, 215, 0, 0.5), transparent);
}

/* ========== 搜索区域 ========== */
.search-section {
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.12), rgba(255, 255, 255, 0.05));
  backdrop-filter: blur(15px);
  border-radius: 20px;
  padding: 32px;
  margin-bottom: 48px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
  animation: slideUp 0.6s ease-out 0.2s both;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.search-bar {
  display: flex;
  align-items: center;
  gap: 16px;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 50px;
  padding: 8px 8px 8px 24px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  transition: all 0.3s ease;
}

.search-bar:focus-within {
  box-shadow: 0 6px 30px rgba(255, 215, 0, 0.4);
  transform: translateY(-2px);
}

.search-icon {
  font-size: 20px;
  color: #D03050;
}

.search-input {
  flex: 1;
  border: none;
  background: transparent;
  font-size: 16px;
  color: #333;
  outline: none;
}

.search-input::placeholder {
  color: #999;
}

.search-button {
  position: relative;
  background: linear-gradient(135deg, #D03050, #8B0000);
  color: white;
  border: none;
  border-radius: 50px;
  padding: 14px 32px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  overflow: hidden;
  transition: all 0.3s ease;
  box-shadow: 0 4px 15px rgba(208, 48, 80, 0.4);
}

.search-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(208, 48, 80, 0.6);
}

.search-button:active {
  transform: translateY(0);
}

.button-shine {
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
  animation: shine 3s infinite;
}

@keyframes shine {
  to {
    left: 200%;
  }
}

.filters-section {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-top: 20px;
}

.filter-label {
  color: white;
  font-weight: 600;
  font-size: 14px;
}

.filter-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.filter-tag {
  background: rgba(255, 215, 0, 0.2);
  color: #FFD700;
  padding: 8px 16px;
  border-radius: 20px;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  border: 1px solid rgba(255, 215, 0, 0.4);
  transition: all 0.3s ease;
}

.filter-tag:hover {
  background: rgba(255, 215, 0, 0.3);
  transform: translateY(-2px);
}

.tag-close {
  font-size: 18px;
  font-weight: 700;
}

/* ========== 加载动画 ========== */
.loading-section {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 100px 20px;
}

.loading-animation {
  text-align: center;
}

.flag-wave {
  width: 80px;
  height: 80px;
  margin: 0 auto 24px;
  background: linear-gradient(135deg, #D03050, #FFD700);
  border-radius: 12px;
  animation: waveFlag 1.5s ease-in-out infinite;
}

@keyframes waveFlag {
  0%, 100% {
    transform: rotate(0deg) scale(1);
  }
  50% {
    transform: rotate(10deg) scale(1.1);
  }
}

.loading-text {
  font-size: 20px;
  color: white;
  font-weight: 600;
  letter-spacing: 2px;
}

/* ========== 空状态 ========== */
.empty-state {
  text-align: center;
  padding: 100px 20px;
  color: white;
}

.empty-icon {
  font-size: 80px;
  margin-bottom: 24px;
  opacity: 0.6;
}

.empty-title {
  font-size: 28px;
  font-weight: 700;
  margin-bottom: 12px;
}

.empty-description {
  font-size: 16px;
  opacity: 0.8;
}

/* ========== 案例网格 ========== */
.cases-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 32px;
  margin-bottom: 60px;
}

.case-card {
  position: relative;
  background: linear-gradient(135deg, #fffef8 0%, #fefefe 100%);
  border-radius: 8px;
  padding: 28px;
  cursor: pointer;
  border: 1px solid rgba(0, 0, 0, 0.08);
  transition: all 0.3s ease;
  animation: cardFadeIn 0.6s ease-out both;
  overflow: hidden;
  box-shadow:
    0 2px 8px rgba(0, 0, 0, 0.08),
    0 4px 16px rgba(0, 0, 0, 0.08);
}

/* 纸张纹理效果 */
.case-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-image:
    repeating-linear-gradient(
      0deg,
      transparent,
      transparent 2px,
      rgba(0, 0, 0, 0.01) 2px,
      rgba(0, 0, 0, 0.01) 4px
    );
  pointer-events: none;
  opacity: 0.3;
}

@keyframes cardFadeIn {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.case-card:hover {
  transform: translateY(-4px);
  border-color: #0066cc;
  box-shadow:
    0 4px 16px rgba(0, 0, 0, 0.12),
    0 8px 32px rgba(0, 102, 204, 0.15);
}

.card-accent {
  position: absolute;
  top: 0;
  left: 0;
  width: 4px;
  height: 100%;
  background: linear-gradient(180deg, #0066cc, #004499);
  transition: width 0.3s ease;
}

.case-card:hover .card-accent {
  width: 4px;
}

.card-glow {
  display: none;
}

.case-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 16px;
  position: relative;
  z-index: 1;
}

.case-tag {
  background: #f0f7ff;
  color: #0066cc;
  padding: 6px 14px;
  border-radius: 16px;
  font-size: 13px;
  font-weight: 600;
  border: 1px solid #cce5ff;
  letter-spacing: 0.5px;
}

.case-title {
  font-size: 22px;
  font-weight: 700;
  color: #1a1a1a;
  margin-bottom: 16px;
  line-height: 1.4;
  text-shadow: none;
  transition: color 0.3s ease;
  position: relative;
  z-index: 1;
}

.case-card:hover .case-title {
  color: #0066cc;
}

.case-summary {
  color: #555;
  font-size: 15px;
  line-height: 1.7;
  margin-bottom: 20px;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  position: relative;
  z-index: 1;
}

.case-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 16px;
  border-top: 1px solid rgba(0, 0, 0, 0.1);
  position: relative;
  z-index: 1;
}

.case-date {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #666;
}

.date-icon {
  font-size: 16px;
}

.case-arrow {
  font-size: 24px;
  color: #0066cc;
  transition: transform 0.3s ease;
}

.case-card:hover .case-arrow {
  transform: translateX(8px);
}

/* ========== 分页 ========== */
.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 32px;
  margin-bottom: 40px;
}

.pagination-button {
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.15), rgba(255, 255, 255, 0.08));
  backdrop-filter: blur(10px);
  color: white;
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 12px;
  padding: 14px 28px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.pagination-button:not(:disabled):hover {
  background: linear-gradient(135deg, rgba(255, 215, 0, 0.3), rgba(208, 48, 80, 0.3));
  border-color: rgba(255, 215, 0, 0.6);
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(255, 215, 0, 0.3);
}

.pagination-button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.page-info {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border-radius: 12px;
  padding: 12px 24px;
  font-size: 18px;
  font-weight: 600;
  color: white;
}

.current-page {
  color: #FFD700;
  font-size: 24px;
}

.page-separator {
  margin: 0 8px;
  opacity: 0.6;
}

.total-pages {
  opacity: 0.8;
}

/* ========== 刷新指示器 ========== */
.refresh-indicator {
  position: fixed;
  bottom: 32px;
  right: 32px;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.15), rgba(255, 255, 255, 0.05));
  backdrop-filter: blur(15px);
  border-radius: 16px;
  padding: 16px 24px;
  display: flex;
  align-items: center;
  gap: 12px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  z-index: 100;
  overflow: hidden;
}

.refresh-icon {
  font-size: 20px;
  animation: rotate 3s linear infinite;
}

@keyframes rotate {
  to {
    transform: rotate(360deg);
  }
}

.refresh-text {
  font-size: 14px;
  color: white;
  font-weight: 600;
}

.refresh-progress {
  position: absolute;
  bottom: 0;
  left: 0;
  height: 3px;
  background: linear-gradient(90deg, #FFD700, #D03050);
  transition: width 1s linear;
}

/* ========== 响应式设计 ========== */
@media (max-width: 768px) {
  .container {
    padding: 60px 16px 40px;
  }

  .hero-title {
    font-size: 36px;
  }

  .title-line {
    font-size: 24px;
  }

  .hero-subtitle {
    font-size: 18px;
  }

  .stat-number {
    font-size: 32px;
  }

  .cases-grid {
    grid-template-columns: 1fr;
    gap: 24px;
  }

  .pagination {
    flex-wrap: wrap;
  }

  .refresh-indicator {
    bottom: 16px;
    right: 16px;
  }
}
</style>
