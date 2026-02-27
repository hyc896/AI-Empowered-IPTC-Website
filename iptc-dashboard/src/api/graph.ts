/**
 * 知识图谱相关 API
 */

import request from './request';
import type { ApiResponse, GraphData, KnowledgePoint } from '@/types';

/**
 * 获取完整知识图谱数据
 */
export function getGraphData(): Promise<ApiResponse<GraphData>> {
  return request({
    url: '/api/graph/data',
    method: 'get',
  });
}

/**
 * 获取知识点列表
 */
export function getKnowledgePoints(): Promise<ApiResponse<KnowledgePoint[]>> {
  return request({
    url: '/api/knowledge-points',
    method: 'get',
  });
}

/**
 * 获取知识点详情
 */
export function getKnowledgePointById(id: string): Promise<ApiResponse<KnowledgePoint>> {
  return request({
    url: `/api/knowledge-points/${id}`,
    method: 'get',
  });
}

/**
 * 获取案例的局部图谱
 */
export function getCaseGraph(caseId: string): Promise<ApiResponse<GraphData>> {
  return request({
    url: `/api/graph/case/${caseId}`,
    method: 'get',
  });
}

/**
 * 获取知识点的局部图谱
 */
export function getKnowledgePointGraph(knowledgePointId: string): Promise<ApiResponse<GraphData>> {
  return request({
    url: `/api/graph/knowledge-point/${knowledgePointId}`,
    method: 'get',
  });
}

/**
 * 获取所有书籍列表
 */
export function getBookList(): Promise<ApiResponse<any>> {
  return request({
    url: '/api/books/list',
    method: 'get',
  });
}

/**
 * 获取指定书籍的知识图谱
 */
export function getBookGraph(bookId: string): Promise<ApiResponse<GraphData>> {
  return request({
    url: `/api/books/${bookId}/graph`,
    method: 'get',
  });
}

/**
 * 获取节点为中心的子图
 */
export function getNodeSubgraph(data: { node_id: string; book_id?: string; depth: number }): Promise<ApiResponse<GraphData>> {
  return request({
    url: '/api/books/node/subgraph',
    method: 'post',
    data,
  });
}

/**
 * 获取层级知识图谱数据（书->章->节->知识点）
 */
export function getKnowledgeGraphData(bookId?: string): Promise<ApiResponse<GraphData>> {
  return request({
    url: '/api/v1/knowledge-graph/data',
    method: 'get',
    params: bookId ? { book_id: bookId } : undefined,
  });
}

/**
 * 获取知识图谱书籍列表
 */
export function getKnowledgeGraphBooks(): Promise<ApiResponse<any[]>> {
  return request({
    url: '/api/v1/knowledge-graph/books',
    method: 'get',
  });
}

/**
 * 获取知识点详细信息
 */
export function getKnowledgePointDetail(kpId: string): Promise<ApiResponse<any>> {
  return request({
    url: `/api/v1/knowledge-graph/knowledge-point/${kpId}`,
    method: 'get',
  });
}










