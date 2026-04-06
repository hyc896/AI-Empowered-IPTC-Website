#!/bin/bash

# 逐光智慧思政平台 - 启动脚本

echo "================================"
echo "逐光智慧思政平台 - 启动中..."
echo "================================"

# 检查Python环境
if ! command -v python &> /dev/null; then
    echo "错误: 未找到Python环境"
    exit 1
fi

# 检查Redis
if ! command -v redis-cli &> /dev/null; then
    echo "警告: 未找到Redis，Celery任务队列可能无法工作"
fi

# 进入backend目录
cd backend

# 初始化数据库（如果需要）
echo "检查数据库..."
python -c "from database import init_database; init_database()" 2>/dev/null || echo "数据库已存在"

# 启动Celery Worker（后台）
echo "启动Celery Worker..."
celery -A celery_app worker --loglevel=info --pool=solo &
CELERY_PID=$!

# 启动FastAPI服务
echo "启动FastAPI服务..."
python main.py

# 清理
kill $CELERY_PID 2>/dev/null
echo "服务已停止"
