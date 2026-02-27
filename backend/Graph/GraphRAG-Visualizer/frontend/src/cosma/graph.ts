
/**
 * Cosma 图谱核心渲染逻辑
 * 基于 D3.js 力导向图和 Graphology 图数据结构
 */

import * as d3 from 'd3';
import GraphEngine from 'graphology';
import type { CosmaGraphData } from '@/types/cosma';

export interface GraphInstance {
  loadData: (data: CosmaGraphData) => void;
  destroy: () => void;
  zoomToNode: (nodeId: string) => void;
  highlightNodes: (nodeIds: string[]) => void;
  unlightNodes: () => void;
}



export function initGraph(container: HTMLElement, onNodeClick?: (nodeId: string) => void): GraphInstance {
  const graph = new GraphEngine({ multi: true });

  const width = container.clientWidth;
  const height = container.clientHeight;

  const svg = d3.select(container)
    .append('svg')
    .attr('width', width)
    .attr('height', height);

  const g = svg.append('g');

  const zoom = d3.zoom<SVGSVGElement, unknown>()
    .scaleExtent([0.1, 10])
    .on('zoom', (event) => {
      g.attr('transform', event.transform);
    });

  svg.call(zoom);

  const simulation = d3.forceSimulation()
    .force('link', d3.forceLink().id((d: any) => d.key).distance(150))
    .force('charge', d3.forceManyBody().strength(-500))
    .force('center', d3.forceCenter(width / 2, height / 2).strength(0.2))
    .force('collision', d3.forceCollide().radius((d: any) => d.attributes.size + 10))
    .force('x', d3.forceX(width / 2).strength(0.15))
    .force('y', d3.forceY(height / 2).strength(0.15));

  let linkElements: d3.Selection<SVGLineElement, any, SVGGElement, unknown>;
  let nodeElements: d3.Selection<SVGCircleElement, any, SVGGElement, unknown>;
  let labelElements: d3.Selection<SVGTextElement, any, SVGGElement, unknown>;

  function loadData(data: CosmaGraphData) {
    graph.clear();

    data.nodes.forEach(node => {
      if (!graph.hasNode(node.key)) {
        graph.addNode(node.key, node.attributes);
      }
    });

    data.edges.forEach(edge => {
      if (graph.hasNode(edge.source) && graph.hasNode(edge.target)) {
        graph.addDirectedEdge(edge.source, edge.target, edge.attributes);
      }
    });

    render();
  }

  function render() {
    g.selectAll('*').remove();

    const links = graph.mapEdges((edge, attrs, source, target) => ({
      source,
      target,
      ...attrs
    }));

    const nodes = graph.mapNodes((node, attrs) => ({
      key: node,
      attributes: attrs
    }));

    linkElements = g.append('g')
      .selectAll('line')
      .data(links)
      .enter()
      .append('line')
      .attr('stroke', '#a0a0a0')  // 使用 Cosma 的链接颜色
      .attr('stroke-opacity', 0.6)
      .attr('stroke-width', 1);

    nodeElements = g.append('g')
      .selectAll('circle')
      .data(nodes)
      .enter()
      .append('circle')
      .attr('r', (d: any) => d.attributes.size)
      .attr('fill', (d: any) => getNodeColor(d.attributes.types[0]))
      .attr('stroke', '#fff')
      .attr('stroke-width', 2)
      .style('cursor', 'pointer')
      .call(d3.drag<SVGCircleElement, any>()
        .on('start', dragStarted)
        .on('drag', dragged)
        .on('end', dragEnded) as any)
      .on('mouseover', function(event, d: any) {
        highlightNodes([d.key]);
        const neighbors = graph.neighbors(d.key);
        highlightNodes([d.key, ...neighbors]);
      })
      .on('mouseout', function() {
        unlightNodes();
      })
      .on('click', function(event, d: any) {
        if (onNodeClick) {
          onNodeClick(d.key);
        }
        zoomToNode(d.key);
      });

    labelElements = g.append('g')
      .selectAll('text')
      .data(nodes)
      .enter()
      .append('text')
      .text((d: any) => d.attributes.label)
      .attr('font-size', 10)
      .attr('dx', (d: any) => d.attributes.size + 5)
      .attr('dy', 4)
      .style('pointer-events', 'none');

    simulation.nodes(nodes as any);
    (simulation.force('link') as d3.ForceLink<any, any>).links(links);
    simulation.alpha(1).restart();

    simulation.on('tick', () => {
      linkElements
        .attr('x1', (d: any) => d.source.x)
        .attr('y1', (d: any) => d.source.y)
        .attr('x2', (d: any) => d.target.x)
        .attr('y2', (d: any) => d.target.y);

      nodeElements
        .attr('cx', (d: any) => d.x)
        .attr('cy', (d: any) => d.y);

      labelElements
        .attr('x', (d: any) => d.x)
        .attr('y', (d: any) => d.y);
    });
  }

  function dragStarted(event: any, d: any) {
    if (!event.active) simulation.alphaTarget(0.3).restart();
    d.fx = d.x;
    d.fy = d.y;
  }

  function dragged(event: any, d: any) {
    d.fx = event.x;
    d.fy = event.y;
  }

  function dragEnded(event: any, d: any) {
    if (!event.active) simulation.alphaTarget(0);
    d.fx = null;
    d.fy = null;
  }

  function getNodeColor(type: string): string {
    // 使用 Cosma 的配色方案
    const colors: Record<string, string> = {
      Person: '#1b9e77',      // 绿色 - 对应 Cosma 的 Personne
      Organization: '#7570b3', // 紫色 - 对应 Cosma 的 Institution
      Location: '#66a61e',     // 黄绿色 - 对应 Cosma 的 Évènement
      Event: '#d95f02',        // 橙色 - 对应 Cosma 的 Œuvre
      Concept: '#e7298a',      // 粉红色 - 对应 Cosma 的 Otlet
      unknown: '#eeeeee'       // 灰色 - 对应 Cosma 的 undefined
    };
    return colors[type] || colors.unknown;
  }

  function zoomToNode(nodeId: string) {
    const node = graph.getNodeAttributes(nodeId);
    if (node && node.x !== undefined && node.y !== undefined) {
      svg.transition()
        .duration(750)
        .call(
          zoom.transform as any,
          d3.zoomIdentity.translate(width / 2, height / 2).scale(1.5).translate(-node.x, -node.y)
        );
    }
  }

  function highlightNodes(nodeIds: string[]) {
    nodeElements.style('opacity', (d: any) =>
      nodeIds.includes(d.key) ? 1 : 0.2
    );
    linkElements.style('opacity', (d: any) =>
      nodeIds.includes(d.source.key) && nodeIds.includes(d.target.key) ? 1 : 0.1
    );
  }

  function unlightNodes() {
    nodeElements.style('opacity', 1);
    linkElements.style('opacity', 0.6);
  }

  function destroy() {
    simulation.stop();
    svg.remove();
  }

  return {
    loadData,
    destroy,
    zoomToNode,
    highlightNodes,
    unlightNodes
  };
}
