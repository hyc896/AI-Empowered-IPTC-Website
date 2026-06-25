import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  server: {
    port: 5715,
    proxy: {
      '/api/v1/iptc': {
        target: 'http://localhost:11528',
        changeOrigin: true
      },
      '/api/v1/knowledge-graph': {
        target: 'http://localhost:11528',
        changeOrigin: true
      },
      '/api': {
        target: 'http://localhost:8001',
        changeOrigin: true
      },
      '/uploads': {
        target: 'http://localhost:8001',
        changeOrigin: true
      },
      // 一期案例平台API代理
      '/case-api': {
        target: 'http://localhost:11528',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/case-api/, '')
      }
    }
  }
})
