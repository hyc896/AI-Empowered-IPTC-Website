export interface ApiResponse<T = any> {
  data: T
  code: number
  message: string
}

export interface PaginationParams {
  page: number
  size: number
}




