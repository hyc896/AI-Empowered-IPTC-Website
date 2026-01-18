/**
 * API 调用封装
 * 封装所有后端 API 调用
 */

import axios from 'axios'
import type { UploadResponse, ExtractRequest, ExtractResponse } from '../types'

const api = axios.create({
  baseURL: '/api',
  timeout: 60000
})

/**
 * 上传 PDF 文件
 */
export const uploadPDF = async (
  file: File,
  pageStart: number = 1,
  pageEnd: number = 20
): Promise<UploadResponse> => {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('page_start', pageStart.toString())
  formData.append('page_end', pageEnd.toString())

  const response = await api.post<UploadResponse>('/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
  return response.data
}

/**
 * 提取实体
 */
export const extractEntities = async (
  request: ExtractRequest
): Promise<ExtractResponse> => {
  const response = await api.post<ExtractResponse>('/extract', request)
  return response.data
}

export default api
