@echo off
title Weather Backend Server

echo ============================================================
echo   Weather Aggregator - Backend Server Launcher
echo ============================================================
echo.

set "PYTHON_VENV=C:\Users\pro 14\.workbuddy\binaries\python\envs\default\Scripts\python.exe"
set "SCRIPT_DIR=%~dp0"

if not exist "%PYTHON_VENV%" goto :try_system_python

echo [OK] Using venv Python
echo.
echo Starting server in background...
start "Weather Backend Server" "%PYTHON_VENV%" "%SCRIPT_DIR%app.py"

echo Waiting for server to be ready...
set TRY=0
:wait_loop
set /a TRY+=1
if %TRY% gtr 30 goto :timeout
"%PYTHON_VENV%" -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health',timeout=2)" >nul 2>&1
if %errorlevel% equ 0 goto :ready
timeout /t 1 /nobreak >nul
goto :wait_loop

:ready
echo Server is ready! Opening browser...
set /a RND=%RANDOM%*%RANDOM%
start "" "http://localhost:8000/?_t=%RND%"
echo.
echo Browser opened. Keep the server window open while using.
echo Close the server window or press Ctrl+C there to stop.
pause
goto :eof

:try_system_python
echo [WARN] venv not found, trying system Python...
python --version >nul 2>&1
if %errorlevel% neq 0 goto :no_python
echo [OK] Using system Python
echo.
echo Starting server in background...
start "Weather Backend Server" python "%SCRIPT_DIR%app.py"

echo Waiting for server to be ready...
set TRY=0
:wait_loop2
set /a TRY+=1
if %TRY% gtr 30 goto :timeout
python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health',timeout=2)" >nul 2>&1
if %errorlevel% equ 0 goto :ready2
timeout /t 1 /nobreak >nul
goto :wait_loop2

:ready2
echo Server is ready! Opening browser...
set /a RND=%RANDOM%*%RANDOM%
start "" "http://localhost:8000/?_t=%RND%"
echo.
echo Browser opened. Keep the server window open while using.
pause
goto :eof

:timeout
echo [ERROR] Server failed to start within 30 seconds.
echo Possible causes:
echo   - Port 8000 is already in use (close other instances first)
echo   - Python packages missing (run: pip install fastapi uvicorn httpx)
echo   - config.json has syntax errors
echo.
pause
goto :eof

:no_python
echo [ERROR] Python not found! Please install Python 3.10+
echo.
pause
goto :eof
