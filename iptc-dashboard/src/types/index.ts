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

// 来源消息类型
export interface SourceMessage {
  title: string;
  url: string | null;
  source_table: string;
  published_at: string | null;
}

// 案例类型
export interface Case {
  id: string;
  title: string;
  content: string;
  summary: string;
  source: string;
  sourceUrl?: string;
  sourceMessages?: SourceMessage[];  // 新增：所有来源消息的详细信息
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
  knowledgePoint?: string;  // 单个知识点ID（用于后端API）
  knowledgePoints?: string[];  // 多个知识点（用于前端筛选）
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
  total_cases: number;                    // 案例总数
  total_knowledge_points: number;         // 知识点总数
  generated_knowledge_points: number;     // 已生成案例的知识点数
  total_relations: number;                // 消息-知识点关联总数
  latest_cases: Array<{                   // 最近生成的案例
    id: string;
    title: string;
    created_at: string;
  }>;
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

// 书籍信息
export interface BookInfo {
  book_id: string;
  book_name: string;
  upload_time: string;
  entity_count: number;
  relation_count: number;
}

// 书籍列表响应
export interface BookListResponse {
  books: BookInfo[];
  total: number;
}

// 节点子图请求
export interface NodeSubgraphRequest {
  node_id: string;
  book_id?: string;
  depth: number;
}
