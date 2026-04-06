<template>
  <div class="showcase-wall">
    <div class="page-header">
      <h2>优秀作品墙</h2>
    </div>

    <!-- 筛选 -->
    <el-card class="filter-card">
      <el-radio-group v-model="typeFilter" @change="fetchShowcase">
        <el-radio-button label="">全部</el-radio-button>
        <el-radio-button v-for="t in practiceTypes" :key="t.value" :label="t.value">{{ t.label }}</el-radio-button>
      </el-radio-group>
    </el-card>

    <!-- 作品列表 -->
    <PageLoading v-if="loading" />
    <div v-else class="showcase-grid">
      <el-empty v-if="list.length === 0" description="暂无优秀作品" />

      <el-card v-for="item in list" :key="item.id" class="showcase-card" shadow="hover" @click="viewDetail(item)">
        <!-- 封面图 -->
        <div class="card-cover">
          <el-image
            v-if="getCoverImage(item)"
            :src="getCoverImage(item)"
            fit="cover"
            class="cover-image"
          />
          <div v-else class="cover-placeholder">
            <el-icon :size="48"><Document /></el-icon>
          </div>
          <div class="cover-overlay">
            <el-tag :type="typeTag(item.practice_type)" size="small">{{ typeLabel(item.practice_type) }}</el-tag>
          </div>
        </div>

        <!-- 内容 -->
        <div class="card-content">
          <div class="card-title">{{ item.title }}</div>
          <div class="card-author">
            <el-icon><User /></el-icon>
            <span>{{ item.user_name || '匿名' }}</span>
          </div>
          <div class="card-excerpt">{{ getExcerpt(item.reflection) }}</div>
          <div class="card-footer">
            <div class="card-score">
              <el-icon><Star /></el-icon>
              <span>{{ item.review?.score || '-' }} 分</span>
            </div>
            <div class="card-date">{{ formatDate(item.submitted_at) }}</div>
          </div>
        </div>
      </el-card>
    </div>

    <el-pagination
      v-if="total > pageSize"
      v-model:current-page="page"
      :page-size="pageSize"
      :total="total"
      layout="prev, pager, next"
      class="pagination"
      @current-change="fetchShowcase"
    />

    <!-- 详情对话框 -->
    <el-dialog v-model="showDetail" :title="selectedItem?.title" width="800px" top="5vh">
      <div v-if="selectedItem" class="detail-content">
        <el-descriptions :column="2" border size="small" style="margin-bottom:16px">
          <el-descriptions-item label="作者">{{ selectedItem.user_name || '匿名' }}</el-descriptions-item>
          <el-descriptions-item label="实践类型">{{ typeLabel(selectedItem.practice_type) }}</el-descriptions-item>
          <el-descriptions-item label="完成日期">{{ formatDate(selectedItem.completion_date) }}</el-descriptions-item>
          <el-descriptions-item label="评分">{{ selectedItem.review?.score || '-' }} 分</el-descriptions-item>
        </el-descriptions>

        <div class="detail-section">
          <h4>实践内容</h4>
          <div class="detail-text">{{ selectedItem.content }}</div>
        </div>

        <div class="detail-section" v-if="selectedItem.reflection">
          <h4>实践感想</h4>
          <div class="detail-text">{{ selectedItem.reflection }}</div>
        </div>

        <div class="detail-section" v-if="selectedItem.review?.comment">
          <h4>教师评语</h4>
          <div class="detail-text review-comment">{{ selectedItem.review.comment }}</div>
        </div>

        <div class="detail-section" v-if="selectedItem.files?.length">
          <h4>附件材料</h4>
          <div class="files-grid">
            <el-image
              v-for="file in getImages(selectedItem.files)"
              :key="file.path"
              :src="file.path"
              :preview-src-list="getImages(selectedItem.files).map(f => f.path)"
              fit="cover"
              class="file-image"
            />
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { submissionAPI } from '@/api'
import PageLoading from '@/components/PageLoading.vue'

const loading = ref(false)
const list = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(12)
const typeFilter = ref('')
const showDetail = ref(false)
const selectedItem = ref(null)

const practiceTypes = [
  { value: 'writing', label: '写作设计' },
  { value: 'presentation', label: '宣传表达' },
  { value: 'visit', label: '参观研学' },
  { value: 'performance', label: '表演体验' },
  { value: 'interaction', label: '交往行动' },
  { value: 'production', label: '生产改造' },
  { value: 'free', label: '自由申请' }
]

const typeLabel = (t) => practiceTypes.find(p => p.value === t)?.label || t
const typeTag = (t) => ({ writing:'', presentation:'success', visit:'warning', performance:'danger', interaction:'info', production:'', free:'' }[t] || '')
const formatDate = (d) => d ? new Date(d).toLocaleDateString('zh-CN') : '-'

const getCoverImage = (item) => {
  if (!item.files || item.files.length === 0) return null
  const imageFile = item.files.find(f => f.type?.startsWith('image/'))
  return imageFile?.path || null
}

const getExcerpt = (text) => {
  if (!text) return '暂无感想'
  return text.length > 80 ? text.substring(0, 80) + '...' : text
}

const getImages = (files) => {
  if (!files) return []
  return files.filter(f => f.type?.startsWith('image/'))
}

const fetchShowcase = async () => {
  loading.value = true
  try {
    const res = await submissionAPI.getShowcase({
      practice_type: typeFilter.value || undefined,
      page: page.value,
      page_size: pageSize.value
    })
    list.value = res.items
    total.value = res.total
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

const viewDetail = (item) => {
  selectedItem.value = item
  showDetail.value = true
}

onMounted(fetchShowcase)
</script>

<style scoped>
.showcase-wall { width: 100%; }
.page-header { margin-bottom: 20px; }
.page-header h2 { font-size: 22px; color: #333; }
.filter-card { margin-bottom: 20px; }
.showcase-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
  min-height: 400px;
}
.showcase-card { cursor: pointer; transition: transform 0.2s; }
.showcase-card:hover { transform: translateY(-4px); }
.card-cover {
  position: relative;
  width: 100%;
  height: 180px;
  background: #f5f7fa;
  overflow: hidden;
}
.cover-image { width: 100%; height: 100%; }
.cover-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #ccc;
}
.cover-overlay {
  position: absolute;
  top: 8px;
  right: 8px;
}
.card-content { padding: 16px; }
.card-title {
  font-size: 16px;
  font-weight: bold;
  color: #333;
  margin-bottom: 8px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.card-author {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: #888;
  margin-bottom: 8px;
}
.card-excerpt {
  font-size: 13px;
  color: #666;
  line-height: 1.6;
  margin-bottom: 12px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: #999;
}
.card-score {
  display: flex;
  align-items: center;
  gap: 4px;
  color: #f39c12;
}
.pagination { margin-top: 20px; justify-content: center; display: flex; }
.detail-content {}
.detail-section { margin-bottom: 20px; }
.detail-section h4 {
  font-size: 15px;
  color: #333;
  margin-bottom: 10px;
  padding-bottom: 6px;
  border-bottom: 1px solid #f0f0f0;
}
.detail-text {
  font-size: 14px;
  color: #555;
  line-height: 1.8;
  white-space: pre-wrap;
}
.review-comment {
  background: #f9f9f9;
  padding: 12px;
  border-radius: 4px;
  border-left: 3px solid #67c23a;
}
.files-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 10px;
}
.file-image {
  width: 100%;
  height: 120px;
  border-radius: 4px;
}
</style>
