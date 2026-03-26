@echo off
echo Starting SignFlow services...

REM Start the model server
start "" cmd /c "..\Common\run_model_server.bat"

REM Start the website
start "" cmd /c "python ..\Website-LandingPage\main.py"

REM Start ngrok tunnel for port 5000
start "" cmd /c "ngrok http 5000"

echo All services started.
pause