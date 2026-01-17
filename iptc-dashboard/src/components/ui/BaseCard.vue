<template>
  <div :class="cardClasses" @click="handleClick">
    <slot></slot>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';

interface Props {
  hoverable?: boolean;
  shadow?: 'light' | 'medium' | 'heavy';
  padding?: 'none' | 'small' | 'medium' | 'large';
}

const props = withDefaults(defineProps<Props>(), {
  hoverable: true,
  shadow: 'light',
  padding: 'medium',
});

const emit = defineEmits<{
  (e: 'click', event: MouseEvent): void;
}>();

const cardClasses = computed(() => [
  'base-card',
  `base-card--shadow-${props.shadow}`,
  `base-card--padding-${props.padding}`,
  {
    'base-card--hoverable': props.hoverable,
  },
]);

const handleClick = (event: MouseEvent) => {
  emit('click', event);
};
</script>

<style scoped>
.base-card {
  background: var(--bg-primary);
  border-radius: var(--border-radius-lg);
  transition: all var(--transition-base);
  overflow: hidden;
  border: 1px solid transparent;
}

.base-card--shadow-light {
  box-shadow: var(--shadow-light);
}

.base-card--shadow-medium {
  box-shadow: var(--shadow-medium);
}

.base-card--shadow-heavy {
  box-shadow: var(--shadow-heavy);
}

.base-card--hoverable {
  cursor: pointer;
}

.base-card--hoverable:hover {
  box-shadow: 0 4px 16px rgba(208, 48, 80, 0.15);
  transform: translateY(-2px);
  border-color: var(--color-primary);
}

.base-card--padding-none {
  padding: 0;
}

.base-card--padding-small {
  padding: var(--spacing-lg);
}

.base-card--padding-medium {
  padding: var(--spacing-xl);
}

.base-card--padding-large {
  padding: var(--spacing-2xl);
}
</style>
