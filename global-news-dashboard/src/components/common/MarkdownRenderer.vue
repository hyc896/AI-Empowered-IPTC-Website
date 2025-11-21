<template>
  <div class="markdown-content" v-html="renderedContent"></div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { renderMarkdown } from '@/utils/markdown'

const props = defineProps<{
  content: string
}>()

const renderedContent = computed(() => {
  return renderMarkdown(props.content)
})
</script>

<style lang="scss">
.markdown-content {
  color: var(--text-primary);
  line-height: 1.6;

  h1,
  h2,
  h3,
  h4,
  h5,
  h6 {
    margin: 16px 0 8px;
    font-weight: 600;
  }

  h1 {
    font-size: 28px;
    border-bottom: 1px solid var(--border-base);
    padding-bottom: 8px;
  }

  h2 {
    font-size: 24px;
  }

  h3 {
    font-size: 20px;
  }

  p {
    margin: 8px 0;
    font-size: 16px;
  }

  ul,
  ol {
    margin: 8px 0;
    padding-left: 24px;
  }

  li {
    margin: 4px 0;
    font-size: 16px;
  }

  code {
    padding: 2px 6px;
    background-color: var(--bg-tertiary);
    border-radius: var(--border-radius-base);
    font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
    font-size: 13px;
  }

  pre {
    margin: 12px 0;
    padding: 12px;
    background-color: var(--bg-tertiary);
    border-radius: var(--border-radius-base);
    overflow-x: auto;

    code {
      padding: 0;
      background: none;
    }
  }

  blockquote {
    margin: 12px 0;
    padding: 8px 16px;
    border-left: 4px solid var(--primary-color);
    background-color: var(--bg-secondary);
    color: var(--text-secondary);
  }

  a {
    color: var(--primary-color);
    text-decoration: none;

    &:hover {
      text-decoration: underline;
    }
  }

  table {
    width: 100%;
    margin: 12px 0;
    border-collapse: collapse;

    th,
    td {
      padding: 8px 12px;
      border: 1px solid var(--border-base);
      text-align: left;
    }

    th {
      background-color: var(--bg-secondary);
      font-weight: 600;
    }
  }

  img {
    max-width: 100%;
    height: auto;
    border-radius: var(--border-radius-base);
  }

  hr {
    margin: 16px 0;
    border: none;
    border-top: 1px solid var(--border-base);
  }
}
</style>
