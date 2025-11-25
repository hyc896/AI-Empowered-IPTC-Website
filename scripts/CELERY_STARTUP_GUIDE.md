# Celery全量改造后的启动指南

## 概述

Celery全量改造后，message_platform的架构变更为：

- **FastAPI**: 仅提供RESTful API服务（端口11528）
- **Celery Worker**: 处理所有采集器任务和AI日报生成任务
- **Celery Beat**: 定时调度任务
- **ChromaDB Server**: 向量数据库服务（端口11530）
- **Redis**: Celery消息队列和结果存储（端口6379）

## 前置要求

### 1. Redis服务运行
确保Redis服务已启动并监听端口6379：
```bash
# Windows: Redis应该已作为系统服务运行
# 检查：
netstat -ano | findstr ":6379"
```

### 2. 安装依赖
```bash
pip install celery==5.5.3 redis kombu
```

## 启动顺序

**必须按以下顺序启动，否则会报错！**

### 步骤1: 启动ChromaDB Server
```bash
cd d:\TechWork\message_platform
scripts\start_chromadb.bat
```

**验证**：
- 终端显示 "Running Chroma on http://0.0.0.0:11530"
- 浏览器访问 http://localhost:11530/api/v1 应返回ChromaDB API信息

### 步骤2: 启动Celery Worker
新开一个终端窗口：
```bash
cd d:\TechWork\message_platform
scripts\start_worker.bat
```

**验证**：
- 终端显示 "celery@hostname ready."
- 显示已注册的任务列表（包含backend.tasks.collector_tasks.run_collector等）

### 步骤3: 启动Celery Beat（定时调度）
新开一个终端窗口：
```bash
cd d:\TechWork\message_platform
scripts\start_beat.bat
```

**验证**：
- 终端显示 "beat: Starting..."
- 显示加载的定时任务列表

### 步骤4: 启动FastAPI服务
新开一个终端窗口：
```bash
cd d:\TechWork\message_platform
python -m uvicorn backend.main:app --host 0.0.0.0 --port 11528
```

**验证**：
- 访问 http://localhost:11528/health 应返回 "healthy"
- 访问 http://localhost:11528/docs 查看API文档

## 手动触发采集器

通过API触发单个消息源的立即采集：
```bash
curl -X POST http://localhost:11528/api/v1/collectors/tonghuashun/trigger
```

返回示例：
```json
{
  "success": true,
  "message": "采集任务已提交到队列: tonghuashun",
  "task_id": "e5f3a2b1-4c8d-4e3f-9a1c-2d3e4f5a6b7c"
}
```

## 手动触发AI日报生成

```bash
curl -X POST "http://localhost:11528/api/v1/ai-reports/generate?report_type=governance"
```

返回示例：
```json
{
  "message": "治理日报生成任务已提交（今天），正在后台执行",
  "report_type": "governance",
  "report_date": "2025-11-23",
  "task_id": "a1b2c3d4-5e6f-7g8h-9i0j-k1l2m3n4o5p6",
  "timestamp": "2025-11-23T15:30:00"
}
```

## 监控任务状态

### 查看Celery任务状态
使用task_id查询任务执行状态：
```bash
curl http://localhost:11528/api/v1/collectors/tonghuashun/task/{task_id}
```

返回示例：
```json
{
  "task_id": "e5f3a2b1-4c8d-4e3f-9a1c-2d3e4f5a6b7c",
  "state": "SUCCESS",
  "result": {
    "success": true,
    "source_name": "tonghuashun",
    "collected_count": 15,
    "duration_seconds": 12.5
  }
}
```

### 查看Worker健康状态
```bash
curl http://localhost:11528/api/v1/collectors/health
```

## 停止服务

**逆序停止**（与启动顺序相反）：

1. 停止FastAPI：在FastAPI终端按 `Ctrl+C`
2. 停止Celery Beat：在Beat终端按 `Ctrl+C`
3. 停止Celery Worker：在Worker终端按 `Ctrl+C`
4. 停止ChromaDB Server：在ChromaDB终端按 `Ctrl+C`

## 常见问题排查

### 问题1: Worker启动失败，报"No module named 'backend.tasks'"
**原因**: 当前工作目录不正确
**解决**: 确保在项目根目录（d:\TechWork\message_platform）下运行脚本

### 问题2: Worker启动时报"Connection refused (Redis)"
**原因**: Redis服务未启动
**解决**: 启动Redis Windows服务

### 问题3: 采集器任务失败，报"ChromaDB connection failed"
**原因**: ChromaDB Server未运行
**解决**: 先运行 scripts\start_chromadb.bat

### 问题4: Beat调度未生效，采集器没有自动运行
**原因**: Celery Beat未启动或配置错误
**解决**:
- 检查scripts\start_beat.bat是否正在运行
- 查看Beat日志，确认定时任务已加载

### 问题5: 采集器任务卡住不执行
**原因**: Worker并发数不足或任务优先级问题
**解决**:
- 调整config.yaml中的`celery.worker.concurrency`（当前为4）
- 检查Worker日志，确认任务是否在队列中

## 环境变量配置

可选的环境变量（在启动脚本中设置）：

```bash
# ChromaDB模式（server或local，默认server）
set CHROMADB_MODE=server

# Celery日志级别（DEBUG/INFO/WARNING/ERROR）
set CELERY_LOG_LEVEL=INFO

# Worker并发数（覆盖config.yaml配置）
set CELERY_WORKER_CONCURRENCY=4
```

## 下一步：安装Flower监控工具

安装Flower后可通过Web界面监控Celery任务：
```bash
pip install flower
flower -A backend.tasks --port=5555 --broker=redis://localhost:6379/1
```

访问 http://localhost:5555 查看Celery监控面板。
