@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Создаю окружение и устанавливаю компоненты...
    py -3 -m venv .venv
    ".venv\Scripts\python.exe" -m pip install --upgrade pip
)
".venv\Scripts\python.exe" -m pip install --force-reinstall *.whl
".venv\Scripts\python.exe" -m wildlife_app --ui gui --config "%~dp0config.ini"
if errorlevel 1 pause
