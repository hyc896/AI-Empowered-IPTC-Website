<template>
  <header class="app-header">
    <div class="container header-container">
      <div class="header-left">
        <router-link to="/" class="logo">
          <div class="logo-icon">AI</div>
          <span class="logo-text">AI赋能思政案例库</span>
        </router-link>
      </div>

      <nav class="header-nav hide-mobile">
        <router-link to="/" class="nav-link">首页</router-link>
        <router-link to="/cases" class="nav-link">案例库</router-link>
        <router-link to="/graph" class="nav-link">知识图谱</router-link>
      </nav>

      <div class="header-right">
        <button class="menu-button hide-desktop" @click="toggleMobileMenu">
          <span class="menu-icon"></span>
        </button>
      </div>
    </div>

    <!-- 移动端菜单 -->
    <transition name="slide">
      <div v-if="appStore.mobileMenuOpen" class="mobile-menu hide-desktop">
        <nav class="mobile-nav">
          <router-link to="/" class="mobile-nav-link" @click="closeMobileMenu">首页</router-link>
          <router-link to="/cases" class="mobile-nav-link" @click="closeMobileMenu">案例库</router-link>
          <router-link to="/graph" class="mobile-nav-link" @click="closeMobileMenu">知识图谱</router-link>
        </nav>
      </div>
    </transition>
  </header>
</template>

<script setup lang="ts">
import { useAppStore } from '@/stores';

const appStore = useAppStore();

const toggleMobileMenu = () => {
  appStore.toggleMobileMenu();
};

const closeMobileMenu = () => {
  appStore.closeMobileMenu();
};
</script>

<style scoped>
.app-header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: var(--header-height);
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-dark) 100%);
  box-shadow: 0 2px 12px rgba(208, 48, 80, 0.2);
  z-index: var(--z-fixed);
}

.header-container {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 100%;
}

.header-left {
  display: flex;
  align-items: center;
}

.logo {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  text-decoration: none;
  transition: transform var(--transition-fast);
}

.logo:hover {
  transform: scale(1.02);
}

.logo-icon {
  width: 40px;
  height: 40px;
  background: var(--color-white);
  border-radius: var(--border-radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-primary);
  font-weight: var(--font-weight-bold);
  font-size: var(--font-size-lg);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.logo-text {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-white);
}

.header-nav {
  display: flex;
  align-items: center;
  gap: var(--spacing-2xl);
}

.nav-link {
  position: relative;
  padding: var(--spacing-sm) 0;
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-medium);
  color: rgba(255, 255, 255, 0.85);
  text-decoration: none;
  transition: color var(--transition-fast);
}

.nav-link::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  width: 0;
  height: 2px;
  background-color: var(--color-white);
  transition: width var(--transition-fast);
}

.nav-link:hover,
.nav-link.router-link-active {
  color: var(--color-white);
}

.nav-link.router-link-active::after {
  width: 100%;
}

.header-right {
  display: flex;
  align-items: center;
  gap: var(--spacing-lg);
}

.menu-button {
  background: none;
  border: none;
  cursor: pointer;
  padding: var(--spacing-sm);
}

.menu-icon {
  display: block;
  width: 24px;
  height: 2px;
  background-color: var(--color-white);
  position: relative;
}

.menu-icon::before,
.menu-icon::after {
  content: '';
  position: absolute;
  width: 100%;
  height: 2px;
  background-color: var(--color-white);
  left: 0;
  transition: transform var(--transition-fast);
}

.menu-icon::before {
  top: -8px;
}

.menu-icon::after {
  bottom: -8px;
}

.mobile-menu {
  position: absolute;
  top: var(--header-height);
  left: 0;
  right: 0;
  background-color: var(--bg-primary);
  box-shadow: var(--shadow-medium);
  padding: var(--spacing-lg);
}

.mobile-nav {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
}

.mobile-nav-link {
  padding: var(--spacing-md);
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-medium);
  color: var(--text-primary);
  text-decoration: none;
  border-radius: var(--border-radius-md);
  transition: background-color var(--transition-fast);
}

.mobile-nav-link:hover,
.mobile-nav-link.router-link-active {
  background-color: rgba(208, 48, 80, 0.1);
  color: var(--color-primary);
}

.slide-enter-active,
.slide-leave-active {
  transition: all 0.3s;
}

.slide-enter-from,
.slide-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

@media (max-width: 768px) {
  .logo-text {
    font-size: var(--font-size-base);
  }
}
</style>
