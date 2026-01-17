<template>
  <transition name="fade">
    <div v-if="visible" class="loading-screen">
      <div class="loading-content">
        <div class="spinner-container">
          <div class="spinner"></div>
          <div class="spinner-inner"></div>
        </div>
        <p class="loading-text">{{ text }}</p>
        <p class="loading-tip" v-if="tip">{{ tip }}</p>
      </div>
    </div>
  </transition>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  visible: boolean
  text?: string
  tip?: string
}>(), {
  text: '正在加载...',
  tip: ''
})
</script>

<style scoped lang="scss">
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.loading-screen {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;

  .loading-content {
    text-align: center;
    color: white;

    .spinner-container {
      position: relative;
      width: 80px;
      height: 80px;
      margin: 0 auto 24px;

      .spinner {
        position: absolute;
        width: 80px;
        height: 80px;
        border: 4px solid rgba(255, 255, 255, 0.3);
        border-top-color: white;
        border-radius: 50%;
        animation: spin 1s linear infinite;
      }

      .spinner-inner {
        position: absolute;
        top: 50%;
        left: 50%;
        width: 50px;
        height: 50px;
        margin: -25px 0 0 -25px;
        border: 3px solid transparent;
        border-bottom-color: rgba(255, 255, 255, 0.7);
        border-radius: 50%;
        animation: spin 0.7s linear infinite reverse;
      }
    }

    .loading-text {
      font-size: 18px;
      font-weight: 500;
      margin: 0 0 8px 0;
      animation: pulse 1.5s ease-in-out infinite;
    }

    .loading-tip {
      font-size: 14px;
      opacity: 0.8;
      margin: 0;
    }
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.6; }
  }
}
</style>
