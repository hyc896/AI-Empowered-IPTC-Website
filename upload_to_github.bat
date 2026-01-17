@echo off
chcp 65001 >nul
cd /d "D:\AI-Empowered IPTC Website\一期"

echo ============================================
echo 上传一期项目到GitHub新仓库
echo 仓库地址: https://github.com/hyc896/AI-Empowered-IPTC-Website.git
echo 注意: 已排除 global-news-dashboard 前端
echo ============================================
echo.

echo [Step 1] 检查Git仓库状态...
git status
echo.

echo [Step 2] 添加所有更改到暂存区（遵循.gitignore规则）...
git add .
if %errorlevel% neq 0 (
    echo [ERROR] git add 失败
    pause
    exit /b 1
)
echo.

echo [Step 3] 提交更改...
git commit -m "Initial commit: Upload Phase 1 project (exclude global-news-dashboard)"
if %errorlevel% neq 0 (
    echo [WARNING] git commit 失败或没有需要提交的更改
)
echo.

echo [Step 4] 配置远程仓库...
git remote remove origin 2>nul
git remote add origin https://github.com/hyc896/AI-Empowered-IPTC-Website.git
if %errorlevel% neq 0 (
    echo [WARNING] 远程仓库配置可能已存在
)
echo.

echo [Step 5] 推送到GitHub（首次推送使用 -f 强制）...
git branch -M main
git push -u origin main -f
if %errorlevel% neq 0 (
    echo [ERROR] git push 失败
    echo 可能原因:
    echo 1. 网络连接问题
    echo 2. GitHub 凭据未配置
    echo 3. 仓库访问权限不足
    pause
    exit /b 1
)
echo.

echo ============================================
echo [SUCCESS] 上传完成！
echo ============================================
echo 远程仓库: https://github.com/hyc896/AI-Empowered-IPTC-Website.git
echo.
echo 已排除的内容:
echo - global-news-dashboard/ 前端项目
echo - node_modules/
echo - __pycache__/
echo - data/chromadb/ 和 data/chromadb_mp/
echo - logs/
echo - .env 环境变量
echo - full_database_dump.sql
echo - 其他 .gitignore 中定义的文件
echo.
pause
