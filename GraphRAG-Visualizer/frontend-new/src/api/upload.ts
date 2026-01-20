/**
 * 文件上传相关 API
 */
import api from './index'
import type { UploadResponse } from '@/types/api'

/**
 * 上传 PDF 文件
 * @param file PDF 文件
 * @param pageStart 起始页码
 * @param pageEnd 结束页码
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

  return api.post('/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}
