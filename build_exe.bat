@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    py -3 -m venv .venv 2>nul || python -m venv .venv
    if errorlevel 1 goto nopython
)

echo Installing the build tools...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q -r requirements.txt pyinstaller pillow
if errorlevel 1 goto failed

echo Building Recipe Randomiser.exe...
".venv\Scripts\pyinstaller.exe" --noconfirm --clean --windowed --name "Recipe Randomiser" --icon "src\assets\icon.png" --add-data "src\assets;assets" --collect-data customtkinter "src\main.py"
if errorlevel 1 goto failed

echo.
echo Done! Your app is in:  dist\Recipe Randomiser\Recipe Randomiser.exe
echo Copy the whole "dist\Recipe Randomiser" folder anywhere you like.
pause
exit /b 0

:nopython
echo.
echo Python wasn't found. Install it from https://www.python.org/downloads/
echo and tick "Add python.exe to PATH" during setup, then run this again.
pause
exit /b 1

:failed
echo.
echo The build failed. Check the messages above.
pause
exit /b 1
