<template>
  <div class="not-found-view">
    <div class="container">
      <div class="not-found-content">
        <div class="error-code">404</div>
        <h1 class="error-title">页面未找到</h1>
        <p class="error-description">
          抱歉，您访问的页面不存在或已被移除。
        </p>
        <base-button type="primary" size="large" @click="goHome">
          返回首页
        </base-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router';
import BaseButton from '@/components/ui/BaseButton.vue';

const router = useRouter();

const goHome = () => {
  router.push('/');
};
</script>

<style scoped>
.not-found-view {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-accent) 100%);
}

.not-found-content {
  text-align: center;
  color: var(--color-white);
  padding: var(--spacing-4xl);
}

.error-code {
  font-size: 120px;
  font-weight: var(--font-weight-bold);
  line-height: 1;
  margin-bottom: var(--spacing-xl);
  opacity: 0.9;
}

.error-title {
  font-size: var(--font-size-3xl);
  font-weight: var(--font-weight-bold);
  margin-bottom: var(--spacing-lg);
}

.error-description {
  font-size: var(--font-size-lg);
  margin-bottom: var(--spacing-2xl);
  opacity: 0.9;
}

@media (max-width: 768px) {
  .error-code {
    font-size: 80px;
  }

  .error-title {
    font-size: var(--font-size-2xl);
  }
}
</style>
