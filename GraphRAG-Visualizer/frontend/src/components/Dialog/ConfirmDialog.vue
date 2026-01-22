<!--
确认对话框组件
用于替代原生的 confirm() 和 alert()
-->
<template>
  <Teleport to="body">
    <Transition name="dialog-fade">
      <div v-if="visible" class="dialog-overlay" @click="handleOverlayClick">
        <div class="dialog-container" @click.stop>
          <div class="dialog-header">
            <h3 class="dialog-title">{{ title }}</h3>
            <button class="dialog-close" @click="handleCancel">
              <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M18 6L6 18M6 6l12 12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
              </svg>
            </button>
          </div>

          <div class="dialog-body">
            <p class="dialog-message">{{ message }}</p>
          </div>

          <div class="dialog-footer">
            <button v-if="showCancel" class="dialog-btn dialog-btn-cancel" @click="handleCancel">
              {{ cancelText }}
            </button>
            <button class="dialog-btn dialog-btn-confirm" @click="handleConfirm">
              {{ confirmText }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref } from 'vue';

interface Props {
  title?: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  showCancel?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  title: '提示',
  confirmText: '确定',
  cancelText: '取消',
  showCancel: true
});

const emit = defineEmits<{
  confirm: [];
  cancel: [];
}>();

const visible = ref(false);

function show() {
  visible.value = true;
}

function hide() {
  visible.value = false;
}

function handleConfirm() {
  emit('confirm');
  hide();
}

function handleCancel() {
  emit('cancel');
  hide();
}

function handleOverlayClick() {
  if (props.showCancel) {
    handleCancel();
  }
}

defineExpose({
  show,
  hide
});
</script>

<style scoped>
.dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  backdrop-filter: blur(4px);
}

.dialog-container {
  background: white;
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  min-width: 400px;
  max-width: 500px;
  overflow: hidden;
  animation: dialog-scale-in 0.2s ease-out;
}

@keyframes dialog-scale-in {
  from {
    transform: scale(0.9);
    opacity: 0;
  }
  to {
    transform: scale(1);
    opacity: 1;
  }
}

.dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid #e5e7eb;
}

.dialog-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
}

.dialog-close {
  width: 32px;
  height: 32px;
  border: none;
  background: transparent;
  color: #6b7280;
  cursor: pointer;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.dialog-close:hover {
  background: #f3f4f6;
  color: #1f2937;
}

.dialog-close svg {
  width: 20px;
  height: 20px;
}

.dialog-body {
  padding: 24px;
}

.dialog-message {
  margin: 0;
  font-size: 15px;
  line-height: 1.6;
  color: #4b5563;
}

.dialog-footer {
  display: flex;
  gap: 12px;
  padding: 16px 24px;
  background: #f9fafb;
  justify-content: flex-end;
}

.dialog-btn {
  padding: 10px 20px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  min-width: 80px;
}

.dialog-btn-cancel {
  background: white;
  color: #6b7280;
  border: 1px solid #d1d5db;
}

.dialog-btn-cancel:hover {
  background: #f9fafb;
  border-color: #9ca3af;
}

.dialog-btn-confirm {
  background: #3b82f6;
  color: white;
}

.dialog-btn-confirm:hover {
  background: #2563eb;
}

/* 淡入淡出动画 */
.dialog-fade-enter-active,
.dialog-fade-leave-active {
  transition: opacity 0.2s ease;
}

.dialog-fade-enter-from,
.dialog-fade-leave-to {
  opacity: 0;
}
</style>
