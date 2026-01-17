<template>
  <div id="app" class="app">
    <!-- 全局革命背景 -->
    <div class="global-revolution-background"></div>
    <div class="global-content-overlay"></div>

    <app-header />
    <main class="app-main">
      <router-view v-slot="{ Component }">
        <transition name="page" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>
    <app-footer />
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue';
import { useUserStore } from '@/stores';
import AppHeader from '@/components/layout/AppHeader.vue';
import AppFooter from '@/components/layout/AppFooter.vue';

const userStore = useUserStore();

onMounted(() => {
  // 初始化用户信息
  userStore.initUserInfo();
});
</script>

<style>
@import '@/styles/index.css';

.app {
  display: flex;
  flex-direction: column;
  height: 100vh;
  position: relative;
  overflow: hidden;
}

/* 全局革命背景 */
.global-revolution-background {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-image: url('/images/revolution-bg.jpg');
  background-size: cover;
  background-position: center;
  background-attachment: fixed;
  z-index: -2;
}

.global-content-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: linear-gradient(
    180deg,
    rgba(0, 0, 0, 0.4) 0%,
    rgba(0, 0, 0, 0.3) 50%,
    rgba(0, 0, 0, 0.5) 100%
  );
  z-index: -1;
}

.app-main {
  flex: 1;
  margin-top: var(--header-height);
  position: relative;
  z-index: 1;
  overflow-y: auto;
  height: calc(100vh - var(--header-height));
}
</style>










