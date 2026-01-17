/**
 * 用户 Store
 */

import { defineStore } from 'pinia';
import { ref } from 'vue';
import type { UserInfo } from '@/types';

export const useUserStore = defineStore('user', () => {
  // 状态
  const userInfo = ref<UserInfo | null>(null);
  const token = ref<string | null>(localStorage.getItem('token'));
  const isLoggedIn = ref(!!token.value);

  // 登录
  function login(userData: UserInfo, userToken: string) {
    userInfo.value = userData;
    token.value = userToken;
    isLoggedIn.value = true;
    localStorage.setItem('token', userToken);
    localStorage.setItem('userInfo', JSON.stringify(userData));
  }

  // 登出
  function logout() {
    userInfo.value = null;
    token.value = null;
    isLoggedIn.value = false;
    localStorage.removeItem('token');
    localStorage.removeItem('userInfo');
  }

  // 初始化用户信息
  function initUserInfo() {
    const storedUserInfo = localStorage.getItem('userInfo');
    if (storedUserInfo) {
      try {
        userInfo.value = JSON.parse(storedUserInfo);
      } catch (error) {
        console.error('解析用户信息失败:', error);
      }
    }
  }

  // 更新用户信息
  function updateUserInfo(data: Partial<UserInfo>) {
    if (userInfo.value) {
      userInfo.value = { ...userInfo.value, ...data };
      localStorage.setItem('userInfo', JSON.stringify(userInfo.value));
    }
  }

  return {
    userInfo,
    token,
    isLoggedIn,
    login,
    logout,
    initUserInfo,
    updateUserInfo,
  };
});
