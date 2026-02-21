/**
 * 采集状态相关 API
 */

import request from './request';

/**
 * 采集状态响应类型
 */
export interface CollectionStatus {
  total_sources: number;
  active_sources: number;
  total_messages: number;
  chinese_messages: number;
  sources: Array<{
    name: string;
    table: string;
    is_active: boolean;
    is_chinese: boolean;
    message_count: number;
    latest_crawled_at: string | null;
  }>;
  updated_at: string;
}

/**
 * 匹配状态响应类型
 */
export interface MatchingStatus {
  total_knowledge_points: number;
  matched_knowledge_points: number;
  generated_knowledge_points: number;
  total_cases: number;
  matching_progress: number;
  generation_progress: number;
  recent_cases: Array<{
    id: string;
    title: string;
    created_at: string;
  }>;
  updated_at: string;
}

/**
 * 调度器信息响应类型
 */
export interface SchedulerInfo {
  case_generation: {
    interval_seconds: number;
    interval_text: string;
    next_run_in_seconds: number;
    last_run_at: string | null;
  };
  batch_match: {
    interval_seconds: number;
    interval_text: string;
    next_run_in_seconds: number;
    last_run_at: string | null;
  };
  updated_at: string;
}

/**
 * 获取采集状态
 */
export function getCollectionStatus(): Promise<CollectionStatus> {
  return request({
    url: '/api/v1/collection/status',
    method: 'get',
  });
}

/**
 * 获取匹配状态
 */
export function getMatchingStatus(): Promise<MatchingStatus> {
  return request({
    url: '/api/v1/collection/matching-status',
    method: 'get',
  });
}

/**
 * 获取调度器信息
 */
export function getSchedulerInfo(): Promise<SchedulerInfo> {
  return request({
    url: '/api/v1/collection/scheduler-info',
    method: 'get',
  });
}
