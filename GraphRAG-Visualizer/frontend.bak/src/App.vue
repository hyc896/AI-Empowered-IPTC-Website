<!--
  主应用组件
  GraphRAG Visualizer 主界面
-->
<template>
  <div id="app">
    <el-container class="app-container">
      <!-- 顶部标题栏 -->
      <el-header class="app-header">
        <h1>GraphRAG Visualizer</h1>
        <p>PDF 文本实体提取与知识图谱可视化</p>
      </el-header>

      <!-- 主内容区域 -->
      <el-main class="app-main">
        <el-row :gutter="20">
          <!-- 左侧面板 -->
          <el-col :span="12">
            <div class="left-panel">
              <!-- 文件上传 -->
              <FileUploader @upload-success="handleUploadSuccess" />

              <!-- 文本预览 -->
              <div style="margin-top: 20px">
                <TextPreview
                  :text="uploadedText"
                  :char-count="charCount"
                />
              </div>
            </div>
          </el-col>

          <!-- 右侧面板 -->
          <el-col :span="12">
            <div class="right-panel">
              <el-card>
                <template #header>
                  <span>实体与图谱可视化</span>
                </template>
                <el-empty
                  v-if="!fileId"
                  description="请先上传 PDF 文件"
                />
                <div v-else>
                  <p><strong>文件名：</strong>{{ filename }}</p>
                  <p><strong>总页数：</strong>{{ totalPages }}</p>
                  <p><strong>当前范围：</strong>{{ currentRange }}</p>
                </div>
              </el-card>
            </div>
          </el-col>
        </el-row>
      </el-main>
    </el-container>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import FileUploader from './components/FileUploader.vue'
import TextPreview from './components/TextPreview.vue'
import type { UploadResponse } from './types'

const fileId = ref('')
const filename = ref('')
const totalPages = ref(0)
const currentRange = ref('')
const uploadedText = ref('')
const charCount = ref(0)

const handleUploadSuccess = (data: UploadResponse) => {
  fileId.value = data.file_id
  filename.value = data.filename
  totalPages.value = data.total_pages
  currentRange.value = data.current_range
  uploadedText.value = data.text
  charCount.value = data.char_count
}
</script>

<style scoped>
#app {
  height: 100vh;
  background-color: #f5f5f5;
}

.app-container {
  height: 100%;
}

.app-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  text-align: center;
  padding: 20px;
}

.app-header h1 {
  margin: 0;
  font-size: 28px;
}

.app-header p {
  margin: 5px 0 0 0;
  font-size: 14px;
  opacity: 0.9;
}

.app-main {
  padding: 20px;
}

.left-panel,
.right-panel {
  height: 100%;
}
</style>
