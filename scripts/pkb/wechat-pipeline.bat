@echo off
REM Process WeChat/OpenClaw/Hermes drop files into captures, review queue, and optional Hugo build.
REM Usage:
REM   scripts\pkb\wechat-pipeline.bat
REM   scripts\pkb\wechat-pipeline.bat --build

cd /d D:\MyLab\Hugo\bubblevan.github.io
if %errorlevel% neq 0 (
    echo ERROR: Cannot cd to repo root
    exit /b 1
)

python -m scripts.pkb.cli process-drop
if %errorlevel% neq 0 exit /b %errorlevel%

python -m scripts.pkb.cli validate-captures
if %errorlevel% neq 0 exit /b %errorlevel%

python -m scripts.pkb.cli review-captures --since today
if %errorlevel% neq 0 exit /b %errorlevel%

if /I "%1"=="--build" (
    npm run build
    if %errorlevel% neq 0 exit /b %errorlevel%
)

echo WeChat pipeline complete.
