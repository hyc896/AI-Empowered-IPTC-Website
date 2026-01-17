/**
 * 知识图谱 Store
 */

import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import type { GraphData, GraphNode, GraphEdge, KnowledgePoint, GraphLayoutConfig } from '@/types';
import { getGraphData, getKnowledgePoints, getCaseGraph, getKnowledgePointGraph } from '@/api';

export const useGraphStore = defineStore('graph', () => {
  // 状态
  const graphData = ref<GraphData>({ nodes: [], edges: [] });
  const knowledgePoints = ref<KnowledgePoint[]>([]);
  const selectedNode = ref<GraphNode | null>(null);
  const highlightedNodes = ref<Set<string>>(new Set());
  const loading = ref(false);
  const error = ref<string | null>(null);

  // 布局配置
  const layoutConfig = ref<GraphLayoutConfig>({
    type: 'force',
    preventOverlap: true,
    nodeSpacing: 50,
    linkDistance: 150,
  });

  // 筛选条件
  const filterNodeType = ref<'all' | 'case' | 'knowledge'>('all');

  // 计算属性
  const filteredGraphData = computed(() => {
    if (filterNodeType.value === 'all') {
      return graphData.value;
    }

    const filteredNodes = graphData.value.nodes.filter(
      (node) => node.type === filterNodeType.value
    );
    const nodeIds = new Set(filteredNodes.map((n) => n.id));
    const filteredEdges = graphData.value.edges.filter(
      (edge) => nodeIds.has(edge.source) && nodeIds.has(edge.target)
    );

    return {
      nodes: filteredNodes,
      edges: filteredEdges,
    };
  });

  const nodeCount = computed(() => graphData.value.nodes.length);
  const edgeCount = computed(() => graphData.value.edges.length);
  const caseNodeCount = computed(
    () => graphData.value.nodes.filter((n) => n.type === 'case').length
  );
  const knowledgeNodeCount = computed(
    () => graphData.value.nodes.filter((n) => n.type === 'knowledge').length
  );

  // 获取完整图谱数据
  async function fetchGraphData() {
    loading.value = true;
    error.value = null;

    try {
      const response = await getGraphData();
      graphData.value = response.data as GraphData;
    } catch (err: any) {
      error.value = err.message || '获取图谱数据失败';
      console.error('获取图谱数据失败:', err);
    } finally {
      loading.value = false;
    }
  }

  // 获取知识点列表
  async function fetchKnowledgePoints() {
    try {
      const response = await getKnowledgePoints();
      knowledgePoints.value = response.data as KnowledgePoint[];
    } catch (err: any) {
      console.error('获取知识点列表失败:', err);
    }
  }

  // 获取案例的局部图谱
  async function fetchCaseGraph(caseId: string) {
    loading.value = true;
    error.value = null;

    try {
      const response = await getCaseGraph(caseId);
      graphData.value = response.data as GraphData;
    } catch (err: any) {
      error.value = err.message || '获取案例图谱失败';
      console.error('获取案例图谱失败:', err);
    } finally {
      loading.value = false;
    }
  }

  // 获取知识点的局部图谱
  async function fetchKnowledgePointGraph(knowledgePointId: string) {
    loading.value = true;
    error.value = null;

    try {
      const response = await getKnowledgePointGraph(knowledgePointId);
      graphData.value = response.data as GraphData;
    } catch (err: any) {
      error.value = err.message || '获取知识点图谱失败';
      console.error('获取知识点图谱失败:', err);
    } finally {
      loading.value = false;
    }
  }

  // 选择节点
  function selectNode(node: GraphNode | null) {
    selectedNode.value = node;

    if (node) {
      // 高亮选中节点及其相邻节点
      const neighbors = new Set<string>([node.id]);
      graphData.value.edges.forEach((edge) => {
        if (edge.source === node.id) {
          neighbors.add(edge.target);
        } else if (edge.target === node.id) {
          neighbors.add(edge.source);
        }
      });
      highlightedNodes.value = neighbors;
    } else {
      highlightedNodes.value = new Set();
    }
  }

  // 更新布局配置
  function updateLayoutConfig(config: Partial<GraphLayoutConfig>) {
    layoutConfig.value = { ...layoutConfig.value, ...config };
  }

  // 更新节点筛选
  function updateNodeFilter(type: 'all' | 'case' | 'knowledge') {
    filterNodeType.value = type;
  }

  // 重置图谱
  function resetGraph() {
    selectedNode.value = null;
    highlightedNodes.value = new Set();
    filterNodeType.value = 'all';
  }

  return {
    // 状态
    graphData,
    knowledgePoints,
    selectedNode,
    highlightedNodes,
    loading,
    error,
    layoutConfig,
    filterNodeType,

    // 计算属性
    filteredGraphData,
    nodeCount,
    edgeCount,
    caseNodeCount,
    knowledgeNodeCount,

    // 方法
    fetchGraphData,
    fetchKnowledgePoints,
    fetchCaseGraph,
    fetchKnowledgePointGraph,
    selectNode,
    updateLayoutConfig,
    updateNodeFilter,
    resetGraph,
  };
});
