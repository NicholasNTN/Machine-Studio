@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] Hay chay install.bat truoc.
  pause
  exit /b 1
)
echo ===============================================
echo Optional: cai Demucs de tach giong goc / nhac nen
echo Luu y: Torch + Demucs co the ton nhieu dung luong.
echo ===============================================
".venv\Scripts\python.exe" -m pip install --upgrade demucs
pause
