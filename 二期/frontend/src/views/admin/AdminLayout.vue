<template>
  <div class="admin-layout">
    <aside class="sidebar">
      <div class="brand">
        <span class="brand-icon">⚙</span>
        <span>逐光管理后台</span>
      </div>
      <nav class="nav">
        <router-link to="/admin" exact class="nav-item">
          <span class="nav-icon">▣</span>系统概览
        </router-link>
        <router-link to="/admin/sources" class="nav-item">
          <span class="nav-icon">◈</span>消息采集
        </router-link>
        <router-link to="/admin/users" class="nav-item">
          <span class="nav-icon">◎</span>用户管理
        </router-link>
        <router-link to="/admin/practices" class="nav-item">
          <span class="nav-icon">◆</span>实践项目
        </router-link>
      </nav>
      <button class="back-btn" @click="router.push('/')">← 返回主站</button>
    </aside>
    <main class="content">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
const router = useRouter()
</script>

<style scoped>
.admin-layout {
  height: 100vh;
  display: flex;
  background: url('@/assets/bg-main.webp') center/cover no-repeat fixed;
  color: #fff;
}
.sidebar {
  width: 220px;
  flex-shrink: 0;
  background: rgba(0,0,0,0.78);
  backdrop-filter: blur(20px);
  border-right: 1px solid rgba(255,215,0,0.1);
  display: flex;
  flex-direction: column;
}
.brand {
  padding: 28px 24px 20px;
  font-size: 15px;
  font-weight: 700;
  color: #ffd700;
  border-bottom: 1px solid rgba(255,255,255,0.06);
  display: flex;
  align-items: center;
  gap: 10px;
}
.brand-icon { font-size: 18px; }
.nav { flex: 1; padding: 12px 0; }
.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 13px 24px;
  font-size: 14px;
  color: rgba(255,255,255,0.55);
  text-decoration: none;
  transition: all 0.15s;
  border-left: 3px solid transparent;
}
.nav-item:hover { color: rgba(255,255,255,0.9); background: rgba(255,255,255,0.04); }
.nav-item.router-link-active {
  color: #ffd700;
  background: rgba(255,215,0,0.08);
  border-left-color: #ffd700;
}
.nav-icon { font-size: 14px; opacity: 0.7; }
.back-btn {
  margin: 16px;
  padding: 10px 16px;
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 8px;
  color: rgba(255,255,255,0.5);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s;
}
.back-btn:hover { background: rgba(255,255,255,0.1); color: #fff; }
.content {
  flex: 1;
  overflow-y: auto;
  padding: 32px;
  min-width: 0;
}
</style>
