/**
 * 实体提取相关 API
 */
import api from './index'
import type { ExtractRequest, ExtractResponse } from '@/types/api'

/**
 * 提取实体和关系
 * @param data 提取请求数据
 */
export const extractEntities = async (
  data: ExtractRequest
): Promise<ExtractResponse> => {
  return api.post('/extract', data)
}
