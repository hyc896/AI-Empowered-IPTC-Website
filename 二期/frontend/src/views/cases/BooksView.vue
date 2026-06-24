<template>
  <div class="books-view">
    <div class="header">
      <el-button text style="color:rgba(255,255,255,0.6)" @click="router.push('/case-platform')">← 返回</el-button>
      <span class="title">知识图谱</span>
    </div>
    <div class="books-wrap">
      <h2 class="section-title">选择教材，探索知识点图谱</h2>
      <div class="books-grid">
        <div v-for="book in books" :key="book.book_id" class="book-card" @click="openGraph(book.book_id)">
          <div class="book-icon">📚</div>
          <h3>{{ book.book_name }}</h3>
          <div class="book-stats">
            <span>{{ book.chapter_count }} 章</span>
            <span>·</span>
            <span>{{ book.kp_count }} 知识点</span>
          </div>
          <div class="book-arrow">点击进入图谱 →</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { graphAPI } from '@/api/index'

const router = useRouter()
const books = ref([])

// 合并马克思主义两个book_id
const MARX_IDS = new Set(['marx_principles_2023', 'marx_basic_principles_2023'])

onMounted(async () => {
  try {
    const res = await graphAPI.getBooks()
    const raw = res.code === 200 ? res.data : (res.data || res || [])
    // 合并马克思主义
    const merged = {}
    raw.forEach(b => {
      const key = MARX_IDS.has(b.book_id) ? 'marx_basic_principles_2023' : b.book_id
      if (!merged[key]) {
        merged[key] = { ...b, book_id: key, book_name: MARX_IDS.has(b.book_id) ? '马克思主义基本原理（2023年版）' : b.book_name }
      } else {
        merged[key].chapter_count += b.chapter_count
        merged[key].kp_count += b.kp_count
      }
    })
    books.value = Object.values(merged)
  } catch (e) {
    books.value = []
  }
})

function openGraph(bookId) {
  // 马克思主义用完整版ID
  const id = bookId === 'marx_basic_principles_2023' ? bookId : bookId
  router.push(`/case-platform/graph?book=${id}`)
}
</script>

<style scoped>
.books-view {
  min-height: 100vh;
  background: url('@/assets/bg-main.webp') center/cover no-repeat fixed;
  color: #fff;
}
.header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px 48px;
  background: rgba(0,0,0,0.4);
  backdrop-filter: blur(12px);
}
.title { font-size: 18px; font-weight: 700; color: #ffd700; }
.books-wrap {
  max-width: 900px;
  margin: 60px auto;
  padding: 0 24px;
}
.section-title {
  text-align: center;
  font-size: 24px;
  color: #ffd700;
  margin-bottom: 48px;
}
.books-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 24px;
}
.book-card {
  background: rgba(0,0,0,0.5);
  border: 1px solid rgba(192,57,43,0.3);
  border-radius: 12px;
  padding: 32px 24px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 12px;
}
.book-card:hover {
  border-color: rgba(255,215,0,0.5);
  background: rgba(192,57,43,0.15);
  transform: translateY(-4px);
}
.book-icon { font-size: 48px; }
.book-card h3 { font-size: 16px; font-weight: 700; color: #fff; line-height: 1.5; }
.book-stats { font-size: 13px; color: rgba(255,255,255,0.5); display: flex; gap: 8px; }
.book-arrow { font-size: 13px; color: #ffd700; margin-top: 8px; }
</style>
