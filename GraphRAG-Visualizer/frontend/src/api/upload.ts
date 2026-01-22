/**
 * 文件上传 API
 */

import request from './index';

export const uploadFile = async (file: File): Promise<{ file_id: string }> => {
  const formData = new FormData();
  formData.append('file', file);
  return request.post('/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
};
