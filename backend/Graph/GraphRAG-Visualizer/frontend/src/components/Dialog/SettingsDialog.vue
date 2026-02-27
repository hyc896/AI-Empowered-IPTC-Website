/**
 * LLM设置弹窗组件
 * 用于配置LLM相关参数
 */

<template>
  <div v-if="visible" class="dialog-overlay" @click.self="handleCancel">
    <div class="dialog-container">
      <div class="dialog-header">
        <h2>LLM 配置</h2>
        <button class="close-btn" @click="handleCancel">×</button>
      </div>

      <div class="dialog-content">
        <div v-if="loading" class="loading-state">
          <p>加载配置中...</p>
        </div>

        <form v-else @submit.prevent="handleSubmit" class="settings-form">
          <div class="form-group">
            <label for="provider">Provider</label>
            <input
              id="provider"
              v-model="formData.provider"
              type="text"
              placeholder="openai"
              required
            />
          </div>

          <div class="form-group">
            <label for="model">Model</label>
            <input
              id="model"
              v-model="formData.model"
              type="text"
              placeholder="qwen-plus"
              required
            />
          </div>

          <div class="form-group">
            <label for="api_key">API Key</label>
            <input
              id="api_key"
              v-model="formData.api_key"
              type="password"
              placeholder="输入API Key"
              required
            />
          </div>

          <div class="form-group">
            <label for="base_url">Base URL</label>
            <input
              id="base_url"
              v-model="formData.base_url"
              type="url"
              placeholder="https://dashscope.aliyuncs.com/compatible-mode/v1"
              required
            />
          </div>

          <div class="form-group">
            <label for="temperature">Temperature</label>
            <input
              id="temperature"
              v-model.number="formData.temperature"
              type="number"
              step="0.1"
              min="0"
              max="2"
              placeholder="0.3"
              required
            />
            <span class="hint">控制输出的随机性 (0-2)</span>
          </div>

          <div class="form-group">
            <label for="max_tokens">Max Tokens</label>
            <input
              id="max_tokens"
              v-model.number="formData.max_tokens"
              type="number"
              min="1"
              max="32000"
              placeholder="4000"
              required
            />
            <span class="hint">最大输出token数</span>
          </div>

          <div v-if="error" class="error-message">
            {{ error }}
          </div>

          <div class="dialog-actions">
            <button type="button" @click="handleCancel" class="btn-cancel">
              取消
            </button>
            <button type="submit" :disabled="saving" class="btn-submit">
              {{ saving ? '保存中...' : '保存' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import axios from 'axios';

const props = defineProps<{
  visible: boolean;
}>();

const emit = defineEmits<{
  close: [];
  saved: [];
}>();

interface LLMConfig {
  provider: string;
  model: string;
  api_key: string;
  base_url: string;
  temperature: number;
  max_tokens: number;
}

const loading = ref(false);
const saving = ref(false);
const error = ref('');

const formData = ref<LLMConfig>({
  provider: 'openai',
  model: 'qwen-plus',
  api_key: '',
  base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
  temperature: 0.3,
  max_tokens: 4000
});

// 监听弹窗显示状态，显示时加载配置
watch(() => props.visible, async (newVal) => {
  if (newVal) {
    await loadConfig();
  }
});

async function loadConfig() {
  loading.value = true;
  error.value = '';

  try {
    const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';
    const response = await axios.get(`${apiBaseUrl}/config/llm`);
    formData.value = response.data;
  } catch (err: any) {
    error.value = '加载配置失败: ' + (err.response?.data?.detail || err.message);
    console.error('加载配置失败:', err);
  } finally {
    loading.value = false;
  }
}

async function handleSubmit() {
  saving.value = true;
  error.value = '';

  try {
    const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';
    await axios.put(`${apiBaseUrl}/config/llm`, formData.value);
    emit('saved');
    emit('close');
  } catch (err: any) {
    error.value = '保存配置失败: ' + (err.response?.data?.detail || err.message);
    console.error('保存配置失败:', err);
  } finally {
    saving.value = false;
  }
}

function handleCancel() {
  emit('close');
}
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
}

.dialog-container {
  background: white;
  border-radius: 12px;
  width: 90%;
  max-width: 600px;
  max-height: 90vh;
  overflow: hidden;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
  display: flex;
  flex-direction: column;
}

.dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem 2rem;
  border-bottom: 1px solid #e8e8e8;
}

.dialog-header h2 {
  margin: 0;
  font-size: 1.5rem;
  color: #333;
}

.close-btn {
  background: none;
  border: none;
  font-size: 2rem;
  color: #999;
  cursor: pointer;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: all 0.2s;
}

.close-btn:hover {
  background: #f5f5f5;
  color: #333;
}

.dialog-content {
  padding: 2rem;
  overflow-y: auto;
  flex: 1;
}

.loading-state {
  text-align: center;
  padding: 2rem;
  color: #666;
}

.settings-form {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-group label {
  font-weight: 600;
  color: #333;
  font-size: 0.95rem;
}

.form-group input {
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 0.95rem;
  transition: all 0.2s;
}

.form-group input:focus {
  outline: none;
  border-color: #147899;
  box-shadow: 0 0 0 3px rgba(20, 120, 153, 0.1);
}

.hint {
  font-size: 0.85rem;
  color: #666;
  font-style: italic;
}

.error-message {
  padding: 1rem;
  background: #fee;
  border: 1px solid #fcc;
  border-radius: 6px;
  color: #c33;
  font-size: 0.9rem;
}

.dialog-actions {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
  margin-top: 1rem;
}

.btn-cancel,
.btn-submit {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 6px;
  font-size: 0.95rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-cancel {
  background: #f5f5f5;
  color: #666;
}

.btn-cancel:hover {
  background: #e8e8e8;
}

.btn-submit {
  background: #147899;
  color: white;
}

.btn-submit:hover:not(:disabled) {
  background: #0f5f7a;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(20, 120, 153, 0.3);
}

.btn-submit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
