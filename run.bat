@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\pythonw.exe" (
    echo First run: setting up Recipe Randomiser. This takes a minute...
    py -3 -m venv .venv 2>nul || python -m venv .venv
    if errorlevel 1 goto nopython
    ".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q -r requirements.txt
    if errorlevel 1 goto failed
)

start "" ".venv\Scripts\pythonw.exe" "src\main.py"
exit /b 0

:nopython
echo.
echo Python wasn't found. Install it from https://www.python.org/downloads/
echo and tick "Add python.exe to PATH" during setup, then run this again.
pause
exit /b 1

:failed
echo.
echo Installing CustomTkinter failed. Check the messages above, then run this again.
rmdir /s /q .venv
pause
exit /b 1
