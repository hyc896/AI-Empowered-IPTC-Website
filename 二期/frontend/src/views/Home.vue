<template>
  <div class="home-container">
    <!-- 顶部导航 -->
    <div class="header">
      <div class="header-left">
        <div class="logo-text">逐光智慧思政</div>
      </div>
      <div class="header-right">
        <el-avatar :size="32" style="background:#c0392b;margin-right:8px">
          {{ userStore.user?.real_name?.[0] }}
        </el-avatar>
        <span class="username">{{ userStore.user?.real_name }}</span>
        <el-tag size="small" style="margin-left:8px">{{ roleLabel }}</el-tag>
        <el-button text @click="handleLogout" style="margin-left:16px">退出登录</el-button>
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
        <div class="module-card cases-card" @click="goToCases">
          <div class="module-badge">板块一</div>
          <div class="module-icon">📚</div>
          <h3>案例学习</h3>
          <p>AI驱动的思政课教学案例库，实时采集热点新闻，自动生成教学案例</p>
          <ul class="feature-list">
            <li>热点新闻自动采集</li>
            <li>AI智能生成案例</li>
            <li>知识图谱可视化</li>
          </ul>
          <div class="module-footer">
            <el-tag>教师 / 学生</el-tag>
            <span class="arrow">进入 →</span>
          </div>
        </div>

        <!-- 实践活动板块 -->
        <div class="module-card practice-card" @click="goToPractice">
          <div class="module-badge">板块二</div>
          <div class="module-icon">🧭</div>
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
            <el-tag :type="userStore.isStudent ? 'primary' : 'success'">
              {{ userStore.isStudent ? '学生端' : '教师端' }}
            </el-tag>
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
  // 案例学习板块跳转到一期项目
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
.home-container { min-height: 100vh; background: #f0f2f5; overflow: hidden; }

.header {
  background: #1a1a2e;
  padding: 0 40px;
  height: 60px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.logo-text { color: #fff; font-size: 20px; font-weight: bold; letter-spacing: 2px; }
.header-right { display: flex; align-items: center; }
.username { color: #fff; font-size: 14px; }

.content { max-width: 1200px; width: 100%; margin: 0 auto; padding: 60px 20px; }

.welcome { text-align: center; margin-bottom: 50px; }
.welcome h2 { font-size: 30px; color: #333; margin-bottom: 10px; }
.welcome p { font-size: 15px; color: #666; }

.modules {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 30px;
}

.module-card {
  background: white;
  border-radius: 12px;
  padding: 36px 32px;
  cursor: pointer;
  transition: all 0.3s;
  position: relative;
  border: 2px solid transparent;
  box-shadow: 0 2px 12px rgba(0,0,0,0.08);
}
.module-card:hover { transform: translateY(-4px); box-shadow: 0 8px 24px rgba(0,0,0,0.12); }
.cases-card:hover { border-color: #409eff; }
.practice-card:hover { border-color: #c0392b; }

.module-badge {
  position: absolute;
  top: 16px;
  right: 16px;
  background: #f0f2f5;
  color: #888;
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 10px;
}
.module-icon { font-size: 48px; margin-bottom: 16px; }
.module-card h3 { font-size: 22px; color: #333; margin-bottom: 10px; }
.module-card p { font-size: 14px; color: #666; line-height: 1.6; margin-bottom: 16px; }

.feature-list { list-style: none; padding: 0; margin-bottom: 20px; }
.feature-list li { font-size: 13px; color: #888; padding: 3px 0; }
.feature-list li::before { content: '✓ '; color: #67c23a; }

.module-footer { display: flex; justify-content: space-between; align-items: center; }
.arrow { color: #999; font-size: 14px; }
.module-card:hover .arrow { color: #333; }

@media (max-width: 768px) {
  .modules { grid-template-columns: 1fr; }
  .header { padding: 0 16px; }
  .content { padding: 30px 16px; }
}
</style>
