@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0.."

python -m pip install -r backend\requirements.txt
if errorlevel 1 exit /b 1

python -m pip install -r desktop_native\requirements-build.txt
if errorlevel 1 exit /b 1

pyinstaller ^
  --name SafePromptGuard ^
  --onefile ^
  --windowed ^
  --paths backend ^
  --add-data "shared;shared" ^
  desktop_native\safeprompt_gui.py
if errorlevel 1 exit /b 1

echo GUI executable created under dist\
endlocal
