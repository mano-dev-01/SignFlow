@echo off
setlocal
title SignFlow Model Server

set "SCRIPT_DIR=%~dp0"
set "OVERLAY_DIR=%SCRIPT_DIR%Overlay"

if not exist "%OVERLAY_DIR%\server.py" (
    echo ERROR: Could not find "%OVERLAY_DIR%\server.py"
    pause
    exit /b 1
)

if not defined PORT set "PORT=8000"

set "PYTHON_EXE=python"
set "PYTHON_ARGS="
set "VENV_PY=%SCRIPT_DIR%..\venv\Scripts\python.exe"
if exist "%VENV_PY%" (
    set "PYTHON_EXE=%VENV_PY%"
) else (
    where python >nul 2>nul
    if errorlevel 1 (
        where py >nul 2>nul
        if errorlevel 1 (
            echo ERROR: No Python interpreter found.
            echo Install Python or create Code\venv first.
            pause
            exit /b 1
        )
        set "PYTHON_EXE=py"
        set "PYTHON_ARGS=-3"
    )
)

set "HOSTNAME_VALUE=%COMPUTERNAME%"
set "LOCALHOST_URL=http://localhost:%PORT%"
set "LAN_IP="
set "PUBLIC_IP="

for /f "usebackq delims=" %%I in (`powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='SilentlyContinue'; $ip=([System.Net.Dns]::GetHostAddresses([System.Net.Dns]::GetHostName()) | Where-Object { $_.AddressFamily -eq [System.Net.Sockets.AddressFamily]::InterNetwork -and $_.IPAddressToString -notlike '127.*' } | Select-Object -ExpandProperty IPAddressToString -First 1); if($ip){$ip}"`) do set "LAN_IP=%%I"

for /f "usebackq delims=" %%I in (`powershell -NoProfile -ExecutionPolicy Bypass -Command "$ProgressPreference='SilentlyContinue'; try { (Invoke-RestMethod 'https://api.ipify.org?format=text' -TimeoutSec 5).ToString().Trim() } catch {}"`) do set "PUBLIC_IP=%%I"

echo ========================================
echo  SignFlow Model Server
echo ========================================
echo Working directory: %OVERLAY_DIR%
echo Python: %PYTHON_EXE% %PYTHON_ARGS%
echo Hostname: %HOSTNAME_VALUE%
echo Port: %PORT%
echo.
echo Health check:
echo   %LOCALHOST_URL%/health

if defined LAN_IP (
    echo LAN URL:
    echo   http://%LAN_IP%:%PORT%/health
)

if defined PUBLIC_IP (
    echo Public IP:
    echo   %PUBLIC_IP%
    echo Public URL:
    echo   http://%PUBLIC_IP%:%PORT%/health
    echo Note: public access still requires firewall and router port forwarding.
) else (
    echo Public IP:
    echo   unavailable
)

echo.
echo Starting server...
echo ========================================
echo.

pushd "%OVERLAY_DIR%"
call "%PYTHON_EXE%" %PYTHON_ARGS% server.py
set "EXIT_CODE=%ERRORLEVEL%"
popd

if not "%EXIT_CODE%"=="0" (
    echo.
    echo Server exited with code %EXIT_CODE%.
    pause
)

endlocal & exit /b %EXIT_CODE%
