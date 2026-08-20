@echo off
setlocal
cd /d "%~dp0"

echo ====================================================
echo     MachineScope Studio v0.3 - INSTALL
echo ====================================================

where py >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Khong tim thay Python Launcher "py".
  echo Cai Python 3.11+ va tick Add Python to PATH.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo [1/4] Tao virtual environment...
  py -3.11 -m venv .venv
  if errorlevel 1 py -m venv .venv
)

echo [2/4] Update pip...
".venv\Scripts\python.exe" -m pip install --upgrade pip

echo [3/4] Cai dependencies...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  echo [ERROR] Cai package that bai.
  pause
  exit /b 1
)

echo.
echo [Downloader] Cap nhat yt-dlp nightly + networking dependencies...
".venv\Scripts\python.exe" -m pip install -U --pre "yt-dlp[default]" "curl-cffi"
if errorlevel 1 (
  echo [WARNING] Khong cap nhat duoc yt-dlp nightly. App van co the chay ban da cai.
)

echo [4/4] Kiem tra FFmpeg...
where ffmpeg >nul 2>nul
if errorlevel 1 (
  if exist "tools\ffmpeg.exe" (
    echo [OK] Tim thay tools\ffmpeg.exe
  ) else (
    echo [WARNING] Chua co FFmpeg.
    echo Copy ffmpeg.exe va ffprobe.exe vao thu muc tools\
  )
) else (
  echo [OK] FFmpeg da co trong PATH.
)

echo.
echo ====================================================
echo CAI DAT XONG - CHAY run.bat
echo ====================================================
pause
