/**
 * 环境配置管理
 */

export const env = {
  // API基础URL
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || 'http://localhost:11528',

  // 应用标题
  appTitle: import.meta.env.VITE_APP_TITLE || '思政课智能案例系统',

  // 是否使用Mock数据
  useMock: import.meta.env.VITE_USE_MOCK === 'true',

  // 是否为开发环境
  isDev: import.meta.env.DEV,

  // 是否为生产环境
  isProd: import.meta.env.PROD
}

// 打印当前环境配置（仅开发环境）
if (env.isDev) {
  console.log('🔧 Environment Config:', {
    apiBaseUrl: env.apiBaseUrl,
    useMock: env.useMock,
    mode: import.meta.env.MODE
  })
}
