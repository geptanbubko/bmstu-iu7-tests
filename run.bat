@echo off
cd /d "%~dp0"
set PYTHONPATH=%~dp0src
py -3 -m wildlife_app
if errorlevel 1 pause
