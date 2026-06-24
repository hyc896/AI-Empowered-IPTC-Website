<template>
  <div class="platform-home">
    <!-- 顶部导航 -->
    <div class="header">
      <div class="header-left">
        <span class="logo">思想政治理论课教学案例库</span>
      </div>
      <div class="header-right">
        <el-button text style="color:rgba(255,255,255,0.6)" @click="router.push('/')">返回主站</el-button>
      </div>
    </div>

    <!-- 英雄区 -->
    <div class="hero">
      <div class="hero-content">
        <h1 class="hero-title">
          <span class="white-text">思想政治理论课</span>
          <span class="gold-text">教学案例库</span>
        </h1>
        <p class="hero-sub">传承红色基因 · 铸就时代新人</p>
        <div class="hero-stats">
          <div class="stat-item">
            <span class="stat-num">{{ stats.total_cases || '--' }}</span>
            <span class="stat-label">教学案例</span>
          </div>
          <div class="stat-divider"></div>
          <div class="stat-item">
            <span class="stat-num">259</span>
            <span class="stat-label">知识点覆盖</span>
          </div>
          <div class="stat-divider"></div>
          <div class="stat-item">
            <span class="stat-num">{{ latestUpdate }}</span>
            <span class="stat-label">最近更新</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 入口卡片 -->
    <div class="entry-section">
      <div class="entry-grid">
        <div class="entry-card" @click="router.push('/cases')">
          <div class="entry-icon">
            <el-icon :size="40"><Reading /></el-icon>
          </div>
          <h3>全部案例</h3>
          <p>浏览 AI 自动生成的思政教学案例，支持按知识点筛选、关键词搜索，上海 / 全国双维度</p>
          <span class="entry-arrow">进入 →</span>
        </div>
        <div class="entry-card" @click="router.push('/case-platform/books')">
          <div class="entry-icon">
            <el-icon :size="40"><Share /></el-icon>
          </div>
          <h3>知识图谱</h3>
          <p>可视化展示三本教材 259 个知识点的层级关系，点击节点查看关联案例</p>
          <span class="entry-arrow">进入 →</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Reading, Share } from '@element-plus/icons-vue'
import { caseAPI } from '@/api/index'

const router = useRouter()
const stats = ref({})

const latestUpdate = computed(() => {
  const cases = stats.value.latest_cases
  if (!cases || !cases.length) return '--'
  const date = new Date(cases[0].created_at)
  return `${date.getMonth() + 1}月${date.getDate()}日`
})

onMounted(async () => {
  try {
    const res = await caseAPI.getStatistics()
    stats.value = res || {}
  } catch (e) {
    // non-blocking
  }
})
</script>

<style scoped>
.platform-home {
  height: 100vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background: url('@/assets/bg-main.webp') center/cover no-repeat fixed;
  color: #fff;
}

.header {
  position: sticky;
  top: 0;
  z-index: 100;
  background: rgba(0,0,0,0.5);
  backdrop-filter: blur(12px);
  padding: 0 48px;
  height: 64px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid rgba(192,57,43,0.2);
}
.logo {
  font-size: 16px;
  font-weight: 700;
  letter-spacing: 1px;
  background: linear-gradient(90deg, #ffd700, #ffa500, #ffd700);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

/* 英雄区 */
.hero {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background:
    radial-gradient(ellipse 80% 60% at 50% 40%, rgba(192,57,43,0.18) 0%, transparent 70%),
    radial-gradient(ellipse 40% 40% at 30% 60%, rgba(255,215,0,0.06) 0%, transparent 60%);
  padding: 40px 40px;
  text-align: center;
}
.hero-title {
  font-size: 48px;
  font-weight: 700;
  line-height: 1.2;
  margin-bottom: 20px;
}
.white-text { color: #fff; display: block; }
.gold-text {
  display: block;
  background: linear-gradient(90deg, #ffd700 0%, #ffa500 40%, #ffe066 70%, #ffd700 100%);
  background-size: 200% auto;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  animation: shine 3s linear infinite;
}
@keyframes shine {
  to { background-position: 200% center; }
}
.hero-sub {
  font-size: 18px;
  color: rgba(255,255,255,0.55);
  letter-spacing: 3px;
  margin-bottom: 48px;
}

.hero-stats {
  display: inline-flex;
  align-items: center;
  gap: 0;
  background: rgba(0,0,0,0.65);
  backdrop-filter: blur(16px);
  border: 1px solid rgba(255,215,0,0.25);
  border-radius: 16px;
  padding: 28px 48px;
}
.stat-item { text-align: center; padding: 0 32px; }
.stat-num {
  display: block;
  font-size: 44px;
  font-weight: 700;
  color: #ffd700;
  line-height: 1;
  margin-bottom: 8px;
}
.stat-label { font-size: 15px; color: rgba(255,255,255,0.75); font-weight: 500; }
.stat-divider {
  width: 1px;
  height: 40px;
  background: rgba(255,215,0,0.2);
}

/* 入口区 */
.entry-section {
  padding: 32px 48px 48px;
  display: flex;
  justify-content: center;
}
.entry-grid {
  width: 100%;
  max-width: 800px;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 28px;
}
.entry-card {
  background: rgba(255,255,255,0.05);
  backdrop-filter: blur(16px);
  border: 1px solid rgba(192,57,43,0.2);
  border-radius: 16px;
  padding: 40px 32px;
  cursor: pointer;
  transition: all 0.3s;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}
.entry-card:hover {
  background: rgba(192,57,43,0.1);
  border-color: rgba(255,215,0,0.3);
  transform: translateY(-6px);
  box-shadow: 0 16px 48px rgba(192,57,43,0.2), 0 0 0 1px rgba(255,215,0,0.1);
}
.entry-icon {
  color: #ffd700;
  margin-bottom: 20px;
}
.entry-card h3 {
  font-size: 22px;
  font-weight: 700;
  color: #fff;
  margin-bottom: 12px;
}
.entry-card p {
  font-size: 14px;
  color: rgba(255,255,255,0.5);
  line-height: 1.7;
  flex: 1;
  margin-bottom: 24px;
}
.entry-arrow {
  color: rgba(255,215,0,0.6);
  font-size: 14px;
  transition: color 0.2s;
}
.entry-card:hover .entry-arrow { color: #ffd700; }

@media (max-width: 900px) {
  .entry-grid { grid-template-columns: 1fr; }
  .hero-title { font-size: 32px; }
  .header { padding: 0 20px; }
  .entry-section { padding: 40px 20px 60px; }
}
</style>
