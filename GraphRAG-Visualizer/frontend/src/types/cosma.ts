/**
 * Cosma 数据类型定义
 * 定义从后端 API 获取的 Cosma Records 格式和前端图谱数据结构
 */

export interface CosmaLink {
  type: string;
  target: string;
  target_name: string;
  contexts: string[];
}

export interface CosmaRecord {
  id: string;
  title: string;
  content: string;
  links: CosmaLink[];
  types: string[];
  tags: string[];
  metas: Record<string, any>;
}

export interface CosmaDataResponse {
  records: CosmaRecord[];
}

export interface GraphNode {
  key: string;
  attributes: {
    label: string;
    types: string[];
    size: number;
    hidden: boolean;
    x?: number;
    y?: number;
    vx?: number;
    vy?: number;
  };
}

export interface GraphEdge {
  key: string;
  source: string;
  target: string;
  attributes: {
    type: string;
    shape: {
      stroke: string;
      dashInterval: string | null;
    };
  };
}

export interface CosmaGraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}
