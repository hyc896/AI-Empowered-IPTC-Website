/**
 * D3.js 知识图谱组合式函数
 * 实现动态交互式力导向图谱
 */

import { ref, onMounted, onBeforeUnmount, watch, type Ref } from 'vue';
import * as d3 from 'd3';
import type { GraphData, GraphNode, GraphEdge } from '@/types';

interface UseD3GraphOptions {
  container: Ref<HTMLElement | null>;
  data: Ref<GraphData>;
  onNodeClick?: (node: GraphNode) => void;
}

// D3 节点类型（扩展位置信息）
interface D3Node extends GraphNode {
  x?: number;
  y?: number;
  fx?: number | null;
  fy?: number | null;
  vx?: number;
  vy?: number;
}

// D3 边类型
interface D3Edge extends GraphEdge {
  source: string | D3Node;
  target: string | D3Node;
}

export function useD3Graph(options: UseD3GraphOptions) {
  const { container, data, onNodeClick } = options;

  // 状态管理
  const svg = ref<d3.Selection<SVGSVGElement, unknown, null, undefined> | null>(null);
  const simulation = ref<d3.Simulation<D3Node, D3Edge> | null>(null);
  const zoomBehavior = ref<d3.ZoomBehavior<SVGSVGElement, unknown> | null>(null);
  const loading = ref(false);

  // 图谱元素分组
  let gZoom: d3.Selection<SVGGElement, unknown, null, undefined>;
  let gLinks: d3.Selection<SVGGElement, unknown, null, undefined>;
  let gNodes: d3.Selection<SVGGElement, unknown, null, undefined>;
  let gLabels: d3.Selection<SVGGElement, unknown, null, undefined>;

  // 当前数据
  const currentNodes = ref<D3Node[]>([]);
  const currentEdges = ref<D3Edge[]>([]);

  // 画布尺寸
  let width = 0;
  let height = 0;

  // 性能优化配置
  const LARGE_GRAPH_THRESHOLD = 500;
  const SIMULATION_ITERATIONS = 300;

  /**
   * 获取节点颜色（根据层级）
   */
  const getNodeColor = (node: D3Node): string => {
    switch (node.type) {
      case 'book':
        return '#8B4513'; // 棕色 - 书
      case 'chapter':
        return '#4A90E2'; // 蓝色 - 章
      case 'section':
        return '#50C878'; // 绿色 - 节
      case 'knowledge_point':
        return '#E94B3C'; // 红色 - 知识点
      default:
        return '#999999';
    }
  };

  /**
   * 获取节点大小（根据层级）
   */
  const getNodeSize = (node: D3Node): number => {
    // 使用节点的size属性，如果没有则根据type设置默认值
    if (node.size) return node.size;

    switch (node.type) {
      case 'book':
        return 60;
      case 'chapter':
        return 45;
      case 'section':
        return 35;
      case 'knowledge_point':
        return 25;
      default:
        return 20;
    }
  };

  /**
   * 初始化 SVG 画布
   */
  const initSVG = () => {
    if (!container.value) return;

    width = container.value.offsetWidth;
    height = container.value.offsetHeight;

    // 清空容器
    d3.select(container.value).selectAll('*').remove();

    // 创建 SVG
    svg.value = d3.select(container.value)
      .append('svg')
      .attr('width', '100%')
      .attr('height', '100%')
      .attr('viewBox', `0 0 ${width} ${height}`);

    // 添加箭头标记
    svg.value.append('defs')
      .append('marker')
      .attr('id', 'arrow')
      .attr('viewBox', '0 0 10 10')
      .attr('refX', 25)
      .attr('refY', 5)
      .attr('markerWidth', 6)
      .attr('markerHeight', 6)
      .attr('orient', 'auto')
      .append('path')
      .attr('d', 'M 0 0 L 10 5 L 0 10 z')
      .attr('fill', '#999');

    // 创建缩放层
    gZoom = svg.value.append('g').attr('class', 'zoom-layer');

    // 创建图层（顺序决定渲染层级）
    gLinks = gZoom.append('g').attr('class', 'links');
    gNodes = gZoom.append('g').attr('class', 'nodes');
    gLabels = gZoom.append('g').attr('class', 'labels');

    // 初始化缩放行为
    initZoom();
  };

  /**
   * 初始化缩放和拖拽
   */
  const initZoom = () => {
    if (!svg.value) return;

    zoomBehavior.value = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.1, 10])
      .on('zoom', (event) => {
        gZoom.attr('transform', event.transform);
      });

    svg.value.call(zoomBehavior.value);
  };

  /**
   * 初始化力导向模拟（层级布局）
   */
  const initSimulation = () => {
    const isLargeGraph = currentNodes.value.length > LARGE_GRAPH_THRESHOLD;

    simulation.value = d3.forceSimulation<D3Node, D3Edge>(currentNodes.value)
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('charge', d3.forceManyBody().strength(isLargeGraph ? -400 : -600))
      .force('link', d3.forceLink<D3Node, D3Edge>(currentEdges.value)
        .id((d: any) => d.id)
        .distance(d => {
          // 根据层级设置边的长度
          const source = d.source as D3Node;
          const target = d.target as D3Node;
          const sourceLevel = source.level || 1;
          const targetLevel = target.level || 1;
          return 150 + (targetLevel - sourceLevel) * 50;
        }))
      .force('collision', d3.forceCollide().radius((d: any) => getNodeSize(d) + 20))
      // 添加Y轴力，使层级结构更明显
      .force('y', d3.forceY<D3Node>().y(d => {
        const level = d.level || 1;
        return height / 5 * level;
      }).strength(0.3))
      .alphaDecay(isLargeGraph ? 0.05 : 0.02)
      .on('tick', onTick);

    // 大规模图谱优化：限制迭代次数
    if (isLargeGraph) {
      simulation.value.stop();
      for (let i = 0; i < SIMULATION_ITERATIONS; ++i) {
        simulation.value.tick();
      }
      simulation.value.restart();
    }
  };

  /**
   * 每帧更新位置
   */
  const onTick = () => {
    // 更新边的位置
    gLinks.selectAll('line')
      .attr('x1', (d: any) => d.source.x)
      .attr('y1', (d: any) => d.source.y)
      .attr('x2', (d: any) => d.target.x)
      .attr('y2', (d: any) => d.target.y);

    // 更新节点的位置
    gNodes.selectAll('circle')
      .attr('cx', (d: any) => d.x)
      .attr('cy', (d: any) => d.y);

    // 更新标签的位置
    gLabels.selectAll('text')
      .attr('x', (d: any) => d.x)
      .attr('y', (d: any) => d.y + getNodeSize(d) + 15);
  };

  /**
   * 节点拖拽行为
   */
  const dragBehavior = () => {
    return d3.drag<SVGCircleElement, D3Node>()
      .on('start', (event, d) => {
        if (!event.active && simulation.value) {
          simulation.value.alphaTarget(0.3).restart();
        }
        d.fx = d.x;
        d.fy = d.y;
      })
      .on('drag', (event, d) => {
        d.fx = event.x;
        d.fy = event.y;
      })
      .on('end', (event, d) => {
        if (!event.active && simulation.value) {
          simulation.value.alphaTarget(0);
        }
        d.fx = null;
        d.fy = null;
      });
  };

  /**
   * 渲染边
   */
  const renderLinks = () => {
    const linkElements = gLinks
      .selectAll<SVGLineElement, D3Edge>('line')
      .data(currentEdges.value, (d: any) => d.id);

    // Enter
    linkElements.enter()
      .append('line')
      .attr('stroke', '#999')
      .attr('stroke-width', 1)
      .attr('stroke-opacity', 0.6)
      .attr('marker-end', 'url(#arrow)');

    // Exit
    linkElements.exit().remove();
  };

  /**
   * 渲染节点
   */
  const renderNodes = () => {
    const nodeElements = gNodes
      .selectAll<SVGCircleElement, D3Node>('circle')
      .data(currentNodes.value, (d: any) => d.id);

    // Enter
    const enterNodes = nodeElements.enter()
      .append('circle')
      .attr('r', d => getNodeSize(d))
      .attr('fill', d => getNodeColor(d))
      .attr('stroke', '#fff')
      .attr('stroke-width', 2)
      .style('cursor', 'pointer')
      .on('click', (event, d) => {
        event.stopPropagation();
        if (onNodeClick) {
          onNodeClick(d as GraphNode);
        }
      });

    // Update
    nodeElements
      .attr('r', d => getNodeSize(d))
      .attr('fill', d => getNodeColor(d));

    // Exit
    nodeElements.exit().remove();
  };

  /**
   * 渲染标签
   */
  const renderLabels = () => {
    const labelElements = gLabels
      .selectAll<SVGTextElement, D3Node>('text')
      .data(currentNodes.value, (d: any) => d.id);

    // Enter
    labelElements.enter()
      .append('text')
      .attr('text-anchor', 'middle')
      .attr('font-size', '16px')
      .attr('fill', '#333')
      .attr('font-weight', '600')
      .attr('pointer-events', 'none')
      .style('text-shadow', '0 0 3px white, 0 0 3px white, 0 0 3px white')
      .text(d => d.label);

    // Update
    labelElements.text(d => d.label);

    // Exit
    labelElements.exit().remove();
  };

  /**
   * 设置图谱数据（完全替换）
   */
  const setData = (newData: GraphData) => {
    if (!newData || !newData.nodes || !newData.edges) return;

    // 完全替换数据
    currentNodes.value = [...newData.nodes];
    currentEdges.value = [...newData.edges];

    // 重新渲染
    renderLinks();
    renderNodes();
    renderLabels();

    // 重新初始化力模拟
    if (simulation.value) {
      simulation.value.nodes(currentNodes.value);
      const linkForce = simulation.value.force('link') as d3.ForceLink<D3Node, D3Edge>;
      if (linkForce) {
        linkForce.links(currentEdges.value);
      }
      simulation.value.alpha(1).restart();
    }
  };

  /**
   * 更新图谱数据（增量添加）
   */
  const updateData = (newData: GraphData) => {
    if (!newData || !newData.nodes || !newData.edges) return;

    // 合并新数据
    const existingNodeIds = new Set(currentNodes.value.map(n => n.id));
    const existingEdgeIds = new Set(currentEdges.value.map(e => e.id));

    // 过滤重复节点和边
    const newNodes = newData.nodes.filter(n => !existingNodeIds.has(n.id));
    const newEdges = newData.edges.filter(e => !existingEdgeIds.has(e.id));

    // 更新当前数据
    currentNodes.value = [...currentNodes.value, ...newNodes];
    currentEdges.value = [...currentEdges.value, ...newEdges];

    // 重新渲染
    renderLinks();
    renderNodes();
    renderLabels();

    // 更新力模拟
    if (simulation.value) {
      simulation.value.nodes(currentNodes.value);
      const linkForce = simulation.value.force('link') as d3.ForceLink<D3Node, D3Edge>;
      if (linkForce) {
        linkForce.links(currentEdges.value);
      }
      simulation.value.alpha(0.3).restart();
    }
  };

  /**
   * 适应画布
   */
  const fitView = () => {
    if (!svg.value || !zoomBehavior.value) return;

    const bounds = gZoom.node()?.getBBox();
    if (!bounds) return;

    const fullWidth = width;
    const fullHeight = height;
    const midX = bounds.x + bounds.width / 2;
    const midY = bounds.y + bounds.height / 2;

    const scale = 0.9 / Math.max(bounds.width / fullWidth, bounds.height / fullHeight);
    const translate = [fullWidth / 2 - scale * midX, fullHeight / 2 - scale * midY];

    svg.value
      .transition()
      .duration(750)
      .call(
        zoomBehavior.value.transform as any,
        d3.zoomIdentity.translate(translate[0], translate[1]).scale(scale)
      );
  };

  /**
   * 重置缩放
   */
  const resetZoom = () => {
    if (!svg.value || !zoomBehavior.value) return;

    svg.value
      .transition()
      .duration(750)
      .call(zoomBehavior.value.transform as any, d3.zoomIdentity);
  };

  /**
   * 导出图片
   */
  const exportImage = () => {
    if (!svg.value) return;

    const svgNode = svg.value.node();
    if (!svgNode) return;

    const serializer = new XMLSerializer();
    const svgString = serializer.serializeToString(svgNode);
    const blob = new Blob([svgString], { type: 'image/svg+xml' });
    const url = URL.createObjectURL(blob);

    const link = document.createElement('a');
    link.href = url;
    link.download = `graph-${Date.now()}.svg`;
    link.click();

    URL.revokeObjectURL(url);
  };

  /**
   * 初始化图谱
   */
  const initGraph = () => {
    initSVG();
    initSimulation();

    if (data.value && data.value.nodes.length > 0) {
      updateData(data.value);
    }
  };

  // 生命周期钩子
  onMounted(() => {
    if (container.value) {
      initGraph();
    }
  });

  onBeforeUnmount(() => {
    if (simulation.value) {
      simulation.value.stop();
    }
  });

  return {
    fitView,
    resetZoom,
    exportImage,
    setData,
    updateData,
  };
}
