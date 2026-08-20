@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] Chua co .venv. Hay chay install.bat truoc.
  pause
  exit /b 1
)

echo ================================================
echo Update yt-dlp NIGHTLY + curl-cffi
echo ================================================
".venv\Scripts\python.exe" -m pip install -U --pre "yt-dlp[default]" "curl-cffi"

echo.
echo Version:
".venv\Scripts\python.exe" -m yt_dlp --version
echo.
pause
