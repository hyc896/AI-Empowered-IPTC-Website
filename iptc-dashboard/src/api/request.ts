/**
 * Axios 配置和拦截器
 */

import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig, AxiosResponse } from 'axios';
import type { ApiResponse } from '@/types';

// 创建 axios 实例
const request: AxiosInstance = axios.create({
  baseURL: 'http://localhost:11528',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
request.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // 可以在这里添加 token
    const token = localStorage.getItem('token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error: AxiosError) => {
    console.error('请求错误:', error);
    return Promise.reject(error);
  }
);

// 响应拦截器
request.interceptors.response.use(
  (response: AxiosResponse<ApiResponse>) => {
    const res = response.data;

    // 如果返回的状态码不是 200，则判断为错误
    if (res.code !== 200 && res.code !== 0) {
      console.error('接口错误:', res.message || 'Error');

      // 可以在这里处理特定错误码
      if (res.code === 401) {
        // 未授权，跳转到登录页
        // router.push('/login');
      }

      return Promise.reject(new Error(res.message || 'Error'));
    }

    return res;
  },
  (error: AxiosError) => {
    console.error('响应错误:', error);

    let message = '网络错误';
    if (error.response) {
      message = `服务器错误: ${error.response.status}`;
    } else if (error.request) {
      message = '网络连接失败';
    }

    return Promise.reject(new Error(message));
  }
);

export default request;
