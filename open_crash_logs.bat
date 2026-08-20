@echo off
setlocal
cd /d "%~dp0"
if not exist "logs" mkdir "logs"
if not exist "logs\console.log" type nul > "logs\console.log"
if not exist "logs\crash.log" type nul > "logs\crash.log"
start "" notepad.exe "logs\console.log"
start "" notepad.exe "logs\crash.log"
