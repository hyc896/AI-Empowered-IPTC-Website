import { defineStore } from 'pinia'
import { practiceAPI } from '@/api'
import { ElNotification } from 'element-plus'
import { markRaw } from 'vue'

export const useTaskStore = defineStore('task', {
  state: () => ({
    // { taskId, title, practiceType, status: 'generating'|'success'|'failed', text, step }
    generatingTasks: [],
    // 完成回调（组件注册，用于自动刷新列表）
    _onCompleteCallbacks: []
  }),

  getters: {
    hasGenerating: (state) => state.generatingTasks.some(t => t.status === 'generating'),
    generatingCount: (state) => state.generatingTasks.filter(t => t.status === 'generating').length
  },

  actions: {
    addTask(taskId, title, practiceType) {
      this.generatingTasks.push({
        taskId,
        title,
        practiceType,
        status: 'generating',
        text: '正在分析知识点...',
        step: 0
      })
      this._startPolling(taskId)
      this._startStepAnimation(taskId)
    },

    _startStepAnimation(taskId) {
      const stages = [
        { step: 0, text: '正在分析知识点...', delay: 0 },
        { step: 1, text: '构建方案框架...', delay: 6000 },
        { step: 2, text: 'AI生成详细步骤...', delay: 14000 },
        { step: 3, text: '整理推荐场馆...', delay: 22000 },
        { step: 4, text: '方案即将完成...', delay: 30000 },
        { step: 5, text: '最终检查中...', delay: 36000 },
      ]
      const timers = []
      stages.forEach(({ step, text, delay }) => {
        timers.push(setTimeout(() => {
          const task = this.generatingTasks.find(t => t.taskId === taskId)
          if (task && task.status === 'generating') {
            task.step = step
            task.text = text
          }
        }, delay))
      })
      // store timers on the task for cleanup
      const task = this.generatingTasks.find(t => t.taskId === taskId)
      if (task) task._timers = markRaw(timers)
    },

    _startPolling(taskId) {
      let attempts = 0
      const poll = setInterval(async () => {
        attempts++
        const task = this.generatingTasks.find(t => t.taskId === taskId)
        if (!task || task.status !== 'generating') {
          clearInterval(poll)
          return
        }
        if (attempts > 60) {
          this._finishTask(taskId, 'failed', '生成超时')
          clearInterval(poll)
          return
        }
        try {
          const res = await practiceAPI.getTaskStatus(taskId)
          if (res.status === 'success') {
            clearInterval(poll)
            this._finishTask(taskId, 'success')
          } else if (res.status === 'failed') {
            clearInterval(poll)
            this._finishTask(taskId, 'failed', res.error_message || '生成失败')
          }
        } catch (e) {
          // 网络错误，继续轮询（但如果是403权限错误则停止）
          if (e.response?.status === 403) {
            clearInterval(poll)
            this._finishTask(taskId, 'failed', '权限不足')
          }
        }
      }, 3000)
      // 存储 interval ID 以便清理
      const task = this.generatingTasks.find(t => t.taskId === taskId)
      if (task) task._pollInterval = markRaw(poll)
    },

    _finishTask(taskId, status, errorMsg) {
      const task = this.generatingTasks.find(t => t.taskId === taskId)
      if (!task) return
      // cleanup timers
      if (task._timers) {
        task._timers.forEach(t => clearTimeout(t))
      }
      // cleanup polling interval
      if (task._pollInterval) {
        clearInterval(task._pollInterval)
      }
      task.status = status
      task.text = status === 'success' ? '生成完成' : (errorMsg || '生成失败')

      if (status === 'success') {
        ElNotification({
          title: '方案生成完成',
          message: `「${task.title || '实践方案'}」已生成，点击"我的实践"查看`,
          type: 'success',
          duration: 8000
        })
      } else {
        ElNotification({
          title: '方案生成失败',
          message: errorMsg || '请稍后重试',
          type: 'error',
          duration: 8000
        })
      }

      // 触发完成回调（用于自动刷新列表等）
      this._onCompleteCallbacks.forEach(cb => cb(taskId, status))

      // 5秒后从列表移除已完成/失败的任务
      setTimeout(() => {
        const idx = this.generatingTasks.findIndex(t => t.taskId === taskId)
        if (idx !== -1) this.generatingTasks.splice(idx, 1)
      }, 5000)
    },

    onComplete(callback) {
      this._onCompleteCallbacks.push(callback)
      return () => {
        const idx = this._onCompleteCallbacks.indexOf(callback)
        if (idx !== -1) this._onCompleteCallbacks.splice(idx, 1)
      }
    },

    removeTask(taskId) {
      const idx = this.generatingTasks.findIndex(t => t.taskId === taskId)
      if (idx !== -1) {
        const task = this.generatingTasks[idx]
        // 清理定时器和轮询
        if (task._timers) {
          task._timers.forEach(t => clearTimeout(t))
        }
        if (task._pollInterval) {
          clearInterval(task._pollInterval)
        }
        this.generatingTasks.splice(idx, 1)
      }
    },

    // 清理所有任务（用于登出时）
    clearAllTasks() {
      this.generatingTasks.forEach(task => {
        if (task._timers) {
          task._timers.forEach(t => clearTimeout(t))
        }
        if (task._pollInterval) {
          clearInterval(task._pollInterval)
        }
      })
      this.generatingTasks = []
      this._onCompleteCallbacks = []
    }
  }
})
