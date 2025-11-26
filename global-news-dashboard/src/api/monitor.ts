import axiosInstance from './index'

export interface ComponentStatus {
  status: 'healthy' | 'unhealthy' | 'degraded' | 'error' | 'unknown'
  error?: string
}

export interface RedisStatus extends ComponentStatus {
  broker_connected: boolean
  backend_connected: boolean
  details?: {
    redis_version?: string
    connected_clients?: number
    used_memory_human?: string
    uptime_in_seconds?: number
  }
}

export interface WorkerStatus extends ComponentStatus {
  count: number
  workers: string[]
  active_tasks: number
  busy?: boolean  // Worker正忙于执行任务（Solo Pool模式下无法响应inspect）
  worker_details?: Record<string, {
    pool: string
    concurrency: number
    active_tasks: number
    reserved_tasks: number
    registered_tasks: number
  }>
}

export interface BeatStatus extends ComponentStatus {
  scheduled_tasks: number
  registered_tasks?: number
}

export interface DatabaseStatus extends ComponentStatus {
  response_ms: number
}

export interface ChromaDBStatus extends ComponentStatus {
  collections: number
  mode: string
}

export interface CollectorStats {
  name: string
  display_name: string
  category: string
  status: 'healthy' | 'unhealthy' | 'degraded'
  interval: number
  total_runs: number
  success_count: number
  failure_count: number
  last_run_at: string | null
  last_run_ago: string
  next_run_in: string | null
  last_error: string | null
}

export interface SystemMonitorResponse {
  overall_status: 'healthy' | 'unhealthy' | 'degraded'
  uptime: string | null
  timestamp: string
  components: {
    redis: RedisStatus
    celery_worker: WorkerStatus
    celery_beat: BeatStatus
    database: DatabaseStatus
    chromadb: ChromaDBStatus
  }
  collectors: CollectorStats[]
  summary: {
    total_collectors: number
    healthy_collectors: number
    total_runs: number
    total_success: number
    total_failures: number
  }
}

export interface ActiveTask {
  id: string
  name: string
  args: string[]
  worker: string
  started_at: number | null
  status: 'running'
}

export interface RecentTask {
  name: string
  source: string
  completed_at: string
  success: boolean
  error: string | null
  status: 'success' | 'failed'
}

export interface PendingTask {
  id: string
  name: string
  full_name: string
  args: string[]
  priority: number
  queue: string
  eta: string | null
  time_limit: number | null
}

export interface QueueInfo {
  pending_tasks: number
  tasks: PendingTask[]
}

export interface QueueStatus {
  queues: Record<string, QueueInfo>
  active_tasks: ActiveTask[]
  recent_tasks: RecentTask[]
  error?: string
}

export const monitorApi = {
  getSystemStatus(): Promise<SystemMonitorResponse> {
    return axiosInstance.get('/api/v1/monitor/system').then(res => res.data)
  },

  getRedisStatus(): Promise<RedisStatus> {
    return axiosInstance.get('/api/v1/monitor/redis').then(res => res.data)
  },

  getWorkersStatus(): Promise<WorkerStatus> {
    return axiosInstance.get('/api/v1/monitor/workers').then(res => res.data)
  },

  getQueueStatus(): Promise<QueueStatus> {
    return axiosInstance.get('/api/v1/monitor/queues').then(res => res.data)
  },

  getCollectorsDetail(): Promise<CollectorStats[]> {
    return axiosInstance.get('/api/v1/monitor/collectors/detail').then(res => res.data)
  },

  triggerCollector(sourceName: string): Promise<{ success: boolean; task_id: string }> {
    return axiosInstance.post(`/api/v1/collectors/${sourceName}/trigger`).then(res => res.data)
  },

  clearQueue(queueName: string): Promise<{ queue: string; cleared_tasks: number }> {
    return axiosInstance.delete(`/api/v1/monitor/queues/${queueName}`).then(res => res.data)
  }
}
