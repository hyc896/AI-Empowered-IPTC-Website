/**
 * API 基础配置
 * 配置 axios 实例和请求拦截器
 * 支持通过环境变量动态配置 API 地址和超时时间
 */

import axios from 'axios';

// 从环境变量读取配置，如果未设置则使用默认值
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';
const API_TIMEOUT = Number(import.meta.env.VITE_API_TIMEOUT) || 300000;

const request = axios.create({
  baseURL: API_BASE_URL,
  timeout: API_TIMEOUT, // 5分钟超时，用于处理大型PDF文件
});

request.interceptors.response.use(
  (response) => response.data,
  (error) => {
    console.error('API Error:', error);
    return Promise.reject(error);
  }
);

export default request;
