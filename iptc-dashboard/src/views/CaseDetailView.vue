<template>
  <div class="case-detail-view">
    <div class="container">
      <!-- 面包屑导航 -->
      <nav class="breadcrumb">
        <router-link to="/">首页</router-link>
        <span class="separator">/</span>
        <router-link to="/cases">案例库</router-link>
        <span class="separator">/</span>
        <span class="current">案例详情</span>
      </nav>

      <div v-if="caseStore.loading" class="loading-section">
        <div class="loading-animation">
          <div class="flag-wave"></div>
          <div class="loading-text">加载中...</div>
        </div>
      </div>

      <div v-else-if="caseStore.currentCase" class="detail-content">
        <div class="content-card">
          <!-- 标题区 -->
          <div class="title-section">
            <h1 class="case-title">{{ caseStore.currentCase.title }}</h1>
            <div class="case-meta">
              <span class="meta-item">
                <span class="meta-icon">📅</span>
                {{ formatDate(caseStore.currentCase.createdAt, 'YYYY-MM-DD') }}
              </span>
            </div>

            <!-- 来源消息列表（可折叠） -->
            <div v-if="caseStore.currentCase.sourceMessages && caseStore.currentCase.sourceMessages.length > 0" class="source-messages">
              <div class="source-messages-header" @click="toggleSourceMessages">
                <span class="meta-icon">🔗</span>
                <span class="source-messages-title">来源消息 ({{ caseStore.currentCase.sourceMessages.length }}条)</span>
                <span class="toggle-icon">{{ showSourceMessages ? '▼' : '▶' }}</span>
              </div>
              <transition name="slide-fade">
                <div v-show="showSourceMessages" class="source-messages-list">
                  <div
                    v-for="(msg, index) in caseStore.currentCase.sourceMessages"
                    :key="index"
                    class="source-message-item"
                  >
                    <span class="message-index">{{ index + 1 }}.</span>
                    <a
                      v-if="msg.url"
                      :href="msg.url"
                      target="_blank"
                      class="message-link"
                      :title="msg.title"
                    >
                      {{ msg.title }}
                    </a>
                    <span v-else class="message-title-no-link">{{ msg.title }}</span>
                  </div>
                </div>
              </transition>
            </div>

            <div class="case-tags">
              <span
                v-for="kp in caseStore.currentCase.knowledgePoints"
                :key="kp"
                class="case-tag"
              >
                {{ kp }}
              </span>
            </div>
          </div>

          <!-- 可滚动内容区 -->
          <div class="scrollable-content">
            <div class="markdown-body" v-html="renderedContent"></div>
          </div>

          <!-- 操作区 -->
          <div class="actions-section">
            <button class="action-button" @click="shareCase">
              <span>📤</span>
              <span>分享</span>
            </button>
            <button class="action-button" @click="exportPDF">
              <span>📄</span>
              <span>导出PDF</span>
            </button>
            <button class="action-button" @click="printCase">
              <span>🖨️</span>
              <span>打印</span>
            </button>
            <button class="action-button" @click="goBack">
              <span>←</span>
              <span>返回</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useCaseStore } from '@/stores';
import { formatDate } from '@/utils';
import { increaseCaseView } from '@/api';
import BaseButton from '@/components/ui/BaseButton.vue';
import BaseCard from '@/components/ui/BaseCard.vue';
import BaseTag from '@/components/ui/BaseTag.vue';
import { marked } from 'marked';
import html2pdf from 'html2pdf.js';

const route = useRoute();
const router = useRouter();
const caseStore = useCaseStore();

const caseId = computed(() => route.params.id as string);

// 控制来源消息列表的展开/折叠
const showSourceMessages = ref(false);

const toggleSourceMessages = () => {
  showSourceMessages.value = !showSourceMessages.value;
};

// 配置marked
marked.setOptions({
  breaks: true,
  gfm: true,
  headerIds: true,
  mangle: false,
});

// 使用marked渲染Markdown内容
const renderedContent = computed(() => {
  if (!caseStore.currentCase || !caseStore.currentCase.content) return '';
  try {
    // 清理可能存在的markdown代码块包裹
    let content = caseStore.currentCase.content;

    // 移除开头的 ```markdown 或 ```
    content = content.replace(/^```markdown\s*\n/, '');
    content = content.replace(/^```\s*\n/, '');

    // 移除结尾的 ```
    content = content.replace(/\n```\s*$/, '');

    return marked.parse(content);
  } catch (error) {
    console.error('Markdown渲染错误:', error);
    return caseStore.currentCase.content;
  }
});

onMounted(async () => {
  await caseStore.fetchCaseDetail(caseId.value);
});

const goBack = () => {
  router.push('/cases');
};

const shareCase = () => {
  const url = window.location.href;
  navigator.clipboard.writeText(url).then(() => {
    alert('链接已复制到剪贴板');
  });
};

const printCase = () => {
  window.print();
};

const exportPDF = () => {
  if (!caseStore.currentCase) return;

  const element = document.querySelector('.content-card');
  if (!element) return;

  const opt = {
    margin: [10, 10, 10, 10],
    filename: `${caseStore.currentCase.title}.pdf`,
    image: { type: 'jpeg', quality: 0.98 },
    html2canvas: {
      scale: 2,
      useCORS: true,
      letterRendering: true,
      scrollY: 0,
      scrollX: 0
    },
    jsPDF: {
      unit: 'mm',
      format: 'a4',
      orientation: 'portrait'
    },
    pagebreak: { mode: ['avoid-all', 'css', 'legacy'] }
  };

  html2pdf().set(opt).from(element).save();
};
</script>

<style scoped>
/* 固定高度，不允许整体滚动 */
.case-detail-view {
  height: 100vh;
  overflow: hidden;
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: calc(var(--header-height) + 24px) 24px 24px;
  height: 100%;
  display: flex;
  flex-direction: column;
}

/* 面包屑导航 */
.breadcrumb {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 24px;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.7);
  flex-shrink: 0;
}

.breadcrumb a {
  color: #FFD700;
  text-decoration: none;
  transition: color 0.3s ease;
}

.breadcrumb a:hover {
  color: #FFF;
}

.separator {
  color: rgba(255, 255, 255, 0.5);
}

.current {
  color: rgba(255, 255, 255, 0.9);
}

/* 加载动画 */
.loading-section {
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: center;
}

.loading-animation {
  text-align: center;
}

.flag-wave {
  width: 80px;
  height: 80px;
  margin: 0 auto 24px;
  background: linear-gradient(135deg, #D03050, #FFD700);
  border-radius: 12px;
  animation: waveFlag 1.5s ease-in-out infinite;
}

@keyframes waveFlag {
  0%, 100% {
    transform: rotate(0deg) scale(1);
  }
  50% {
    transform: rotate(10deg) scale(1.1);
  }
}

.loading-text {
  font-size: 20px;
  color: white;
  font-weight: 600;
  letter-spacing: 2px;
}

/* 详情内容容器 */
.detail-content {
  flex: 1;
  overflow: hidden;
  display: flex;
  justify-content: center;
  align-items: flex-start;
}

/* 内容卡片 - 纸质风格 */
.content-card {
  width: 100%;
  max-width: 900px;
  height: 100%;
  background: linear-gradient(135deg, #fffef8 0%, #fefefe 100%);
  border-radius: 8px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  box-shadow:
    0 2px 8px rgba(0, 0, 0, 0.08),
    0 8px 24px rgba(0, 0, 0, 0.12),
    inset 0 0 60px rgba(255, 253, 245, 0.6);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative;
}

/* 纸张纹理效果 */
.content-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-image:
    repeating-linear-gradient(
      0deg,
      transparent,
      transparent 2px,
      rgba(0, 0, 0, 0.01) 2px,
      rgba(0, 0, 0, 0.01) 4px
    );
  pointer-events: none;
  opacity: 0.3;
}

/* 标题区 */
.title-section {
  padding: 32px 32px 24px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.1);
  flex-shrink: 0;
  position: relative;
  z-index: 1;
}

.case-title {
  font-size: 32px;
  font-weight: 700;
  color: #1a1a1a;
  margin-bottom: 16px;
  line-height: 1.4;
  text-shadow: none;
}

.case-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  margin-bottom: 16px;
  font-size: 14px;
  color: #666;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.meta-icon {
  font-size: 16px;
}

.meta-item a {
  color: #0066cc;
  text-decoration: none;
  transition: color 0.3s ease;
}

.meta-item a:hover {
  color: #004499;
  text-decoration: underline;
}

.case-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

/* 来源消息列表样式 */
.source-messages {
  margin-top: 16px;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 8px;
  border: 1px solid #e0e0e0;
}

.source-messages-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: #333;
  cursor: pointer;
  user-select: none;
  padding: 4px;
  border-radius: 4px;
  transition: background 0.2s ease;
}

.source-messages-header:hover {
  background: rgba(0, 102, 204, 0.05);
}

.source-messages-header:active {
  background: rgba(0, 102, 204, 0.1);
}

.source-messages-title {
  color: #0066cc;
  flex: 1;
}

.toggle-icon {
  color: #0066cc;
  font-size: 12px;
  transition: transform 0.3s ease;
}

.source-messages-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 12px;
}

/* 折叠/展开动画 */
.slide-fade-enter-active {
  transition: all 0.3s ease-out;
}

.slide-fade-leave-active {
  transition: all 0.2s ease-in;
}

.slide-fade-enter-from {
  opacity: 0;
  transform: translateY(-10px);
}

.slide-fade-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

.source-message-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 8px;
  background: white;
  border-radius: 4px;
  transition: background 0.2s ease;
}

.source-message-item:hover {
  background: #f0f7ff;
}

.message-index {
  flex-shrink: 0;
  color: #666;
  font-size: 13px;
  font-weight: 600;
  min-width: 24px;
}

.message-link {
  color: #0066cc;
  text-decoration: none;
  font-size: 14px;
  line-height: 1.5;
  transition: color 0.2s ease;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.message-link:hover {
  color: #004499;
  text-decoration: underline;
}

.message-title-no-link {
  color: #666;
  font-size: 14px;
  line-height: 1.5;
}

.case-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.case-tag {
  background: #f0f7ff;
  color: #0066cc;
  padding: 6px 14px;
  border-radius: 16px;
  font-size: 13px;
  font-weight: 600;
  border: 1px solid #cce5ff;
  letter-spacing: 0.5px;
}

/* 可滚动内容区 */
.scrollable-content {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 32px;
  position: relative;
  z-index: 1;
  max-width: 100%;
}

.scrollable-content::-webkit-scrollbar {
  width: 8px;
}

.scrollable-content::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.05);
  border-radius: 4px;
}

.scrollable-content::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 4px;
  transition: background 0.3s ease;
}

.scrollable-content::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.3);
}

.markdown-body {
  font-size: 16px;
  line-height: 1.8;
  color: #2c3e50;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  max-width: 100%;
  overflow-wrap: break-word;
  word-wrap: break-word;
  word-break: break-word;
}

/* Markdown样式增强 */
.markdown-body h1,
.markdown-body h2,
.markdown-body h3,
.markdown-body h4,
.markdown-body h5,
.markdown-body h6 {
  color: #1a1a1a;
  font-weight: 600;
  margin-top: 24px;
  margin-bottom: 16px;
  line-height: 1.3;
  max-width: 100%;
  overflow-wrap: break-word;
}

.markdown-body h1 {
  font-size: 28px;
  border-bottom: 2px solid #e0e0e0;
  padding-bottom: 12px;
}

.markdown-body h2 {
  font-size: 24px;
  border-bottom: 1px solid #e0e0e0;
  padding-bottom: 8px;
}

.markdown-body h3 {
  font-size: 20px;
}

.markdown-body p {
  margin-bottom: 16px;
  text-align: justify;
  max-width: 100%;
  overflow-wrap: break-word;
}

.markdown-body strong {
  color: #1a1a1a;
  font-weight: 600;
}

.markdown-body em {
  font-style: italic;
  color: #555;
}

.markdown-body ul,
.markdown-body ol {
  margin-bottom: 16px;
  padding-left: 32px;
  max-width: 100%;
}

.markdown-body li {
  margin-bottom: 8px;
  overflow-wrap: break-word;
}

.markdown-body blockquote {
  border-left: 4px solid #0066cc;
  background: #f5f9ff;
  padding: 12px 16px;
  margin: 16px 0;
  color: #555;
  max-width: 100%;
  overflow-wrap: break-word;
}

.markdown-body code {
  background: #f5f5f5;
  padding: 2px 6px;
  border-radius: 3px;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 14px;
  color: #d63384;
  white-space: pre-wrap;
  word-wrap: break-word;
  max-width: 100%;
  display: inline-block;
}

.markdown-body pre {
  background: #f5f5f5;
  padding: 16px;
  border-radius: 6px;
  overflow-x: auto;
  margin: 16px 0;
  max-width: 100%;
}

.markdown-body pre code {
  background: none;
  padding: 0;
  color: #2c3e50;
  white-space: pre-wrap;
  word-break: break-all;
}

.markdown-body a {
  color: #0066cc;
  text-decoration: none;
  word-wrap: break-word;
}

.markdown-body a:hover {
  text-decoration: underline;
}

.markdown-body img {
  max-width: 100%;
  height: auto;
  display: block;
  margin: 16px auto;
}

.markdown-body table {
  width: 100%;
  max-width: 100%;
  border-collapse: collapse;
  margin: 16px 0;
  overflow-x: auto;
  display: block;
}

.markdown-body table th,
.markdown-body table td {
  border: 1px solid #ddd;
  padding: 8px;
  text-align: left;
  word-wrap: break-word;
}

.markdown-body table th {
  background-color: #f5f5f5;
  font-weight: 600;
}

/* 操作区 */
.actions-section {
  display: flex;
  gap: 12px;
  padding: 20px 32px;
  border-top: 1px solid rgba(0, 0, 0, 0.1);
  flex-shrink: 0;
  position: relative;
  z-index: 1;
  background: rgba(255, 255, 255, 0.5);
}

.action-button {
  flex: 1;
  background: #ffffff;
  color: #2c3e50;
  border: 1px solid #d0d0d0;
  border-radius: 6px;
  padding: 12px 20px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.action-button:hover {
  background: #f5f5f5;
  border-color: #0066cc;
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 102, 204, 0.15);
}

.action-button:active {
  transform: translateY(0);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .container {
    padding: calc(var(--header-height) + 16px) 16px 16px;
  }

  .content-card {
    border-radius: 16px;
  }

  .title-section {
    padding: 24px 20px 20px;
  }

  .case-title {
    font-size: 24px;
  }

  .scrollable-content {
    padding: 20px;
  }

  .actions-section {
    padding: 16px 20px;
    flex-wrap: wrap;
  }

  .action-button {
    font-size: 14px;
    padding: 10px 16px;
  }
}

/* 打印样式 */
@media print {
  .case-detail-view {
    position: static;
    height: auto;
    overflow: visible;
  }

  .container {
    height: auto;
    padding: 0;
  }

  .breadcrumb,
  .actions-section {
    display: none;
  }

  .detail-content {
    height: auto;
    overflow: visible;
  }

  .content-card {
    height: auto;
    box-shadow: none;
    border: 1px solid #ddd;
    border-radius: 0;
    max-width: 100%;
  }

  .content-card::before {
    display: none;
  }

  .scrollable-content {
    overflow: visible;
    height: auto;
    max-height: none;
    padding: 20px;
  }

  .markdown-body {
    page-break-inside: avoid;
  }

  .markdown-body h1,
  .markdown-body h2,
  .markdown-body h3 {
    page-break-after: avoid;
  }

  .markdown-body pre,
  .markdown-body blockquote,
  .markdown-body table {
    page-break-inside: avoid;
  }
}
</style>
