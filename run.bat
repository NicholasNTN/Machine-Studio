@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] Chua cai dat. Hay chay install.bat truoc.
  pause
  exit /b 1
)
if not exist "logs" mkdir "logs"
echo.>> "logs\console.log"
echo ===== START %date% %time% =====>> "logs\console.log"
".venv\Scripts\python.exe" app.py >> "logs\console.log" 2>&1
set RC=%ERRORLEVEL%
if not "%RC%"=="0" (
  echo.
  echo [ERROR] MachineScope Studio vua thoat bat thuong. Exit code: %RC%
  echo Xem logs\console.log va logs\crash.log.
  echo Ban co the chay open_crash_logs.bat.
  pause
)
exit /b %RC%
