<template>
  <div class="markdown-renderer" v-html="renderedContent"></div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { renderMarkdown } from '@/utils/markdown'

const props = defineProps<{
  content: string
}>()

const renderedContent = computed(() => {
  return renderMarkdown(props.content || '')
})
</script>

<style lang="scss">
.markdown-renderer {
  font-size: 15px;
  line-height: 1.8;
  color: #1f2937;

  h1, h2, h3, h4, h5, h6 {
    margin: 24px 0 16px;
    font-weight: 600;
    line-height: 1.4;
  }

  h1 {
    font-size: 28px;
    border-bottom: 2px solid #e5e7eb;
    padding-bottom: 8px;
  }

  h2 {
    font-size: 24px;
  }

  h3 {
    font-size: 20px;
  }

  p {
    margin: 12px 0;
  }

  a {
    color: #3b82f6;
    text-decoration: none;
    &:hover {
      text-decoration: underline;
    }
  }

  ul, ol {
    margin: 12px 0;
    padding-left: 24px;
  }

  li {
    margin: 6px 0;
  }

  code {
    background: #f3f4f6;
    padding: 2px 6px;
    border-radius: 4px;
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 14px;
  }

  pre {
    background: #1f2937;
    padding: 16px;
    border-radius: 8px;
    overflow-x: auto;
    margin: 16px 0;

    code {
      background: none;
      padding: 0;
      color: #fff;
    }
  }

  blockquote {
    border-left: 4px solid #3b82f6;
    padding-left: 16px;
    margin: 16px 0;
    color: #6b7280;
  }

  img {
    max-width: 100%;
    height: auto;
    border-radius: 8px;
    margin: 16px 0;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    margin: 16px 0;
  }

  th, td {
    border: 1px solid #e5e7eb;
    padding: 8px 12px;
    text-align: left;
  }

  th {
    background: #f9fafb;
    font-weight: 600;
  }
}
</style>
