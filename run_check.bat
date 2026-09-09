@echo off
cd /d "%~dp0"
set PYTHONUTF8=1
"%LOCALAPPDATA%\Programs\Python\Python312\python.exe" check_canyon.py >> check_log.txt 2>&1
