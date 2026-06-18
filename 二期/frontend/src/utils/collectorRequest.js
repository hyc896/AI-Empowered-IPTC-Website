import axios from 'axios'

// 一期后端的请求实例（通过 nginx 代理到 collector-backend:11528）
const collectorRequest = axios.create({
  baseURL: '/api/v1',
  timeout: 30000
})

collectorRequest.interceptors.response.use(
  response => response.data,
  error => Promise.reject(error)
)

export default collectorRequest
