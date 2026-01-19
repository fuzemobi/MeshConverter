@echo off
REM Setup script for MeshConverter_v2 (Windows)

echo ==================================
echo MeshConverter_v2 Setup
echo ==================================
echo.

REM Check Python version
echo Checking Python version...
python --version
if errorlevel 1 (
    echo Error: Python not found. Please install Python 3.8 or higher.
    pause
    exit /b 1
)
echo.

REM Create virtual environment
echo Creating virtual environment...
if exist venv (
    echo Warning: Virtual environment already exists
    choice /C YN /M "Remove and recreate"
    if errorlevel 2 (
        echo Using existing virtual environment
    ) else (
        rmdir /s /q venv
        python -m venv venv
        echo Created new virtual environment
    )
) else (
    python -m venv venv
    echo Created virtual environment
)
echo.

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat
echo Virtual environment activated
echo.

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip >nul 2>&1
echo pip upgraded
echo.

REM Install dependencies
echo Installing dependencies...
echo This may take a few minutes...
pip install -r requirements.txt
echo Dependencies installed
echo.

REM Run tests
echo Running tests...
python test_converter.py

if %errorlevel% equ 0 (
    echo.
    echo ==================================
    echo Setup Complete!
    echo ==================================
    echo.
    echo To get started:
    echo   1. Activate the virtual environment:
    echo      venv\Scripts\activate.bat
    echo.
    echo   2. Convert a mesh:
    echo      python mesh_to_cad_converter.py your_file.stl
    echo.
    echo   3. Batch convert:
    echo      python batch_convert.py input_folder\ -o output\
    echo.
    echo   4. Visualize results:
    echo      python visualize_results.py original.stl simplified.stl
    echo.
) else (
    echo.
    echo ==================================
    echo Setup Failed
    echo ==================================
    echo.
    echo Some tests failed. Please check the output above.
    echo You may need to install additional system dependencies.
    echo.
)

pause
