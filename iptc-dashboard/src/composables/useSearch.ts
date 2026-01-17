/**
 * 搜索相关的组合式函数
 */

import { ref, watch } from 'vue';
import { debounce } from '@/utils';

interface UseSearchOptions {
  onSearch: (keyword: string) => void;
  debounceTime?: number;
  minLength?: number;
}

export function useSearch(options: UseSearchOptions) {
  const { onSearch, debounceTime = 300, minLength = 0 } = options;

  const keyword = ref('');
  const searching = ref(false);

  // 防抖搜索函数
  const debouncedSearch = debounce((value: string) => {
    if (value.length >= minLength) {
      searching.value = true;
      onSearch(value);
      searching.value = false;
    } else if (value.length === 0) {
      onSearch('');
    }
  }, debounceTime);

  // 监听关键词变化
  watch(keyword, (newValue) => {
    debouncedSearch(newValue);
  });

  // 清空搜索
  const clearSearch = () => {
    keyword.value = '';
  };

  // 立即搜索
  const searchNow = () => {
    if (keyword.value.length >= minLength) {
      onSearch(keyword.value);
    }
  };

  return {
    keyword,
    searching,
    clearSearch,
    searchNow,
  };
}
