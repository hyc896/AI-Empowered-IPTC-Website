<template>
  <div class="app-container">
    <div class="app-header">
      <h1>Global News Dashboard</h1>
      <nav class="app-nav">
        <router-link to="/messages">消息列表</router-link>
        <router-link to="/message-sources">消息源管理</router-link>
        <router-link to="/globe">地球视图</router-link>
      </nav>
    </div>
    <div class="content-wrapper">
      <router-view />
    </div>
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped lang="scss">
.app-container {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100vh;
  overflow: hidden;

  .app-header {
    padding: 16px 24px;
    background: var(--bg-primary);
    border-bottom: 1px solid var(--border-base);
    display: flex;
    align-items: center;
    justify-content: space-between;

    h1 {
      font-size: 20px;
      font-weight: 600;
      color: var(--text-primary);
      margin: 0;
    }

    .app-nav {
      display: flex;
      gap: 24px;

      a {
        color: var(--text-regular);
        text-decoration: none;
        padding: 8px 16px;
        border-radius: 4px;
        transition: all 0.3s;

        &:hover {
          background: var(--bg-secondary);
          color: var(--text-primary);
        }

        &.router-link-active {
          color: var(--primary-color);
          background: var(--bg-secondary);
        }
      }
    }
  }

  .content-wrapper {
    flex: 1;
    overflow-y: auto;
    overflow-x: hidden;
    background: var(--bg-secondary);
  }
}
</style>
