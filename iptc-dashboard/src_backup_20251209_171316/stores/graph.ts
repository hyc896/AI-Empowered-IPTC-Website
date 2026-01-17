import { defineStore } from 'pinia'
import { ref } from 'vue'
import { graphAPI } from '@/api/graph'
import type { GraphData, GraphNode } from '@/types/graph'

export const useGraphStore = defineStore('graph', () => {
  const graphData = ref<GraphData>({ nodes: [], edges: [] })
  const loading = ref(false)
  const selectedNode = ref<GraphNode | null>(null)

  const fetchFullGraph = async () => {
    loading.value = true
    try {
      graphData.value = await graphAPI.getFullGraph()
    } catch (error) {
      console.error('Failed to fetch full graph:', error)
    } finally {
      loading.value = false
    }
  }

  const fetchCaseRelations = async (caseId: string) => {
    loading.value = true
    try {
      graphData.value = await graphAPI.getCaseRelations(caseId)
    } catch (error) {
      console.error('Failed to fetch case relations:', error)
    } finally {
      loading.value = false
    }
  }

  const selectNode = (node: GraphNode | null) => {
    selectedNode.value = node
  }

  return {
    graphData,
    loading,
    selectedNode,
    fetchFullGraph,
    fetchCaseRelations,
    selectNode
  }
})
