<template>
  <div class="messages-view">
    <div class="messages-header">
      <div class="header-left">
        <el-select
          v-model="filterSourceId"
          placeholder="全部来源"
          clearable
          style="width: 200px"
          @change="handleFilterChange"
        >
          <el-option
            v-for="source in sources"
            :key="source.id"
            :label="source.display_name || source.name"
            :value="source.id"
          />
        </el-select>
        <el-input
          v-model="keyword"
          placeholder="搜索消息..."
          clearable
          style="width: 300px"
          :prefix-icon="Search"
          @change="handleFilterChange"
        />
      </div>
    </div>
    <div class="messages-stats">
      <el-card shadow="never">
        <el-statistic title="总消息" :value="stats.total_messages || 0" />
      </el-card>
      <el-card shadow="never">
        <el-statistic title="消息源" :value="stats.total_sources || 0" />
      </el-card>
      <el-card shadow="never">
        <el-statistic title="活跃源" :value="stats.active_sources || 0" />
      </el-card>
    </div>
    <div v-loading="loading" class="messages-list">
      <MessageCard
        v-for="message in messages"
        :key="message.id"
        :message="message"
        @view="handleViewMessage"
      />
    </div>
    <div class="messages-pagination">
      <el-pagination
        v-model:current-page="currentPage"
        :page-size="pageSize"
        :total="total"
        layout="prev, pager, next, total"
        @current-change="handlePageChange"
      />
    </div>

    <el-drawer
      v-model="drawerVisible"
      title="消息详情"
      size="50%"
    >
      <div v-if="selectedMessage" class="message-detail">
        <h2>{{ selectedMessage.title }}</h2>
        <div class="message-meta">
          <span v-if="selectedMessage.author">作者: {{ selectedMessage.author }}</span>
          <span v-if="selectedMessage.published_at">
            发布时间: {{ formatDate(selectedMessage.published_at) }}
          </span>
        </div>
        <div class="message-content">
          <MarkdownRenderer :content="selectedMessage.content" />
        </div>
        <div v-if="selectedMessage.url" class="message-link">
          <el-link :href="selectedMessage.url" target="_blank" type="primary">
            查看原文
          </el-link>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Search } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useMessageStore } from '@/stores'
import type { Message } from '@/types/models'
import { formatDate } from '@/utils/date'
import MessageCard from '@/components/common/MessageCard.vue'
import MarkdownRenderer from '@/components/common/MarkdownRenderer.vue'

const messageStore = useMessageStore()

// 只显示活跃的消息源
const sources = computed(() => messageStore.activeSources)
const messages = computed(() => messageStore.messages)
const total = computed(() => messageStore.total)
const stats = computed(() => messageStore.stats)

const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(20)
const filterSourceId = ref<string | undefined>()
const keyword = ref('')

const drawerVisible = ref(false)
const selectedMessage = ref<Message | null>(null)

onMounted(async () => {
  await messageStore.fetchMessageSources()
  await fetchData()
  await messageStore.fetchMessageStats()
})

const fetchData = async () => {
  loading.value = true
  try {
    await messageStore.fetchMessages({
      limit: pageSize.value,
      offset: (currentPage.value - 1) * pageSize.value,
      source_id: filterSourceId.value,
      keyword: keyword.value || undefined
    })
  } catch (error) {
    ElMessage.error('加载消息失败')
  } finally {
    loading.value = false
  }
}

const handleFilterChange = () => {
  currentPage.value = 1
  fetchData()
}

const handlePageChange = () => {
  fetchData()
}

const handleViewMessage = (message: Message) => {
  selectedMessage.value = message
  drawerVisible.value = true
}
</script>

<style scoped lang="scss">
.messages-view {
  padding: 20px;

  .messages-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 20px;

    .header-left {
      display: flex;
      gap: 12px;
    }
  }

  .messages-stats {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 16px;
    margin-bottom: 20px;
  }

  .messages-list {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
    gap: 16px;
    margin-bottom: 20px;
  }

  .messages-pagination {
    display: flex;
    justify-content: center;
  }
}

.message-detail {
  h2 {
    font-size: 24px;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 16px;
  }

  .message-meta {
    display: flex;
    gap: 24px;
    font-size: 14px;
    color: var(--text-secondary);
    margin-bottom: 24px;
  }

  .message-content {
    margin-bottom: 24px;
  }

  .message-link {
    text-align: center;
  }
}
</style>
