@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Hay chay install.bat truoc.
  pause
  exit /b 1
)

".venv\Scripts\python.exe" -m pip install --upgrade pyinstaller
".venv\Scripts\pyinstaller.exe" --noconfirm --clean --windowed ^
  --name "MachineStudio" ^
  --collect-all PySide6 ^
  --collect-all google.genai ^
  --collect-all edge_tts ^
  app.py

echo.
echo Build xong. EXE nam trong dist\MachineStudio\
echo Copy tools\ffmpeg.exe va tools\ffprobe.exe vao dist\MachineStudio\tools\ neu can.
echo Demucs la optional; nen test bang run.bat truoc khi build.
pause
