@echo off
chcp 65001 >nul
cd /d "D:\AI-Empowered IPTC Website\message_platform"

echo ============================================
echo Step 1: 添加所有更改到暂存区
echo ============================================
git add .
if %errorlevel% neq 0 (
    echo [ERROR] git add 失败
    pause
    exit /b 1
)

echo.
echo ============================================
echo Step 2: 提交更改
echo ============================================
git commit -m "Update: 准备上传到新远程仓库（排除 global-news-dashboard）"
if %errorlevel% neq 0 (
    echo [WARNING] git commit 失败或没有需要提交的更改
)

echo.
echo ============================================
echo Step 3: 添加新远程仓库
echo ============================================
git remote add new-origin https://github.com/hyc896/AI-Empowered-IPTC-Website.git
if %errorlevel% neq 0 (
    echo [WARNING] 新远程仓库可能已存在，尝试更新...
    git remote set-url new-origin https://github.com/hyc896/AI-Empowered-IPTC-Website.git
)

echo.
echo ============================================
echo Step 4: 推送到新仓库
echo ============================================
git push -u new-origin main
if %errorlevel% neq 0 (
    echo [ERROR] git push 失败
    echo 可能需要：
    echo 1. 检查网络连接
    echo 2. 确认 GitHub 凭据
    echo 3. 确认仓库访问权限
    pause
    exit /b 1
)

echo.
echo ============================================
echo Step 5: 重命名远程仓库（设置新仓库为默认）
echo ============================================
git remote rename origin old-origin
git remote rename new-origin origin

echo.
echo ============================================
echo Step 6: 验证远程仓库配置
echo ============================================
git remote -v

echo.
echo ============================================
echo [SUCCESS] 所有操作完成！
echo ============================================
echo 当前远程仓库配置：
echo - origin: https://github.com/hyc896/AI-Empowered-IPTC-Website.git (默认)
echo - old-origin: https://github.com/Infinity-light/message_platform.git (备份)
echo.
pause
