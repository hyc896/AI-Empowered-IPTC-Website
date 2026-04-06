import { defineStore } from 'pinia'
import { authAPI } from '@/api'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    user: JSON.parse(localStorage.getItem('user') || 'null')
  }),

  getters: {
    isLoggedIn: (state) => !!state.token,
    isStudent: (state) => state.user?.role === 'student',
    isTeacher: (state) => state.user?.role === 'teacher',
    isAdmin: (state) => state.user?.role === 'admin'
  },

  actions: {
    // 登录
    async login(credentials) {
      const res = await authAPI.login(credentials)
      this.token = res.access_token
      this.user = res.user
      localStorage.setItem('token', res.access_token)
      localStorage.setItem('user', JSON.stringify(res.user))
      return res
    },

    // 登出
    async logout() {
      try {
        await authAPI.logout()
      } finally {
        this.token = ''
        this.user = null
        localStorage.removeItem('token')
        localStorage.removeItem('user')

        // 清理所有后台任务
        const { useTaskStore } = await import('./task')
        const taskStore = useTaskStore()
        taskStore.clearAllTasks()
      }
    },

    // 获取当前用户信息
    async fetchUserInfo() {
      const user = await authAPI.getCurrentUser()
      this.user = user
      localStorage.setItem('user', JSON.stringify(user))
      return user
    }
  }
})
