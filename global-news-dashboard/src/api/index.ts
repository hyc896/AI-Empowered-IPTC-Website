import axios, { type AxiosInstance, type AxiosResponse } from 'axios'
import { ElMessage } from 'element-plus'
import { API_TIMEOUT } from '@/constants'

// 前端通过Vite proxy在服务器内网访问后端
// 浏览器请求 /api/* -> Vite proxy -> localhost:11528/api/*
const baseURL = ''

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
