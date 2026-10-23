@echo off
setlocal
cd /d "%~dp0.."
if not exist ".venv\Scripts\python.exe" (
  echo Prima esegui scripts\setup-windows.bat.
  exit /b 1
)
".venv\Scripts\python.exe" scripts\start.py %*
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" pause
exit /b %RESULT%
