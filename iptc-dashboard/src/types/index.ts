/**
 * 通用类型定义
 */

// API 响应通用格式
export interface ApiResponse<T = any> {
  code: number;
  message: string;
  data: T;
}

// 分页参数
export interface PaginationParams {
  page: number;
  pageSize: number;
}

// 分页响应
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

// 案例类型
export interface Case {
  id: string;
  title: string;
  content: string;
  summary: string;
  source: string;
  sourceUrl?: string;
  publishDate: string;
  viewCount: number;
  knowledgePoints: string[];
  createdAt: string;
  updatedAt: string;
}

// 知识点类型
export interface KnowledgePoint {
  id: string;
  name: string;
  description: string;
  category?: string;
  relatedCaseCount: number;
}

// 图谱节点类型
export interface GraphNode {
  id: string;
  label: string;
  type: 'case' | 'knowledge';
  size?: number;
  style?: {
    fill?: string;
    stroke?: string;
    lineWidth?: number;
  };
  data?: Case | KnowledgePoint;
}

// 图谱边类型
export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  type?: 'case-knowledge' | 'knowledge-knowledge';
  style?: {
    stroke?: string;
    lineWidth?: number;
    lineDash?: number[];
  };
}

// 图谱数据
export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

// 搜索参数
export interface SearchParams extends PaginationParams {
  keyword?: string;
  knowledgePoints?: string[];
  startDate?: string;
  endDate?: string;
  sortBy?: 'relevance' | 'date';
  sortOrder?: 'asc' | 'desc';
}

// 筛选条件
export interface FilterOptions {
  knowledgePoints: string[];
  dateRange?: [string, string];
  sources?: string[];
}

// 用户信息
export interface UserInfo {
  id: string;
  username: string;
  email?: string;
  avatar?: string;
  role?: string;
}

// 统计数据
export interface Statistics {
  totalCases: number;
  totalKnowledgePoints: number;
  totalTopics: number;
  recentUpdates: number;
}

// 图谱布局选项
export interface GraphLayoutConfig {
  type: 'force' | 'circular' | 'radial' | 'dagre';
  preventOverlap?: boolean;
  nodeSpacing?: number;
  linkDistance?: number;
}

// 加载状态
export interface LoadingState {
  loading: boolean;
  error: string | null;
}
