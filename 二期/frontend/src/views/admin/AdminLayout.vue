<template>
  <div class="admin-layout">
    <div class="sidebar">
      <div class="brand">逐光管理后台</div>
      <nav class="nav">
        <router-link to="/admin" exact class="nav-item">概览</router-link>
        <router-link to="/admin/sources" class="nav-item">消息采集</router-link>
        <router-link to="/admin/users" class="nav-item">用户管理</router-link>
        <router-link to="/admin/practices" class="nav-item">实践项目</router-link>
      </nav>
      <div class="nav-bottom">
        <el-button text style="color:rgba(255,255,255,0.5);font-size:12px" @click="router.push('/')">← 返回主站</el-button>
      </div>
    </div>
    <div class="body">
      <router-view />
    </div>
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
  width: 200px;
  flex-shrink: 0;
  background: rgba(0,0,0,0.6);
  backdrop-filter: blur(16px);
  border-right: 1px solid rgba(255,255,255,0.08);
  display: flex;
  flex-direction: column;
  padding: 0;
}
.brand {
  padding: 24px 20px;
  font-size: 14px;
  font-weight: 700;
  color: #ffd700;
  border-bottom: 1px solid rgba(255,255,255,0.08);
}
.nav { display: flex; flex-direction: column; padding: 12px 0; flex: 1; }
.nav-item {
  padding: 12px 20px;
  font-size: 13px;
  color: rgba(255,255,255,0.6);
  text-decoration: none;
  transition: all 0.15s;
}
.nav-item:hover { color: #fff; background: rgba(255,255,255,0.06); }
.nav-item.router-link-active { color: #ffd700; background: rgba(192,57,43,0.2); border-left: 3px solid #ffd700; }
.nav-bottom { padding: 16px 12px; border-top: 1px solid rgba(255,255,255,0.08); }
.body { flex: 1; overflow-y: auto; padding: 24px; }
</style>
