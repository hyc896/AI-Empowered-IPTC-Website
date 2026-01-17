<template>
  <header class="app-header">
    <div class="header-container">
      <div class="logo-section">
        <h1 class="logo">思政课智能案例系统</h1>
      </div>

      <nav class="nav-menu">
        <router-link to="/cases" class="nav-item" active-class="active">
          <el-icon><Document /></el-icon>
          案例库
        </router-link>
        <router-link to="/graph" class="nav-item" active-class="active">
          <el-icon><Connection /></el-icon>
          知识图谱
        </router-link>
      </nav>

      <div class="header-actions">
        <SearchBar v-if="false" />
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { Document, Connection } from '@element-plus/icons-vue'
import SearchBar from '@/components/common/SearchBar.vue'
</script>

<style scoped lang="scss">
.app-header {
  background: #fff;
  border-bottom: 1px solid #e5e7eb;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.header-container {
  max-width: 1600px;
  margin: 0 auto;
  padding: 0 24px;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.logo {
  font-size: 20px;
  font-weight: 600;
  color: #3b82f6;
  margin: 0;
}

.nav-menu {
  display: flex;
  gap: 8px;
}

.nav-item {
  padding: 8px 16px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
  color: #6b7280;
  text-decoration: none;
  transition: all 0.2s;

  &:hover {
    background: #f3f4f6;
    color: #3b82f6;
  }

  &.active {
    background: #eff6ff;
    color: #3b82f6;
    font-weight: 600;
  }
}
</style>
