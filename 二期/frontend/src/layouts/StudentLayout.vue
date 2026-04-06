<template>
  <div class="student-layout">
    <el-container>
      <!-- 侧边栏 -->
      <el-aside :width="collapsed ? '64px' : '220px'" class="sidebar">
        <div class="logo" @click="$router.push('/')">
          <el-icon v-if="collapsed"><Compass /></el-icon>
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
          <el-menu-item index="/student/knowledge">
            <el-icon><Search /></el-icon>
            <template #title>选择知识点</template>
          </el-menu-item>
          <el-menu-item index="/student/my-practices">
            <el-icon><List /></el-icon>
            <template #title>我的实践</template>
          </el-menu-item>
          <el-menu-item index="/student/calendar">
            <el-icon><Calendar /></el-icon>
            <template #title>实践日历</template>
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
        <!-- 顶部栏 -->
        <el-header class="header">
          <div class="header-left">
            <el-breadcrumb separator="/">
              <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
              <el-breadcrumb-item>实践活动</el-breadcrumb-item>
            </el-breadcrumb>
          </div>
          <div class="header-right">
            <!-- 后台生成任务指示器 -->
            <div v-if="taskStore.hasGenerating" class="task-indicator" @click="$router.push('/student/my-practices')">
              <span class="task-spinner"></span>
              <span>{{ taskStore.generatingCount }}个方案生成中...</span>
            </div>
            <el-dropdown @command="handleCommand">
              <span class="user-info">
                <el-avatar :size="32" style="background:#c0392b">{{ userStore.user?.real_name?.[0] }}</el-avatar>
                <span>{{ userStore.user?.real_name }}</span>
                <el-icon><ArrowDown /></el-icon>
              </span>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="profile">个人中心</el-dropdown-item>
                  <el-dropdown-item command="logout">退出登录</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </el-header>

        <!-- 主内容 -->
        <el-main class="main-content">
          <router-view />
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useTaskStore } from '@/stores/task'
import { ElMessage } from 'element-plus'

const router = useRouter()
const userStore = useUserStore()
const taskStore = useTaskStore()
const collapsed = ref(false)

const handleCommand = async (cmd) => {
  if (cmd === 'profile') {
    router.push('/student/profile')
  } else if (cmd === 'logout') {
    await userStore.logout()
    ElMessage.success('已退出登录')
    router.push('/login')
  }
}
</script>

<style scoped>
.student-layout { height: 100vh; overflow: hidden; }
.sidebar {
  background: #1a1a2e;
  transition: width 0.3s;
  position: relative;
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
.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}
.main-content { background: #f5f7fa; padding: 20px; height: calc(100vh - 60px); overflow-y: auto; display: flex; flex-direction: column; }
.task-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 14px;
  background: #fdf6ec;
  border: 1px solid #faecd8;
  border-radius: 20px;
  font-size: 13px;
  color: #e6a23c;
  cursor: pointer;
  transition: background 0.2s;
}
.task-indicator:hover { background: #faecd8; }
.task-spinner {
  width: 12px;
  height: 12px;
  border: 2px solid #e6a23c;
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>
