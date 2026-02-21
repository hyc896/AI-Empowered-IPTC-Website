<template>
  <div class="book-select-page">
    <h2 class="page-title">知识图谱</h2>
    <p class="page-subtitle">选择教材，查看知识点图谱</p>
    <div class="books-grid">
      <div
        v-for="book in books"
        :key="book.id"
        class="book-card"
        :class="{ clicking: clickingId === book.id }"
        @click="handleClick(book)"
      >
        <div class="book-cover">
          <img :src="book.cover" :alt="book.name" />
        </div>
        <div class="book-name">{{ book.name }}</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';

const router = useRouter();

const books = [
  { id: 'marx_basic_principles_2023', name: '马克思主义基本原理', cover: '/books/marx.png' },
  { id: 'xi_thought_2023', name: '习近平新时代中国特色社会主义思想概论', cover: '/books/xi.png' },
  { id: 'morality_law_2023', name: '思想道德与法治', cover: '/books/morality.png' },
];

const clickingId = ref<string | null>(null);

function handleClick(book: { id: string }) {
  clickingId.value = book.id;
  setTimeout(() => {
    clickingId.value = null;
    router.push(`/graph/mindmap/${book.id}`);
  }, 200);
}
</script>

<style scoped>
.book-select-page {
  min-height: calc(100vh - var(--header-height));
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 60px 24px;
}

.page-title {
  font-size: 2rem;
  font-weight: var(--font-weight-bold);
  color: #fff;
  margin-bottom: 12px;
  text-shadow: 0 2px 8px rgba(0,0,0,0.5);
}

.page-subtitle {
  font-size: var(--font-size-base);
  color: rgba(255,255,255,0.8);
  margin-bottom: 56px;
}

.books-grid {
  display: flex;
  gap: 48px;
  flex-wrap: wrap;
  justify-content: center;
}

.book-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  cursor: pointer;
  transition: transform 0.25s ease, box-shadow 0.25s ease;
  border-radius: 12px;
  padding: 16px;
  background: rgba(255,255,255,0.15);
  backdrop-filter: blur(8px);
  box-shadow: 0 4px 20px rgba(0,0,0,0.3);
  width: 220px;
}

.book-card:hover {
  transform: translateY(-8px);
  box-shadow: 0 16px 40px rgba(0,0,0,0.4);
  background: rgba(255,255,255,0.22);
}

.book-card.clicking {
  transform: scale(0.95);
}

.book-cover {
  width: 180px;
  height: 240px;
  overflow: hidden;
  border-radius: 6px;
  margin-bottom: 16px;
}

.book-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.book-name {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  color: #fff;
  text-align: center;
  line-height: 1.5;
}
</style>
