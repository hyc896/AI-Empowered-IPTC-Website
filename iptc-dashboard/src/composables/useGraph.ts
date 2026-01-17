/**
 * 知识图谱相关的组合式函数
 */

import { ref, onMounted, onBeforeUnmount, type Ref } from 'vue';
import { Graph, type GraphOptions } from '@antv/g6';
import type { GraphData, GraphNode, GraphLayoutConfig } from '@/types';

interface UseGraphOptions {
  container: Ref<HTMLElement | null>;
  data: Ref<GraphData>;
  layoutConfig: Ref<GraphLayoutConfig>;
  onNodeClick?: (node: GraphNode) => void;
}

export function useGraph(options: UseGraphOptions) {
  const { container, data, layoutConfig, onNodeClick } = options;

  const graph = ref<Graph | null>(null);
  const loading = ref(false);

  // 初始化图谱
  const initGraph = () => {
    if (!container.value) return;

    const width = container.value.offsetWidth;
    const height = container.value.offsetHeight;

    const graphOptions: GraphOptions = {
      container: container.value,
      width,
      height,
      modes: {
        default: ['drag-canvas', 'zoom-canvas', 'drag-node'],
      },
      layout: {
        type: layoutConfig.value.type,
        preventOverlap: layoutConfig.value.preventOverlap,
        nodeSpacing: layoutConfig.value.nodeSpacing,
        linkDistance: layoutConfig.value.linkDistance,
      },
      defaultNode: {
        size: 40,
        style: {
          lineWidth: 2,
          fill: '#5b8ff9',
          stroke: '#5b8ff9',
        },
        labelCfg: {
          style: {
            fill: '#333',
            fontSize: 12,
          },
        },
      },
      defaultEdge: {
        style: {
          stroke: '#e2e2e2',
          lineWidth: 1,
          endArrow: {
            path: 'M 0,0 L 8,4 L 8,-4 Z',
            fill: '#e2e2e2',
          },
        },
      },
      nodeStateStyles: {
        hover: {
          fill: '#d03050',
          stroke: '#d03050',
          lineWidth: 3,
        },
        selected: {
          fill: '#36cfc9',
          stroke: '#36cfc9',
          lineWidth: 3,
        },
      },
      edgeStateStyles: {
        hover: {
          stroke: '#d03050',
          lineWidth: 2,
        },
      },
    };

    graph.value = new Graph(graphOptions);

    // 绑定事件
    graph.value.on('node:click', (evt) => {
      const { item } = evt;
      if (item) {
        const model = item.getModel() as GraphNode;
        onNodeClick?.(model);
      }
    });

    graph.value.on('node:mouseenter', (evt) => {
      const { item } = evt;
      if (item) {
        graph.value?.setItemState(item, 'hover', true);
      }
    });

    graph.value.on('node:mouseleave', (evt) => {
      const { item } = evt;
      if (item) {
        graph.value?.setItemState(item, 'hover', false);
      }
    });

    // 渲染数据
    if (data.value) {
      graph.value.data(data.value);
      graph.value.render();
    }
  };

  // 更新图谱数据
  const updateData = (newData: GraphData) => {
    if (!graph.value) return;

    loading.value = true;
    graph.value.changeData(newData);
    loading.value = false;
  };

  // 更新布局
  const updateLayout = (config: GraphLayoutConfig) => {
    if (!graph.value) return;

    graph.value.updateLayout({
      type: config.type,
      preventOverlap: config.preventOverlap,
      nodeSpacing: config.nodeSpacing,
      linkDistance: config.linkDistance,
    });
  };

  // 适应画布
  const fitView = () => {
    if (!graph.value) return;
    graph.value.fitView(20);
  };

  // 重置缩放
  const resetZoom = () => {
    if (!graph.value) return;
    graph.value.zoomTo(1);
    graph.value.fitCenter();
  };

  // 导出图片
  const exportImage = (name = 'graph') => {
    if (!graph.value) return;
    graph.value.downloadFullImage(name, 'image/png', {
      backgroundColor: '#fff',
      padding: 20,
    });
  };

  // 高亮节点
  const highlightNodes = (nodeIds: string[]) => {
    if (!graph.value) return;

    const nodes = graph.value.getNodes();
    const edges = graph.value.getEdges();

    // 重置所有节点和边的状态
    nodes.forEach((node) => {
      graph.value?.clearItemStates(node);
    });
    edges.forEach((edge) => {
      graph.value?.clearItemStates(edge);
    });

    // 高亮指定节点
    nodeIds.forEach((id) => {
      const node = graph.value?.findById(id);
      if (node) {
        graph.value?.setItemState(node, 'selected', true);
      }
    });
  };

  // 清除高亮
  const clearHighlight = () => {
    if (!graph.value) return;

    const nodes = graph.value.getNodes();
    nodes.forEach((node) => {
      graph.value?.clearItemStates(node);
    });
  };

  // 销毁图谱
  const destroyGraph = () => {
    if (graph.value) {
      graph.value.destroy();
      graph.value = null;
    }
  };

  // 生命周期
  onMounted(() => {
    initGraph();

    // 监听窗口大小变化
    const handleResize = () => {
      if (graph.value && container.value) {
        const width = container.value.offsetWidth;
        const height = container.value.offsetHeight;
        graph.value.changeSize(width, height);
        graph.value.fitView(20);
      }
    };

    window.addEventListener('resize', handleResize);

    onBeforeUnmount(() => {
      window.removeEventListener('resize', handleResize);
      destroyGraph();
    });
  });

  return {
    graph,
    loading,
    initGraph,
    updateData,
    updateLayout,
    fitView,
    resetZoom,
    exportImage,
    highlightNodes,
    clearHighlight,
    destroyGraph,
  };
}
