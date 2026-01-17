<template>
  <span :class="tagClasses">
    <slot></slot>
    <button v-if="closable" class="tag-close" @click="handleClose">×</button>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue';

interface Props {
  type?: 'primary' | 'secondary' | 'accent' | 'success' | 'warning' | 'error';
  size?: 'small' | 'medium' | 'large';
  closable?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  type: 'primary',
  size: 'medium',
  closable: false,
});

const emit = defineEmits<{
  (e: 'close'): void;
}>();

const tagClasses = computed(() => [
  'base-tag',
  `base-tag--${props.type}`,
  `base-tag--${props.size}`,
]);

const handleClose = () => {
  emit('close');
};
</script>

<style scoped>
.base-tag {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-xs);
  border-radius: var(--border-radius-sm);
  font-weight: var(--font-weight-medium);
  white-space: nowrap;
  transition: all var(--transition-fast);
}

.base-tag--primary {
  background-color: var(--color-primary);
  color: var(--color-white);
}

.base-tag--secondary {
  background-color: var(--color-secondary);
  color: var(--color-white);
}

.base-tag--accent {
  background-color: var(--color-accent);
  color: var(--color-white);
}

.base-tag--success {
  background-color: var(--color-success);
  color: var(--color-white);
}

.base-tag--warning {
  background-color: var(--color-warning);
  color: var(--color-white);
}

.base-tag--error {
  background-color: var(--color-error);
  color: var(--color-white);
}

.base-tag--small {
  padding: 2px var(--spacing-sm);
  font-size: var(--font-size-xs);
}

.base-tag--medium {
  padding: var(--spacing-xs) var(--spacing-md);
  font-size: var(--font-size-sm);
}

.base-tag--large {
  padding: var(--spacing-sm) var(--spacing-lg);
  font-size: var(--font-size-base);
}

.tag-close {
  background: none;
  border: none;
  color: inherit;
  font-size: 18px;
  line-height: 1;
  cursor: pointer;
  padding: 0;
  margin-left: 2px;
  opacity: 0.7;
  transition: opacity var(--transition-fast);
}

.tag-close:hover {
  opacity: 1;
}
</style>
