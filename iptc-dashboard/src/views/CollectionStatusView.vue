<template>
  <div class="collection-status-view">
    <CollectionStatus />
  </div>
</template>

<script setup lang="ts">
import CollectionStatus from '@/components/CollectionStatus.vue';
</script>

<style scoped>
.collection-status-view {
  min-height: 100vh;
  background: var(--bg-secondary);
}
</style>
