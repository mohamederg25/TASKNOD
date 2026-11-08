@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    py -3 -m venv .venv
    if errorlevel 1 goto :error
)

echo Installing dependencies...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :error

echo Building TaskNudge.exe...
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean TaskNudge.spec
if errorlevel 1 goto :error

echo.
echo Built dist\TaskNudge.exe
echo Move the EXE to a permanent folder before enabling "Start with Windows".
pause
exit /b 0

:error
echo.
echo Build failed. Review the output above.
pause
exit /b 1
