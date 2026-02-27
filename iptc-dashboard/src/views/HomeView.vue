<template>
  <div class="home-view">
    <!-- 英雄区 -->
    <section class="hero-section">
      <div class="hero-background"></div>
      <div class="container hero-content">
        <h1 class="hero-title slide-up">AI赋能思政教育</h1>
        <p class="hero-subtitle slide-up">智能案例库与知识图谱系统</p>
        <div class="hero-actions slide-up">
          <base-button type="secondary" size="large" @click="navigateToCases">
            探索案例库
          </base-button>
          <base-button type="outline" size="large" @click="navigateToGraph">
            查看知识图谱
          </base-button>
        </div>
      </div>
    </section>

    <!-- 功能介绍区 -->
    <section class="features-section">
      <div class="container">
        <h2 class="section-title">核心功能</h2>
        <div class="features-grid">
          <div v-for="feature in features" :key="feature.title" class="feature-card fade-in">
            <div class="feature-icon" v-html="feature.icon"></div>
            <h3 class="feature-title">{{ feature.title }}</h3>
            <p class="feature-description">{{ feature.description }}</p>
          </div>
        </div>
      </div>
    </section>

    <!-- 数据统计区 -->
    <section class="statistics-section">
      <div class="container">
        <h2 class="section-title">平台数据</h2>
        <div class="statistics-grid">
          <div v-for="stat in statisticsData" :key="stat.label" class="stat-card">
            <div class="stat-value">{{ formatNumber(stat.value) }}+</div>
            <div class="stat-label">{{ stat.label }}</div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useAppStore } from '@/stores';
import { formatNumber } from '@/utils';
import BaseButton from '@/components/ui/BaseButton.vue';

const router = useRouter();
const appStore = useAppStore();

const features = [
  {
    title: '智能案例采集',
    description: '自动采集和分类思政案例，构建全面的案例资源库',
    icon: '<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path><polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline><line x1="12" y1="22.08" x2="12" y2="12"></line></svg>',
  },
  {
    title: '知识图谱可视化',
    description: '直观展示案例间关系，帮助理解知识结构和关联',
    icon: '<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><path d="M8 14s1.5 2 4 2 4-2 4-2"></path><line x1="9" y1="9" x2="9.01" y2="9"></line><line x1="15" y1="9" x2="15.01" y2="9"></line></svg>',
  },
  {
    title: '语义检索分析',
    description: '智能搜索和推荐，快速找到相关案例和知识点',
    icon: '<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>',
  },
];

const statisticsData = ref([
  { label: '案例总数', value: 0 },
  { label: '知识点', value: 0 },
  { label: '覆盖主题', value: 0 },
  { label: '最近更新', value: 0 },
]);

onMounted(async () => {
  await appStore.fetchStatistics();
  statisticsData.value = [
    { label: '案例总数', value: appStore.statistics.total_cases },
    { label: '知识点总数', value: appStore.statistics.total_knowledge_points },
    { label: '已生成案例', value: appStore.statistics.generated_knowledge_points },
    { label: '关联总数', value: appStore.statistics.total_relations },
  ];
});

const navigateToCases = () => {
  router.push('/cases');
};

const navigateToGraph = () => {
  router.push('/graph');
};
</script>

<style scoped>
.home-view {
  min-height: 100vh;
}

/* 英雄区样式 */
.hero-section {
  position: relative;
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.hero-background {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-image: radial-gradient(circle at 20% 50%, rgba(255, 255, 255, 0.1) 0%, transparent 50%),
    radial-gradient(circle at 80% 80%, rgba(255, 255, 255, 0.1) 0%, transparent 50%);
  animation: float 10s ease-in-out infinite;
}

@keyframes float {
  0%,
  100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-20px);
  }
}

.hero-content {
  position: relative;
  z-index: 1;
  text-align: center;
  color: var(--color-white);
}

.hero-title {
  font-size: var(--font-size-4xl);
  font-weight: var(--font-weight-bold);
  margin-bottom: var(--spacing-lg);
  animation-delay: 0.1s;
}

.hero-subtitle {
  font-size: var(--font-size-xl);
  margin-bottom: var(--spacing-3xl);
  opacity: 0.95;
  animation-delay: 0.2s;
}

.hero-actions {
  display: flex;
  gap: var(--spacing-lg);
  justify-content: center;
  animation-delay: 0.3s;
}

.slide-up {
  animation: slideUp 0.8s ease-out forwards;
  opacity: 0;
}

@keyframes slideUp {
  to {
    opacity: 1;
    transform: translateY(0);
  }
  from {
    opacity: 0;
    transform: translateY(30px);
  }
}

/* 功能区样式 */
.features-section {
  padding: var(--spacing-4xl) 0;
  background-color: var(--bg-secondary);
}

.section-title {
  text-align: center;
  font-size: var(--font-size-3xl);
  font-weight: var(--font-weight-bold);
  margin-bottom: var(--spacing-3xl);
  color: var(--text-primary);
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: var(--spacing-2xl);
}

.feature-card {
  background: var(--bg-primary);
  padding: var(--spacing-2xl);
  border-radius: var(--border-radius-lg);
  box-shadow: var(--shadow-light);
  text-align: center;
  transition: all var(--transition-base);
}

.feature-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-medium);
}

.feature-icon {
  color: var(--color-primary);
  margin-bottom: var(--spacing-lg);
}

.feature-title {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-semibold);
  margin-bottom: var(--spacing-md);
  color: var(--text-primary);
}

.feature-description {
  color: var(--text-secondary);
  line-height: var(--line-height-relaxed);
}

/* 统计区样式 */
.statistics-section {
  padding: var(--spacing-4xl) 0;
  background-color: var(--bg-primary);
}

.statistics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--spacing-2xl);
}

.stat-card {
  text-align: center;
  padding: var(--spacing-2xl);
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-dark) 100%);
  border-radius: var(--border-radius-lg);
  color: var(--color-white);
  transition: transform var(--transition-base);
  box-shadow: 0 4px 12px rgba(208, 48, 80, 0.3);
}

.stat-card:hover {
  transform: scale(1.05);
}

.stat-value {
  font-size: var(--font-size-4xl);
  font-weight: var(--font-weight-bold);
  margin-bottom: var(--spacing-md);
}

.stat-label {
  font-size: var(--font-size-lg);
  opacity: 0.95;
}

.fade-in {
  animation: fadeIn 0.8s ease-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

@media (max-width: 768px) {
  .hero-title {
    font-size: var(--font-size-3xl);
  }

  .hero-subtitle {
    font-size: var(--font-size-lg);
  }

  .hero-actions {
    flex-direction: column;
  }

  .features-grid,
  .statistics-grid {
    grid-template-columns: 1fr;
  }
}
</style>
