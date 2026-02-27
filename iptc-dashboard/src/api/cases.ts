/**
 * 案例相关 API
 */

import request from './request';
import type { ApiResponse, Case, PaginatedResponse, SearchParams } from '@/types';

/**
 * 获取案例列表
 */
export function getCases(params: SearchParams): Promise<ApiResponse<PaginatedResponse<Case>>> {
  return request({
    url: '/api/v1/iptc/cases',
    method: 'get',
    params: {
      page: params.page || 1,
      page_size: params.pageSize || 20,
      knowledge_point_id: params.knowledgePoint,
      search: params.keyword,
    },
  });
}

/**
 * 获取案例详情
 */
export function getCaseById(id: string): Promise<ApiResponse<Case>> {
  return request({
    url: `/api/v1/iptc/cases/${id}`,
    method: 'get',
  });
}

/**
 * 搜索案例
 */
export function searchCases(params: SearchParams): Promise<ApiResponse<PaginatedResponse<Case>>> {
  return request({
    url: '/api/cases/search',
    method: 'get',
    params,
  });
}

/**
 * 获取相关案例
 */
export function getRelatedCases(caseId: string, limit = 3): Promise<ApiResponse<Case[]>> {
  return request({
    url: `/api/cases/${caseId}/related`,
    method: 'get',
    params: { limit },
  });
}

/**
 * 增加案例浏览量
 */
export function increaseCaseView(caseId: string): Promise<ApiResponse<void>> {
  return request({
    url: `/api/cases/${caseId}/view`,
    method: 'post',
  });
}

/**
 * 删除案例
 */
export function deleteCase(caseId: string): Promise<void> {
  return request({
    url: `/api/v1/iptc/cases/${caseId}`,
    method: 'delete',
  });
}
