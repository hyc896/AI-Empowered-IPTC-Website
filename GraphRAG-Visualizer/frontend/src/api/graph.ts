/**
 * 图谱相关 API
 * 提供文件列表、Cosma 数据获取等接口
 */

import request from './index';
import type { CosmaDataResponse } from '@/types/cosma';

export interface FileInfo {
  file_id: string;
  name: string;
  entity_count: number;
}

export interface FileListResponse {
  files: FileInfo[];
}

export interface ProgressInfo {
  file_id: string;
  status: 'processing' | 'completed' | 'failed';
  progress: number;
  message: string;
  total_blocks?: number;
  current_block?: number;
  entities_count?: number;
  relations_count?: number;
  updated_at: string;
}

export const getFileList = (): Promise<FileListResponse> => {
  return request.get('/graph/files');
};

export const getFileProgress = (fileId: string): Promise<ProgressInfo> => {
  return request.get(`/graph/progress/${fileId}`);
};

export const getCosmaData = (fileId: string): Promise<CosmaDataResponse> => {
  return request.get(`/graph/cosma/${fileId}`);
};

export const deleteFile = (fileId: string): Promise<{ message: string }> => {
  return request.delete(`/graph/files/${fileId}`);
};

export const renameFile = (fileId: string, newName: string): Promise<{ message: string }> => {
  return request.put(`/graph/files/${fileId}`, { new_name: newName });
};

export interface BaikeResult {
  success: boolean;
  title?: string;
  summary?: string;
  info?: Record<string, string>;
  url?: string;
  message?: string;
}

export interface BookInfo {
  title: string;
  author: string;
  cover: string;
  link: string;
  publisher?: string;
  isbn?: string;
  description?: string;
}

export interface BooksResult {
  success: boolean;
  books?: BookInfo[];
  total?: number;
  message?: string;
  from_cache?: boolean;
}

export const searchBaike = (keyword: string): Promise<BaikeResult> => {
  return request.get(`/graph/search/baike`, { params: { keyword } });
};

export const searchBooks = (keyword: string): Promise<BooksResult> => {
  return request.get(`/graph/search/books`, { params: { keyword } });
};
