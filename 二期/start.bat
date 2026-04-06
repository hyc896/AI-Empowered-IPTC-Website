@echo off
chcp 65001 >nul
echo ================================
echo 逐光智慧思政平台 - 启动中...
echo ================================

REM 检查Python环境
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到Python环境
    pause
    exit /b 1
)

REM 进入backend目录
cd backend

REM 初始化数据库
echo 检查数据库...
python -c "from database import init_database; init_database()" 2>nul

REM 启动Celery Worker（新窗口）
echo 启动Celery Worker...
start "Celery Worker" cmd /k "celery -A celery_app worker --loglevel=info --pool=solo"

REM 等待2秒
timeout /t 2 /nobreak >nul

REM 启动FastAPI服务
echo 启动FastAPI服务...
python main.py

pause
