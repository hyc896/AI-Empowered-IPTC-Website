@echo off
echo Starting Message Platform Server...
cd /d "D:\TechWork\message_platform"
start /b python backend/main.py
echo Message Platform started on http://localhost:11523
pause