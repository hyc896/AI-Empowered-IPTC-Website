<template>
  <div class="teacher-layout">
    <el-container>
      <el-aside :width="collapsed ? '64px' : '220px'" class="sidebar">
        <div class="logo" @click="$router.push('/')">
          <el-icon v-if="collapsed"><Management /></el-icon>
          <span v-else>逐光智慧思政</span>
        </div>
        <el-menu
          :default-active="$route.path"
          router
          :collapse="collapsed"
          background-color="#1a1a2e"
          text-color="#ccc"
          active-text-color="#fff"
        >
          <el-menu-item index="/teacher/review">
            <el-icon><Check /></el-icon>
            <template #title>
              <span>审核工作台</span>
              <el-badge v-if="pendingCount > 0" :value="pendingCount" :max="99" class="menu-badge" />
            </template>
          </el-menu-item>
          <el-menu-item index="/teacher/statistics">
            <el-icon><DataAnalysis /></el-icon>
            <template #title>统计分析</template>
          </el-menu-item>
          <el-menu-item index="/teacher/venues">
            <el-icon><Location /></el-icon>
            <template #title>场馆管理</template>
          </el-menu-item>
          <el-menu-item index="/">
            <el-icon><House /></el-icon>
            <template #title>返回首页</template>
          </el-menu-item>
        </el-menu>
        <div class="collapse-btn" @click="collapsed = !collapsed">
          <el-icon><ArrowLeft v-if="!collapsed" /><ArrowRight v-else /></el-icon>
        </div>
      </el-aside>

      <el-container>
        <el-header class="header">
          <div class="header-left">
            <el-breadcrumb separator="/">
              <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
              <el-breadcrumb-item>教师管理</el-breadcrumb-item>
            </el-breadcrumb>
          </div>
          <div class="header-right">
            <el-dropdown @command="handleCommand">
              <span class="user-info">
                <el-avatar :size="32" style="background:#27ae60">{{ userStore.user?.real_name?.[0] }}</el-avatar>
                <span>{{ userStore.user?.real_name }}</span>
                <el-icon><ArrowDown /></el-icon>
              </span>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="logout">退出登录</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </el-header>
        <el-main class="main-content">
          <router-view />
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { reviewAPI } from '@/api'
import { ElMessage } from 'element-plus'

const router = useRouter()
const userStore = useUserStore()
const collapsed = ref(false)
const pendingCount = ref(0)

const fetchPendingCount = async () => {
  try {
    const res = await reviewAPI.getStatistics()
    pendingCount.value = res.pending || 0
  } catch (e) {
    // ignore
  }
}

// 初始加载 + 定时刷新
let timer = null
onMounted(() => {
  fetchPendingCount()
  timer = setInterval(fetchPendingCount, 30000)
})

onUnmounted(() => {
  clearInterval(timer)
})

const handleCommand = async (cmd) => {
  if (cmd === 'logout') {
    await userStore.logout()
    ElMessage.success('已退出登录')
    router.push('/login')
  }
}
</script>

<style scoped>
.teacher-layout { height: 100vh; overflow: hidden; }
.sidebar {
  background: #1a1a2e;
  transition: width 0.3s;
  display: flex;
  flex-direction: column;
}
.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 16px;
  font-weight: bold;
  cursor: pointer;
  border-bottom: 1px solid #333;
  padding: 0 16px;
  white-space: nowrap;
  overflow: hidden;
}
.el-menu { border-right: none; flex: 1; }
.collapse-btn {
  padding: 12px;
  text-align: center;
  color: #ccc;
  cursor: pointer;
  border-top: 1px solid #333;
}
.collapse-btn:hover { color: #fff; }
.header {
  background: #fff;
  border-bottom: 1px solid #eee;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
}
.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  color: #333;
}
.main-content { background: #f5f7fa; padding: 20px; height: calc(100vh - 60px); overflow: hidden; box-sizing: border-box; }
.menu-badge { margin-left: 8px; }
.menu-badge :deep(.el-badge__content) { background-color: #f56c6c; }
</style>
