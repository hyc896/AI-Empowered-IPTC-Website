/**
 * 统计数据相关 API
 */

import request from './request';
import type { ApiResponse, Statistics } from '@/types';

/**
 * 获取统计数据
 */
export function getStatistics(): Promise<ApiResponse<Statistics>> {
  return request({
    url: '/api/statistics',
    method: 'get',
  });
}

/**
 * 获取热门知识点
 */
export function getHotKnowledgePoints(limit = 10): Promise<ApiResponse<Array<{ name: string; count: number }>>> {
  return request({
    url: '/api/statistics/hot-knowledge-points',
    method: 'get',
    params: { limit },
  });
}

/**
 * 获取最新案例
 */
export function getRecentCases(limit = 5): Promise<ApiResponse<Array<any>>> {
  return request({
    url: '/api/statistics/recent-cases',
    method: 'get',
    params: { limit },
  });
}
