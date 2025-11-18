@echo off

REM Define paths as variables
set "PYTHON_PATH=C:\Users\USERNAME\AppData\Local\Programs\Python\Python311\python.exe"
set "SCRIPT_PATH=C:\Users\auto_pokemon_tcgp\auto_pokemon_tcgp.py"

REM Check if Python executable exists
if not exist "%PYTHON_PATH%" (
    echo Error: Python executable not found at %PYTHON_PATH%
    pause
    exit /b 1
)

REM Check if script file exists
if not exist "%SCRIPT_PATH%" (
    echo Error: Script file not found at %SCRIPT_PATH%
    pause
    exit /b 1
)

REM Execute the Python script
"%PYTHON_PATH%" "%SCRIPT_PATH%"

REM Pause Command Prompt to view output
pause