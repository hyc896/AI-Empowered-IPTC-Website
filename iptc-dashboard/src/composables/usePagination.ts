/**
 * 分页相关的组合式函数
 */

import { ref, computed } from 'vue';

interface UsePaginationOptions {
  initialPage?: number;
  initialPageSize?: number;
  total?: number;
  onPageChange?: (page: number) => void;
  onPageSizeChange?: (pageSize: number) => void;
}

export function usePagination(options: UsePaginationOptions = {}) {
  const {
    initialPage = 1,
    initialPageSize = 20,
    total: initialTotal = 0,
    onPageChange,
    onPageSizeChange,
  } = options;

  const currentPage = ref(initialPage);
  const pageSize = ref(initialPageSize);
  const total = ref(initialTotal);

  // 计算总页数
  const totalPages = computed(() => Math.ceil(total.value / pageSize.value));

  // 是否有上一页
  const hasPrev = computed(() => currentPage.value > 1);

  // 是否有下一页
  const hasNext = computed(() => currentPage.value < totalPages.value);

  // 切换页码
  const changePage = (page: number) => {
    if (page < 1 || page > totalPages.value) return;
    currentPage.value = page;
    onPageChange?.(page);
  };

  // 上一页
  const prevPage = () => {
    if (hasPrev.value) {
      changePage(currentPage.value - 1);
    }
  };

  // 下一页
  const nextPage = () => {
    if (hasNext.value) {
      changePage(currentPage.value + 1);
    }
  };

  // 切换每页数量
  const changePageSize = (size: number) => {
    pageSize.value = size;
    currentPage.value = 1; // 重置到第一页
    onPageSizeChange?.(size);
  };

  // 重置分页
  const reset = () => {
    currentPage.value = initialPage;
    pageSize.value = initialPageSize;
    total.value = initialTotal;
  };

  return {
    currentPage,
    pageSize,
    total,
    totalPages,
    hasPrev,
    hasNext,
    changePage,
    prevPage,
    nextPage,
    changePageSize,
    reset,
  };
}
