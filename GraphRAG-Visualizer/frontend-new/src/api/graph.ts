/**
 * 图谱查询相关 API
 */
import api from './index'
import type { GraphVisualizeResponse } from '@/types/graph'

/**
 * 获取图谱可视化数据
 * @param fileId 文件 ID
 * @param pageRange 页面范围，如 "1-20"
 */
export const getGraphData = async (
  fileId: string,
  pageRange?: string
): Promise<GraphVisualizeResponse> => {
  const params = pageRange ? { page_range: pageRange } : {}
  return api.get(`/graph/visualize/${fileId}`, { params })
}
