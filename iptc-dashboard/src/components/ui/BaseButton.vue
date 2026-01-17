<template>
  <button :class="buttonClasses" :disabled="disabled || loading" @click="handleClick">
    <span v-if="loading" class="loading-spinner"></span>
    <slot v-else></slot>
  </button>
</template>

<script setup lang="ts">
import { computed } from 'vue';

interface Props {
  type?: 'primary' | 'secondary' | 'outline' | 'text';
  size?: 'small' | 'medium' | 'large';
  disabled?: boolean;
  loading?: boolean;
  block?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  type: 'primary',
  size: 'medium',
  disabled: false,
  loading: false,
  block: false,
});

const emit = defineEmits<{
  (e: 'click', event: MouseEvent): void;
}>();

const buttonClasses = computed(() => [
  'base-button',
  `base-button--${props.type}`,
  `base-button--${props.size}`,
  {
    'base-button--disabled': props.disabled,
    'base-button--loading': props.loading,
    'base-button--block': props.block,
  },
]);

const handleClick = (event: MouseEvent) => {
  if (!props.disabled && !props.loading) {
    emit('click', event);
  }
};
</script>

<style scoped>
.base-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: var(--border-radius-md);
  font-weight: var(--font-weight-medium);
  cursor: pointer;
  transition: all var(--transition-fast);
  outline: none;
  user-select: none;
}

.base-button--primary {
  background-color: var(--color-primary);
  color: var(--color-white);
}

.base-button--primary:hover:not(:disabled) {
  background-color: var(--color-primary-dark);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(208, 48, 80, 0.3);
}

.base-button--secondary {
  background-color: var(--color-secondary);
  color: var(--color-white);
}

.base-button--secondary:hover:not(:disabled) {
  background-color: #e8a03d;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(240, 173, 78, 0.3);
}

.base-button--outline {
  background-color: transparent;
  border: 2px solid var(--color-primary);
  color: var(--color-primary);
}

.base-button--outline:hover:not(:disabled) {
  background-color: var(--color-primary);
  color: var(--color-white);
}

.base-button--text {
  background-color: transparent;
  color: var(--color-primary);
  padding: 0;
}

.base-button--text:hover:not(:disabled) {
  color: var(--color-primary-dark);
}

.base-button--small {
  padding: var(--spacing-sm) var(--spacing-lg);
  font-size: var(--font-size-sm);
  height: 32px;
}

.base-button--medium {
  padding: var(--spacing-md) var(--spacing-xl);
  font-size: var(--font-size-base);
  height: 40px;
}

.base-button--large {
  padding: var(--spacing-lg) var(--spacing-2xl);
  font-size: var(--font-size-lg);
  height: 48px;
}

.base-button--block {
  width: 100%;
  display: flex;
}

.base-button--disabled,
.base-button--loading {
  opacity: 0.6;
  cursor: not-allowed;
  pointer-events: none;
}

.loading-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid currentColor;
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
