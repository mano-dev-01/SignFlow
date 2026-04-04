@echo off
title SignFlow Launcher (Windows)
setlocal

set "SCRIPT_DIR=%~dp0"
set "WINDOWS_OVERLAY=%SCRIPT_DIR%"
set "CODE_DIR=%SCRIPT_DIR%.."
set "MODELS_DIR=%CODE_DIR%\Models"
set "COMMON_OVERLAY=%CODE_DIR%\Common\Overlay"
if "%SIGNFLOW_SERVER_URL%"=="" set "SIGNFLOW_SERVER_URL=https://mano-dev-01-signflow-inference.hf.space"

set "PYTHON_EXE=python"
set "VENV_PY=%CODE_DIR%\venv\Scripts\python.exe"
if exist "%VENV_PY%" (
    set "PYTHON_EXE=%VENV_PY%"
) else (
    set "VENV_PY=%CODE_DIR%\Mac\venv\Scripts\python.exe"
    if exist "%VENV_PY%" (
        set "PYTHON_EXE=%VENV_PY%"
    )
)

echo ========================================
echo  SignFlow - Running from Code\Windows
echo ========================================

echo [DEBUG] Current folder: %CD%
echo [DEBUG] Using overlay path: %WINDOWS_OVERLAY%
echo [DEBUG] Python: %PYTHON_EXE%
echo [DEBUG] Models: %MODELS_DIR%

echo [1/1] Starting overlay client...
echo [INFO] Using remote server: %SIGNFLOW_SERVER_URL%
start "SignFlow Overlay" cmd /k "cd /d "%WINDOWS_OVERLAY%" && echo [OVERLAY] Starting... && echo [OVERLAY] Remote server: %SIGNFLOW_SERVER_URL% && "%PYTHON_EXE%" overlay_remote.py --server %SIGNFLOW_SERVER_URL%"

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

endlocal
