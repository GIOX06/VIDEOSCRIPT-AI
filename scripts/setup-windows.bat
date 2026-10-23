@echo off
setlocal
cd /d "%~dp0.."
for %%T in (uv node npm ffmpeg ffprobe) do (
  where %%T >nul 2>nul
  if errorlevel 1 (
    echo Manca %%T. Installa i prerequisiti descritti in README.md e riapri il terminale.
    exit /b 1
  )
)
if "%~1"=="--base" (
  uv sync --frozen
) else if "%~1"=="" (
  uv sync --frozen --extra ai
) else (
  echo Uso: scripts\setup-windows.bat [--base]
  exit /b 1
)
if errorlevel 1 exit /b 1
pushd frontend
call npm ci
set "RESULT=%ERRORLEVEL%"
popd
if not "%RESULT%"=="0" exit /b %RESULT%
".venv\Scripts\python.exe" scripts\start.py --check
if errorlevel 1 exit /b 1
echo Installazione completata. Avvia scripts\start-windows.bat.
