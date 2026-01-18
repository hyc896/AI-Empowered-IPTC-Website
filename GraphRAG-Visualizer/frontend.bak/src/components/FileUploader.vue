<!--
  文件上传组件
  支持拖拽上传 PDF 文件，并选择页面范围
-->
<template>
  <el-card class="uploader-card">
    <template #header>
      <div class="card-header">
        <span>PDF 文件上传</span>
      </div>
    </template>

    <el-upload
      ref="uploadRef"
      class="upload-demo"
      drag
      :auto-upload="false"
      :on-change="handleFileChange"
      :limit="1"
      accept=".pdf"
    >
      <el-icon class="el-icon--upload"><upload-filled /></el-icon>
      <div class="el-upload__text">
        拖拽 PDF 文件到此处或 <em>点击上传</em>
      </div>
      <template #tip>
        <div class="el-upload__tip">
          仅支持 PDF 格式，文件大小不超过 50MB
        </div>
      </template>
    </el-upload>

    <div v-if="selectedFile" class="file-info">
      <el-divider />
      <p><strong>已选择文件：</strong>{{ selectedFile.name }}</p>

      <div class="page-range">
        <el-form :inline="true">
          <el-form-item label="页面范围">
            <el-input-number
              v-model="pageStart"
              :min="1"
              :max="pageEnd"
              placeholder="起始页"
            />
            <span style="margin: 0 10px">-</span>
            <el-input-number
              v-model="pageEnd"
              :min="pageStart"
              :max="999"
              placeholder="结束页"
            />
          </el-form-item>
        </el-form>
      </div>

      <el-button
        type="primary"
        :loading="uploading"
        @click="handleUpload"
        style="width: 100%"
      >
        {{ uploading ? '上传中...' : '开始上传' }}
      </el-button>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import { uploadPDF } from '../api'
import type { UploadResponse } from '../types'
import type { UploadFile } from 'element-plus'

const emit = defineEmits<{
  (e: 'upload-success', data: UploadResponse): void
}>()

const uploadRef = ref()
const selectedFile = ref<File | null>(null)
const uploading = ref(false)
const pageStart = ref(1)
const pageEnd = ref(20)

const handleFileChange = (file: UploadFile) => {
  if (!file.raw) return

  // 验证文件类型
  if (file.raw.type !== 'application/pdf') {
    ElMessage.error('只能上传 PDF 格式的文件')
    return
  }

  // 验证文件大小（50MB）
  const maxSize = 50 * 1024 * 1024
  if (file.raw.size > maxSize) {
    ElMessage.error('文件大小不能超过 50MB')
    return
  }

  selectedFile.value = file.raw
}

const handleUpload = async () => {
  if (!selectedFile.value) {
    ElMessage.warning('请先选择文件')
    return
  }

  uploading.value = true
  try {
    const response = await uploadPDF(
      selectedFile.value,
      pageStart.value,
      pageEnd.value
    )
    ElMessage.success('文件上传成功')
    emit('upload-success', response)
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '上传失败')
  } finally {
    uploading.value = false
  }
}
</script>

<style scoped>
.uploader-card {
  height: 100%;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.file-info {
  margin-top: 20px;
}

.page-range {
  margin: 15px 0;
}
</style>
