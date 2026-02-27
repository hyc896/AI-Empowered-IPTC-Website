/**
 * Cosma 数据转换工具
 * 将后端返回的 Cosma Records 转换为 Graphology 图数据结构
 */

import type { CosmaRecord, CosmaGraphData, GraphNode, GraphEdge } from '@/types/cosma';

export function convertRecordsToGraph(records: CosmaRecord[]): CosmaGraphData {
  const nodes: GraphNode[] = records.map(record => ({
    key: record.id,
    attributes: {
      label: record.title,
      types: record.types,
      size: Math.min(10 + (record.metas.mention_count || 1) * 2, 30),
      hidden: false
    }
  }));

  const edges: GraphEdge[] = [];
  let edgeIndex = 0;

  records.forEach(record => {
    record.links.forEach(link => {
      edges.push({
        key: `edge-${edgeIndex++}`,
        source: record.id,
        target: link.target,
        attributes: {
          type: link.type,
          shape: {
            stroke: 'simple',
            dashInterval: null
          }
        }
      });
    });
  });

  return { nodes, edges };
}
