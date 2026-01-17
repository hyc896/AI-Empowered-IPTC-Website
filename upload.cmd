@echo off
cd /d D:\AI-Empowered~1\message_platform
git add .
git commit -m "Update"
git remote add new-origin https://github.com/hyc896/AI-Empowered-IPTC-Website.git
git push -u new-origin main
git remote rename origin old-origin
git remote rename new-origin origin
git remote -v
pause
