@echo off
REM PKB Drop Processor - Cron Runner (Windows)
REM Called by Windows Task Scheduler or Hermes cron
REM Usage: scripts\pkb\cron-process-drop.bat

cd /d D:\MyLab\Hugo\bubblevan.github.io
if %errorlevel% neq 0 (
    echo ERROR: Cannot cd to repo root
    exit /b 1
)

echo %date% %time% - Running process-drop...
python -m scripts.pkb.cli process-drop
echo %date% %time% - Done.
