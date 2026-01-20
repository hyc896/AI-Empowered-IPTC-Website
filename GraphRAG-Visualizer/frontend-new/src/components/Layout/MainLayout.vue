<!--
  主布局组件
  提供应用的整体布局结构
-->
<template>
  <el-container class="main-layout">
    <!-- 顶部导航栏 -->
    <el-header class="header">
      <div class="header-content">
        <div class="logo">
          <el-icon :size="28"><Grid /></el-icon>
          <span class="title">GraphRAG 可视化</span>
        </div>
        <div class="header-actions">
          <el-button type="primary" @click="showUploadDialog = true">
            <el-icon><Upload /></el-icon>
            上传 PDF
          </el-button>
        </div>
      </div>
    </el-header>

    <!-- 主内容区 -->
    <el-main class="main-content">
      <slot></slot>
    </el-main>

    <!-- 上传对话框 -->
    <UploadDialog v-model="showUploadDialog" @success="handleUploadSuccess" />
  </el-container>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Grid, Upload } from '@element-plus/icons-vue'
import UploadDialog from '@/components/Upload/UploadDialog.vue'

const showUploadDialog = ref(false)

const handleUploadSuccess = (fileId: string) => {
  showUploadDialog.value = false
  emit('upload-success', fileId)
}

const emit = defineEmits<{
  'upload-success': [fileId: string]
}>()
</script>

<style scoped>
.main-layout {
  height: 100vh;
  background: #f5f7fa;
}

.header {
  background: #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  padding: 0;
}

.header-content {
  height: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 24px;
}

.logo {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 20px;
  font-weight: 600;
  color: #409eff;
}

.main-content {
  padding: 24px;
}
</style>
