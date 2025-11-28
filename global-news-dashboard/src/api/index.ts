import axios, { type AxiosInstance, type AxiosResponse } from 'axios'
import { ElMessage } from 'element-plus'
import { API_TIMEOUT } from '@/constants'

// 使用相对路径，通过Vite proxy转发到后端
// 开发模式：Vite proxy转发 /api -> localhost:11528
// 生产模式：需要Nginx配置proxy
const baseURL = import.meta.env.VITE_API_BASE_URL || ''

const axiosInstance: AxiosInstance = axios.create({
  baseURL,
  timeout: API_TIMEOUT,
  headers: {
    'Content-Type': 'application/json'
  }
})

axiosInstance.interceptors.request.use(
  (config) => {
    return config
  },
  (error) => {
    console.error('Request error:', error)
    return Promise.reject(error)
  }
)

axiosInstance.interceptors.response.use(
  (response: AxiosResponse) => {
    return response
  },
  (error) => {
    const message = error.response?.data?.detail || error.message || '网络错误'
    ElMessage.error(message)
    return Promise.reject(error)
  }
)

export default axiosInstance
