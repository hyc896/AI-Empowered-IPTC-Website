/**
 * 应用全局 Store
 */

import { defineStore } from 'pinia';
import { ref } from 'vue';
import type { Statistics } from '@/types';
import { getStatistics } from '@/api';

export const useAppStore = defineStore('app', () => {
  // 状态
  const statistics = ref<Statistics>({
    total_cases: 0,
    total_knowledge_points: 0,
    generated_knowledge_points: 0,
    total_relations: 0,
    latest_cases: [],
  });

  const loading = ref(false);
  const sidebarCollapsed = ref(false);
  const mobileMenuOpen = ref(false);

  // 获取统计数据
  async function fetchStatistics() {
    loading.value = true;

    try {
      const response = await getStatistics();
      statistics.value = response as Statistics;
    } catch (err: any) {
      console.error('获取统计数据失败:', err);
    } finally {
      loading.value = false;
    }
  }

  // 切换侧边栏
  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value;
  }

  // 切换移动端菜单
  function toggleMobileMenu() {
    mobileMenuOpen.value = !mobileMenuOpen.value;
  }

  // 关闭移动端菜单
  function closeMobileMenu() {
    mobileMenuOpen.value = false;
  }

  return {
    statistics,
    loading,
    sidebarCollapsed,
    mobileMenuOpen,
    fetchStatistics,
    toggleSidebar,
    toggleMobileMenu,
    closeMobileMenu,
  };
});
