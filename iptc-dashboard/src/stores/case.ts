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
    pageSize: 18,
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
      const response = await getCaseById(id);
      currentCase.value = response.data;
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
      const response = await getRelatedCases(caseId, 3);
      relatedCases.value = response.data;
    } catch (err: any) {
      console.error('获取相关案例失败:', err);
      relatedCases.value = [];
    }
  }

  // 重置筛选条件
  function resetFilters() {
    searchParams.value = {
      page: 1,
      pageSize: 18,
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
