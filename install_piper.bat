@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] Chua co .venv.
  echo Hay chay install.bat truoc.
  pause
  exit /b 1
)

echo ===============================================
echo MachineScope - Install / Update Piper Offline TTS
echo ===============================================

".venv\Scripts\python.exe" -m pip install -U "piper-tts"
if errorlevel 1 (
  echo.
  echo [ERROR] Khong cai duoc piper-tts.
  pause
  exit /b 1
)

echo.
echo [OK] Piper da san sang.
echo Voice model se chi tai khi ban chon trong Voice Manager.
echo.
".venv\Scripts\python.exe" -c "import piper; print('Piper import OK')"
pause
