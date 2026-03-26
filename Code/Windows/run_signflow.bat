@echo off
title SignFlow Launcher (Windows)

set "SCRIPT_DIR=%~dp0"
set "COMMON_OVERLAY=%SCRIPT_DIR%..\Common\Overlay"
if "%SIGNFLOW_SERVER_URL%"=="" set "SIGNFLOW_SERVER_URL=https://mano-dev-01-signflow-inference.hf.space"

echo ========================================
echo  SignFlow - Running from Code\Windows -> Code\Common\Overlay
echo ========================================

echo [DEBUG] Current folder: %CD%

echo [DEBUG] Using common overlay path: %COMMON_OVERLAY%

if not exist "%COMMON_OVERLAY%" (
    echo ERROR: Common overlay directory not found: %COMMON_OVERLAY%
    pause
    exit /b 1
)

echo [1/1] Starting overlay client...
echo [INFO] Using remote server: %SIGNFLOW_SERVER_URL%
start "SignFlow Overlay" cmd /k "cd /d "%COMMON_OVERLAY%" && echo [OVERLAY] Starting... && echo [OVERLAY] Remote server: %SIGNFLOW_SERVER_URL% && python overlay_remote.py --server %SIGNFLOW_SERVER_URL%"

echo.
echo ========================================
echo  The overlay window is now open.
echo  - "SignFlow Overlay" = camera + overlay UI
echo  - Remote inference runs on Hugging Face Space
echo.
echo  Close this window whenever you like.
echo  To stop: close the Overlay window.
echo ========================================
pause
