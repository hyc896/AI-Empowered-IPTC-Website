import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { caseAPI } from '@/api/case'
import type { CaseItem, CaseListParams } from '@/types/case'

export const useCaseStore = defineStore('case', () => {
  const cases = ref<CaseItem[]>([])
  const total = ref(0)
  const loading = ref(false)
  const currentCase = ref<CaseItem | null>(null)

  const fetchCases = async (params: CaseListParams) => {
    loading.value = true
    try {
      const res = await caseAPI.getCases(params)
      cases.value = res.items
      total.value = res.total
    } catch (error) {
      console.error('Failed to fetch cases:', error)
    } finally {
      loading.value = false
    }
  }

  const fetchCaseDetail = async (id: string) => {
    loading.value = true
    try {
      currentCase.value = await caseAPI.getCaseDetail(id)
    } catch (error) {
      console.error('Failed to fetch case detail:', error)
    } finally {
      loading.value = false
    }
  }

  const searchCases = async (query: string, top_k = 10) => {
    loading.value = true
    try {
      cases.value = await caseAPI.searchCases(query, top_k)
      total.value = cases.value.length
    } catch (error) {
      console.error('Failed to search cases:', error)
    } finally {
      loading.value = false
    }
  }

  return {
    cases,
    total,
    loading,
    currentCase,
    fetchCases,
    fetchCaseDetail,
    searchCases
  }
})
