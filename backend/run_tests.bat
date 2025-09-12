@echo off
echo ============================================================
echo GEE Integration Test Runner
echo ============================================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or not in PATH
    echo Please install Python and try again
    pause
    exit /b 1
)

echo ✅ Python is available
echo.

REM Check if we're in the right directory
if not exist "test_gee_integration.py" (
    echo ❌ test_gee_integration.py not found
    echo Please run this script from the backend directory
    pause
    exit /b 1
)

echo ✅ Test files found
echo.

REM Run the integration tests
echo 🚀 Starting integration tests...
echo.
python run_integration_tests.py

echo.
echo ============================================================
echo Test execution completed
echo ============================================================
pause
