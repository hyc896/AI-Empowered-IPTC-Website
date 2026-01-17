import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js'

export const markdownRenderer = new MarkdownIt({
  html: true,
  linkify: true,
  typographer: true,
  highlight: (str, lang) => {
    if (lang && hljs.getLanguage(lang)) {
      try {
        return hljs.highlight(str, { language: lang }).value
      } catch (error) {
        console.error('Highlight error:', error)
      }
    }
    return ''
  }
})

export function renderMarkdown(content: string): string {
  return markdownRenderer.render(content)
}
