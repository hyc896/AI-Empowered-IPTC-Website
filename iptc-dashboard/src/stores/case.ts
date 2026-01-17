/**
 * 案例 Store
 */

import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import type { Case, SearchParams, PaginatedResponse, FilterOptions } from '@/types';
import { getCases, searchCases, getCaseById, getRelatedCases } from '@/api';

export const useCaseStore = defineStore('case', () => {
  // 状态
  const cases = ref<Case[]>([]);
  const currentCase = ref<Case | null>(null);
  const relatedCases = ref<Case[]>([]);
  const total = ref(0);
  const loading = ref(false);
  const error = ref<string | null>(null);

  // 搜索和筛选参数
  const searchParams = ref<SearchParams>({
    page: 1,
    pageSize: 20,
    keyword: '',
    sortBy: 'date',
    sortOrder: 'desc',
  });

  const filterOptions = ref<FilterOptions>({
    knowledgePoints: [],
    dateRange: undefined,
    sources: [],
  });

  // 计算属性
  const totalPages = computed(() => Math.ceil(total.value / searchParams.value.pageSize));
  const hasMore = computed(() => searchParams.value.page < totalPages.value);
  const isEmpty = computed(() => !loading.value && cases.value.length === 0);

  // 获取案例列表
  async function fetchCases() {
    loading.value = true;
    error.value = null;

    try {
      const params: SearchParams = {
        ...searchParams.value,
        knowledgePoints: filterOptions.value.knowledgePoints,
        startDate: filterOptions.value.dateRange?.[0],
        endDate: filterOptions.value.dateRange?.[1],
      };

      const response = await getCases(params);
      const data = response.data as PaginatedResponse<Case>;

      cases.value = data.items;
      total.value = data.total;
    } catch (err: any) {
      error.value = err.message || '获取案例列表失败';
      console.error('获取案例列表失败:', err);
    } finally {
      loading.value = false;
    }
  }

  // 搜索案例
  async function search(keyword: string) {
    searchParams.value.keyword = keyword;
    searchParams.value.page = 1;
    await fetchCases();
  }

  // 更新筛选条件
  function updateFilters(filters: Partial<FilterOptions>) {
    filterOptions.value = { ...filterOptions.value, ...filters };
    searchParams.value.page = 1;
    fetchCases();
  }

  // 更新排序
  function updateSort(sortBy: 'relevance' | 'date', sortOrder: 'asc' | 'desc' = 'desc') {
    searchParams.value.sortBy = sortBy;
    searchParams.value.sortOrder = sortOrder;
    searchParams.value.page = 1;
    fetchCases();
  }

  // 更改页码
  function changePage(page: number) {
    searchParams.value.page = page;
    fetchCases();
  }

  // 更改每页数量
  function changePageSize(pageSize: number) {
    searchParams.value.pageSize = pageSize;
    searchParams.value.page = 1;
    fetchCases();
  }

  // 获取案例详情
  async function fetchCaseDetail(id: string) {
    loading.value = true;
    error.value = null;

    try {
      // 从JSON文件读取所有案例，然后找到对应ID的案例
      const response = await fetch('/cases.json');
      const data = await response.json();
      const caseItem = data.data.items.find((item: Case) => item.id === id);

      if (caseItem) {
        currentCase.value = caseItem;
      } else {
        error.value = '案例不存在';
      }
    } catch (err: any) {
      error.value = err.message || '获取案例详情失败';
      console.error('获取案例详情失败:', err);
    } finally {
      loading.value = false;
    }
  }

  // 获取相关案例
  async function fetchRelatedCases(caseId: string) {
    try {
      // 从JSON文件读取所有案例，然后找到相关的案例（相同知识点）
      const response = await fetch('/cases.json');
      const data = await response.json();
      const currentCaseItem = data.data.items.find((item: Case) => item.id === caseId);

      if (currentCaseItem && currentCaseItem.knowledgePoints.length > 0) {
        // 找到具有相同知识点的案例（排除当前案例）
        const related = data.data.items.filter((item: Case) =>
          item.id !== caseId &&
          item.knowledgePoints.some((kp: string) =>
            currentCaseItem.knowledgePoints.includes(kp)
          )
        ).slice(0, 3); // 最多返回3个相关案例

        relatedCases.value = related;
      } else {
        relatedCases.value = [];
      }
    } catch (err: any) {
      console.error('获取相关案例失败:', err);
    }
  }

  // 重置筛选条件
  function resetFilters() {
    searchParams.value = {
      page: 1,
      pageSize: 20,
      keyword: '',
      sortBy: 'date',
      sortOrder: 'desc',
    };
    filterOptions.value = {
      knowledgePoints: [],
      dateRange: undefined,
      sources: [],
    };
    fetchCases();
  }

  return {
    // 状态
    cases,
    currentCase,
    relatedCases,
    total,
    loading,
    error,
    searchParams,
    filterOptions,

    // 计算属性
    totalPages,
    hasMore,
    isEmpty,

    // 方法
    fetchCases,
    search,
    updateFilters,
    updateSort,
    changePage,
    changePageSize,
    fetchCaseDetail,
    fetchRelatedCases,
    resetFilters,
  };
});
