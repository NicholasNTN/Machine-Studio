@echo off
setlocal
cd /d "%~dp0"

echo ==============================================
echo MachineScope Studio - FFmpeg Diagnostic
echo ==============================================
echo.

if exist "tools\ffprobe.exe" (
  echo [LOCAL] tools\ffprobe.exe:
  "tools\ffprobe.exe" -version
  echo.
) else (
  echo [LOCAL] Khong co tools\ffprobe.exe
)

where ffprobe
echo.
where ffmpeg
echo.
pause
