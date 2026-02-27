<template>
  <div class="book-upload">
    <div class="upload-area" @click="triggerFileInput">
      <input
        ref="fileInput"
        type="file"
        accept=".pdf,.docx,.doc,.epub,.txt"
        @change="handleFileSelect"
        style="display: none"
      />
      <div class="upload-icon">📚</div>
      <p class="upload-text">点击上传书籍</p>
      <p class="upload-hint">支持 PDF、Word、EPUB、TXT 格式</p>
    </div>

    <div v-if="uploading" class="upload-progress">
      <div class="progress-bar">
        <div class="progress-fill" :style="{ width: progress + '%' }"></div>
      </div>
      <p class="progress-text">{{ statusMessage }}</p>
    </div>

    <div v-if="uploadSuccess" class="upload-success">
      <p>✅ 上传成功！正在处理...</p>
    </div>

    <div v-if="uploadError" class="upload-error">
      <p>❌ {{ uploadError }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import axios from 'axios';
import { useGraphStore } from '@/stores';

const graphStore = useGraphStore();

const fileInput = ref<HTMLInputElement | null>(null);
const uploading = ref(false);
const progress = ref(0);
const statusMessage = ref('');
const uploadSuccess = ref(false);
const uploadError = ref('');

const triggerFileInput = () => {
  fileInput.value?.click();
};

const handleFileSelect = async (event: Event) => {
  const target = event.target as HTMLInputElement;
  const file = target.files?.[0];

  if (!file) return;

  uploadSuccess.value = false;
  uploadError.value = '';
  uploading.value = true;
  progress.value = 0;
  statusMessage.value = '正在上传...';

  const formData = new FormData();
  formData.append('file', file);

  try {
    const response = await axios.post(
      'http://localhost:8000/api/upload',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total) {
            progress.value = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          }
        },
      }
    );

    uploadSuccess.value = true;
    statusMessage.value = '上传成功，正在提取知识图谱...';

    // 等待一段时间后刷新书籍列表
    setTimeout(async () => {
      await graphStore.fetchBookList();
      uploading.value = false;
      uploadSuccess.value = false;
      progress.value = 0;
    }, 2000);

  } catch (error: any) {
    uploadError.value = error.response?.data?.detail || '上传失败';
    uploading.value = false;
  }

  // 重置文件输入
  if (target) {
    target.value = '';
  }
};
</script>

<style scoped>
.book-upload {
  width: 100%;
}

.upload-area {
  border: 2px dashed var(--border-color);
  border-radius: var(--border-radius-md);
  padding: var(--spacing-xl);
  text-align: center;
  cursor: pointer;
  transition: all var(--transition-fast);
  background: var(--bg-secondary);
}

.upload-area:hover {
  border-color: var(--color-primary);
  background: var(--bg-primary);
}

.upload-icon {
  font-size: 48px;
  margin-bottom: var(--spacing-md);
}

.upload-text {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
  margin-bottom: var(--spacing-sm);
}

.upload-hint {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}

.upload-progress {
  margin-top: var(--spacing-lg);
}

.progress-bar {
  width: 100%;
  height: 8px;
  background: var(--bg-secondary);
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--color-primary);
  transition: width var(--transition-fast);
}

.progress-text {
  margin-top: var(--spacing-sm);
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  text-align: center;
}

.upload-success,
.upload-error {
  margin-top: var(--spacing-md);
  padding: var(--spacing-md);
  border-radius: var(--border-radius-md);
  text-align: center;
}

.upload-success {
  background: rgba(52, 211, 153, 0.1);
  color: #10b981;
}

.upload-error {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
}
</style>
