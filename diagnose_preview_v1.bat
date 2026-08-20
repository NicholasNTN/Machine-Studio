@echo off
setlocal
cd /d "%~dp0"

echo ==============================================
echo MachineScope Studio v1.0 - Preview Diagnostics
echo ==============================================
echo.

if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] Khong co .venv. Hay chay install.bat.
  pause
  exit /b 1
)

".venv\Scripts\python.exe" -c "from PySide6 import __version__; from PySide6.QtMultimedia import QVideoSink,QVideoFrame,QMediaPlayer; print('PySide6:',__version__); print('QVideoSink: OK'); print('setVideoSink:',hasattr(QMediaPlayer,'setVideoSink')); print('QVideoFrame.toImage:',hasattr(QVideoFrame,'toImage'))"

echo.
echo FFmpeg:
where ffmpeg
where ffprobe
echo.
pause
