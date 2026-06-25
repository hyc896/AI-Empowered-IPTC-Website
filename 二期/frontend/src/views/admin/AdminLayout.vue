<template>
  <div class="admin-layout">
    <aside class="admin-sidebar">
      <div class="brand-block">
        <div class="brand-mark">ZG</div>
        <div>
          <strong>逐光管理后台</strong>
          <span>IPTC Operations</span>
        </div>
      </div>

      <nav class="admin-nav">
        <router-link to="/admin" class="nav-item" exact-active-class="active">
          <el-icon><DataAnalysis /></el-icon>
          <span>系统总览</span>
        </router-link>
        <router-link to="/admin/sources" class="nav-item" active-class="active">
          <el-icon><Connection /></el-icon>
          <span>采集与生成</span>
        </router-link>
        <router-link to="/admin/users" class="nav-item" active-class="active">
          <el-icon><User /></el-icon>
          <span>用户管理</span>
        </router-link>
        <router-link to="/admin/practices" class="nav-item" active-class="active">
          <el-icon><Files /></el-icon>
          <span>实践项目</span>
        </router-link>
      </nav>

      <div class="sidebar-footer">
        <span>当前模块</span>
        <strong>{{ currentTitle }}</strong>
        <button class="back-button" @click="router.push('/')">返回主站</button>
      </div>
    </aside>

    <section class="admin-main">
      <header class="admin-topbar">
        <div>
          <span class="eyebrow">Admin Console</span>
          <h1>{{ currentTitle }}</h1>
        </div>
        <div class="topbar-meta">
          <span>生产环境</span>
          <strong>{{ today }}</strong>
        </div>
      </header>
      <main class="admin-content">
        <router-view />
      </main>
    </section>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { Connection, DataAnalysis, Files, User } from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()

const titleMap = {
  AdminOverview: '系统总览',
  AdminSources: '采集与生成',
  AdminUsers: '用户管理',
  AdminPractices: '实践项目',
}

const currentTitle = computed(() => titleMap[route.name] || '管理后台')
const today = new Date().toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' })
</script>

<style scoped>
.admin-layout {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr);
  background:
    linear-gradient(135deg, rgba(15, 19, 25, 0.94), rgba(26, 30, 36, 0.9)),
    url('@/assets/bg-main.webp') center/cover no-repeat fixed;
  color: #f5efe4;
}

.admin-sidebar {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  padding: 22px 18px;
  border-right: 1px solid rgba(231, 196, 125, 0.18);
  background: rgba(9, 12, 16, 0.84);
  backdrop-filter: blur(22px);
}

.brand-block {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 8px 24px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.brand-mark {
  width: 44px;
  height: 44px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  background: #d6b15f;
  color: #151515;
  font-weight: 800;
  letter-spacing: 0;
}

.brand-block strong {
  display: block;
  font-size: 16px;
  letter-spacing: 0;
}

.brand-block span,
.eyebrow {
  display: block;
  margin-top: 3px;
  font-size: 11px;
  color: rgba(245, 239, 228, 0.48);
  letter-spacing: 0;
}

.admin-nav {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 18px 0;
  flex: 1;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 11px;
  min-height: 42px;
  padding: 0 12px;
  border-radius: 8px;
  color: rgba(245, 239, 228, 0.62);
  text-decoration: none;
  transition: all 0.18s ease;
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.06);
  color: #fff;
}

.nav-item.active {
  background: rgba(214, 177, 95, 0.16);
  color: #f2ca76;
  box-shadow: inset 0 0 0 1px rgba(214, 177, 95, 0.18);
}

.nav-item .el-icon {
  font-size: 17px;
}

.sidebar-footer {
  padding: 16px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.sidebar-footer span {
  display: block;
  color: rgba(245, 239, 228, 0.46);
  font-size: 12px;
}

.sidebar-footer strong {
  display: block;
  margin-top: 4px;
}

.back-button {
  width: 100%;
  height: 36px;
  margin-top: 14px;
  border-radius: 8px;
  border: 1px solid rgba(214, 177, 95, 0.25);
  background: transparent;
  color: #f2ca76;
  cursor: pointer;
}

.back-button:hover {
  background: rgba(214, 177, 95, 0.1);
}

.admin-main {
  min-width: 0;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.admin-topbar {
  min-height: 86px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 22px 32px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(14, 17, 22, 0.58);
  backdrop-filter: blur(18px);
}

.admin-topbar h1 {
  margin: 4px 0 0;
  font-size: 26px;
  line-height: 1.2;
  letter-spacing: 0;
}

.topbar-meta {
  min-width: 146px;
  padding: 10px 14px;
  border-radius: 8px;
  text-align: right;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.topbar-meta span {
  display: block;
  font-size: 12px;
  color: rgba(245, 239, 228, 0.46);
}

.topbar-meta strong {
  display: block;
  margin-top: 2px;
  color: #f2ca76;
}

.admin-content {
  flex: 1;
  min-width: 0;
  overflow-y: auto;
  padding: 28px 32px 36px;
}

@media (max-width: 860px) {
  .admin-layout {
    grid-template-columns: 1fr;
  }

  .admin-sidebar {
    min-height: auto;
    border-right: 0;
    border-bottom: 1px solid rgba(231, 196, 125, 0.18);
  }

  .admin-nav {
    flex-direction: row;
    overflow-x: auto;
  }

  .sidebar-footer {
    display: none;
  }

  .admin-topbar {
    padding: 18px 20px;
  }

  .admin-content {
    padding: 20px;
  }
}
</style>
