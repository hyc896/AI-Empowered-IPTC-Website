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










