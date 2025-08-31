@echo off
REM GEE Templates Testing Suite - Windows Batch Runner
REM This script makes it easy to run GEE template tests on Windows

echo.
echo ========================================
echo   GEE Templates Testing Suite
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python and try again
    pause
    exit /b 1
)

echo Python found! Starting tests...
echo.

REM Change to the testing directory
cd /d "%~dp0"

echo Current directory: %CD%
echo.

REM Show menu
echo Choose an option:
echo 1. Run all tests
echo 2. List available templates
echo 3. Test specific template
echo 4. Exit
echo.

set /p choice="Enter your choice (1-4): "

if "%choice%"=="1" (
    echo.
    echo Running full test suite...
    python test_all_gee_templates.py
) else if "%choice%"=="2" (
    echo.
    echo Listing available templates...
    python run_gee_tests.py --list
) else if "%choice%"=="3" (
    echo.
    set /p template="Enter template name (e.g., climate_analysis): "
    echo.
    echo Testing template: %template%
    python run_gee_tests.py --template %template%
) else if "%choice%"=="4" (
    echo Exiting...
    exit /b 0
) else (
    echo Invalid choice. Please run the script again.
)

echo.
echo Tests completed!
pause
