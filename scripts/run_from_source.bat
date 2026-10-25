@echo off
REM Runs Clip Cartel Agent from this source folder (after you edit the code).
REM Needs Python 3.11+ from python.org (tick "Add python.exe to PATH" when installing).
cd /d "%~dp0"
if not exist .venv (
  python -m venv .venv || (echo Python not found. Install it from https://www.python.org/downloads/ & pause & exit /b 1)
  .venv\Scripts\python -m pip install --upgrade pip
  .venv\Scripts\python -m pip install -r requirements.txt
)
start "" .venv\Scripts\pythonw.exe -m agent
