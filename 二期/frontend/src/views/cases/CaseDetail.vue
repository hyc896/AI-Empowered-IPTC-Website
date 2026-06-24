<template>
  <div class="case-detail-page">
    <!-- 顶部栏 -->
    <div class="header">
      <el-button text :icon="ArrowLeft" style="color:rgba(255,255,255,0.7)" @click="router.back()">返回案例库</el-button>
      <span class="logo-text">案例详情</span>
      <div></div>
    </div>

    <!-- 加载中 -->
    <div v-if="loading" class="loading-wrap">
      <el-skeleton :rows="10" animated style="max-width:860px;margin:40px auto;padding:0 20px" />
    </div>

    <!-- 404 -->
    <div v-else-if="!caseData" class="empty-wrap">
      <el-empty description="案例不存在或已被删除" />
      <el-button type="primary" style="margin-top:16px" @click="router.push('/cases')">返回案例库</el-button>
    </div>

    <!-- 详情 -->
    <div v-else class="detail-wrap">
      <!-- 知识点标签 -->
      <div class="kp-tags">
        <el-tag
          v-for="kp in caseData.knowledgePoints"
          :key="kp"
          effect="light"
          size="small"
          style="margin-right:6px;background:rgba(192,57,43,0.12);border-color:rgba(192,57,43,0.35);color:#e8b4b8"
        >{{ kp }}</el-tag>
      </div>

      <!-- 标题 -->
      <h1 class="title">{{ caseData.title }}</h1>

      <!-- 元信息 -->
      <div class="meta">
        <span>发布于 {{ formatDate(caseData.publishDate || caseData.createdAt) }}</span>
      </div>

      <!-- 摘要 -->
      <div v-if="caseData.summary" class="summary-block">
        <div class="summary-label">摘要</div>
        <p class="summary-text">{{ caseData.summary }}</p>
      </div>

      <!-- 正文 -->
      <div class="content-block">
        <div class="content-text" v-html="formattedContent"></div>
      </div>

      <!-- 来源新闻 -->
      <div v-if="caseData.sourceMessages && caseData.sourceMessages.length" class="sources-block">
        <div class="section-title">参考新闻来源</div>
        <div
          v-for="msg in caseData.sourceMessages"
          :key="msg.url || msg.title"
          class="source-item"
        >
          <a
            v-if="msg.url"
            :href="msg.url"
            target="_blank"
            rel="noopener noreferrer"
            class="source-title"
          >{{ msg.title }}</a>
          <span v-else class="source-title no-link">{{ msg.title }}</span>
          <span class="source-date">{{ formatDate(msg.published_at) }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft } from '@element-plus/icons-vue'
import { marked } from 'marked'
import { caseAPI } from '@/api/index'

const route = useRoute()
const router = useRouter()

const caseData = ref(null)
const loading = ref(true)

const formatDate = (dateStr) => {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return isNaN(d) ? '' : d.toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric' })
}

const formattedContent = computed(() => {
  if (!caseData.value?.content) return ''
  return marked.parse(caseData.value.content)
})

onMounted(async () => {
  try {
    const res = await caseAPI.getDetail(route.params.id)
    caseData.value = res.data
  } catch (e) {
    caseData.value = null
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.case-detail-page {
  min-height: 100vh;
  background: #1a0a0a;
  color: #e8d5d5;
}

.header {
  background: rgba(0,0,0,0.6);
  backdrop-filter: blur(12px);
  padding: 0 40px;
  height: 60px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid rgba(192,57,43,0.2);
  position: sticky;
  top: 0;
  z-index: 100;
}
.logo-text { color: rgba(255,255,255,0.5); font-size: 14px; }

.loading-wrap, .empty-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 80px 20px;
}

.detail-wrap {
  max-width: 860px;
  margin: 0 auto;
  padding: 48px 20px 80px;
}

.kp-tags { margin-bottom: 16px; }

.title {
  font-size: 28px;
  font-weight: 700;
  color: #fff;
  line-height: 1.4;
  margin-bottom: 16px;
}

.meta {
  font-size: 13px;
  color: rgba(255,255,255,0.35);
  margin-bottom: 32px;
}
.source-link {
  color: rgba(192,57,43,0.7);
  text-decoration: none;
}
.source-link:hover { color: #c0392b; text-decoration: underline; }

.summary-block {
  background: rgba(192,57,43,0.06);
  border-left: 3px solid #c0392b;
  border-radius: 0 8px 8px 0;
  padding: 16px 20px;
  margin-bottom: 32px;
}
.summary-label {
  font-size: 11px;
  font-weight: 600;
  color: #c0392b;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: 8px;
}
.summary-text {
  font-size: 15px;
  color: rgba(255,255,255,0.7);
  line-height: 1.7;
  margin: 0;
}

.content-block {
  margin-bottom: 48px;
}
.content-text {
  font-size: 15px;
  color: rgba(255,255,255,0.75);
  line-height: 1.9;
}
.content-text :deep(p) {
  margin-bottom: 1.2em;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: rgba(255,255,255,0.5);
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(255,255,255,0.08);
}

.sources-block {
  border-top: 1px solid rgba(255,255,255,0.08);
  padding-top: 32px;
}
.source-item {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 10px 0;
  border-bottom: 1px solid rgba(255,255,255,0.05);
  gap: 16px;
}
.source-title {
  font-size: 14px;
  color: rgba(192,57,43,0.8);
  text-decoration: none;
  line-height: 1.5;
  flex: 1;
}
.source-title:hover { color: #c0392b; text-decoration: underline; }
.source-title.no-link { color: rgba(255,255,255,0.5); cursor: default; }
.source-date {
  font-size: 12px;
  color: rgba(255,255,255,0.3);
  flex-shrink: 0;
  white-space: nowrap;
}
</style>
