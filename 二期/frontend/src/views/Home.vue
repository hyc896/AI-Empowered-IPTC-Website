<template>
  <div class="home-container">
    <!-- 顶部导航 -->
    <div class="header">
      <div class="header-left">
        <div class="logo-text">逐光智慧思政</div>
      </div>
      <div class="header-right">
        <el-avatar :size="32" style="background:rgba(255,255,255,0.2);margin-right:8px">
          {{ userStore.user?.real_name?.[0] }}
        </el-avatar>
        <span class="username">{{ userStore.user?.real_name }}</span>
        <el-tag size="small" effect="dark" style="margin-left:8px;background:rgba(255,255,255,0.15);border:none;color:#fff">{{ roleLabel }}</el-tag>
        <el-button text style="margin-left:16px;color:rgba(255,255,255,0.7)" @click="handleLogout">退出登录</el-button>
      </div>
    </div>

    <!-- 主内容 -->
    <div class="content">
      <div class="welcome">
        <h2>欢迎回来，{{ userStore.user?.real_name }}</h2>
        <p>{{ roleDesc }}</p>
      </div>

      <div class="modules">
        <!-- 案例学习板块 -->
        <div class="module-card" @click="goToCases">
          <div class="module-badge">板块一</div>
          <div class="module-icon-wrap">
            <el-icon :size="36"><Reading /></el-icon>
          </div>
          <h3>案例学习</h3>
          <p>AI驱动的思政课教学案例库，实时采集热点新闻，自动生成教学案例</p>
          <ul class="feature-list">
            <li>热点新闻自动采集</li>
            <li>AI智能生成案例</li>
            <li>知识图谱可视化</li>
          </ul>
          <div class="module-footer">
            <span class="role-tag">教师 / 学生</span>
            <span class="arrow">进入 →</span>
          </div>
        </div>

        <!-- 实践活动板块 -->
        <div class="module-card" @click="goToPractice">
          <div class="module-badge">板块二</div>
          <div class="module-icon-wrap">
            <el-icon :size="36"><Compass /></el-icon>
          </div>
          <h3>实践活动</h3>
          <p>
            <span v-if="userStore.isStudent">选择知识点，AI生成个性化实践方案，完成实践并提交</span>
            <span v-else>审核学生实践作业，管理场馆资源，查看统计数据</span>
          </p>
          <ul class="feature-list">
            <li v-if="userStore.isStudent">AI个性化方案生成</li>
            <li v-if="userStore.isStudent">7种实践类型可选</li>
            <li v-if="userStore.isStudent">在线提交实践成果</li>
            <li v-if="!userStore.isStudent">审核工作台</li>
            <li v-if="!userStore.isStudent">场馆资源管理</li>
            <li v-if="!userStore.isStudent">统计分析报表</li>
          </ul>
          <div class="module-footer">
            <span class="role-tag">{{ userStore.isStudent ? '学生端' : '教师端' }}</span>
            <span class="arrow">进入 →</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { ElMessage } from 'element-plus'

const router = useRouter()
const userStore = useUserStore()

const roleLabel = computed(() => ({ student: '学生', teacher: '教师', admin: '管理员' }[userStore.user?.role] || '')
)
const roleDesc = computed(() => {
  if (userStore.isStudent) return '选择你感兴趣的知识点，开始你的实践之旅'
  if (userStore.isTeacher) return '查看教学案例，审核学生实践作业'
  return '系统管理'
})

const goToCases = () => {
  const a = document.createElement('a')
  a.href = 'http://localhost:5714'
  a.target = '_blank'
  a.rel = 'noopener noreferrer'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}

const goToPractice = () => {
  if (userStore.isStudent) {
    router.push('/student/knowledge')
  } else {
    router.push('/teacher/review')
  }
}

const handleLogout = async () => {
  await userStore.logout()
  ElMessage.success('已退出登录')
  router.push('/login')
}
</script>

<style scoped>
.home-container {
  min-height: 100vh;
  background: url('@/assets/bg-main.png') center/cover no-repeat fixed;
  position: relative;
}
.home-container::before {
  content: '';
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.35);
  pointer-events: none;
}

.header {
  position: relative;
  z-index: 1;
  background: rgba(0, 0, 0, 0.3);
  backdrop-filter: blur(12px);
  padding: 0 40px;
  height: 60px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid rgba(255,255,255,0.08);
}
.logo-text { color: #fff; font-size: 20px; font-weight: bold; letter-spacing: 2px; }
.header-right { display: flex; align-items: center; }
.username { color: #fff; font-size: 14px; }

.content {
  position: relative;
  z-index: 1;
  max-width: 1000px;
  width: 100%;
  margin: 0 auto;
  padding: 80px 20px;
}

.welcome { text-align: center; margin-bottom: 60px; }
.welcome h2 { font-size: 32px; color: #fff; margin-bottom: 10px; font-weight: 600; text-shadow: 0 2px 8px rgba(0,0,0,0.3); }
.welcome p { font-size: 15px; color: rgba(255,255,255,0.75); }

.modules {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 30px;
}

.module-card {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 16px;
  padding: 36px 32px;
  cursor: pointer;
  transition: all 0.3s;
  position: relative;
  color: #fff;
}
.module-card:hover {
  transform: translateY(-4px);
  background: rgba(255, 255, 255, 0.16);
  border-color: rgba(255, 255, 255, 0.3);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.3);
}

.module-badge {
  position: absolute;
  top: 16px;
  right: 16px;
  background: rgba(255, 255, 255, 0.12);
  color: rgba(255, 255, 255, 0.6);
  font-size: 12px;
  padding: 2px 10px;
  border-radius: 10px;
}
.module-icon-wrap {
  margin-bottom: 16px;
  color: rgba(255, 255, 255, 0.85);
}
.module-card h3 { font-size: 22px; color: #fff; margin-bottom: 10px; font-weight: 600; }
.module-card p { font-size: 14px; color: rgba(255,255,255,0.7); line-height: 1.6; margin-bottom: 16px; }

.feature-list { list-style: none; padding: 0; margin-bottom: 20px; }
.feature-list li {
  font-size: 13px;
  color: rgba(255,255,255,0.6);
  padding: 3px 0;
}
.feature-list li::before { content: '· '; color: rgba(255,255,255,0.4); }

.module-footer { display: flex; justify-content: space-between; align-items: center; }
.role-tag {
  font-size: 12px;
  color: rgba(255,255,255,0.5);
  background: rgba(255,255,255,0.1);
  padding: 2px 10px;
  border-radius: 4px;
}
.arrow { color: rgba(255,255,255,0.5); font-size: 14px; transition: color 0.2s; }
.module-card:hover .arrow { color: #fff; }

@media (max-width: 768px) {
  .modules { grid-template-columns: 1fr; }
  .header { padding: 0 16px; }
  .content { padding: 40px 16px; }
}
</style>
