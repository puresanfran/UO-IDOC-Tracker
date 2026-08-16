@echo off
echo ================================================
echo  UO Second Age - Housing Placement Analyzer
echo ================================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.10+ from python.org
    pause
    exit /b 1
)

:: Install dependencies
echo Installing dependencies...
pip install numpy Pillow -q
echo Done.
echo.

:: Create output folder
if not exist "E:\Ultima House Mapping\output" (
    mkdir "E:\Ultima House Mapping\output"
    echo Created E:\Ultima House Mapping\output
)

echo Choose what to run:
echo   1) Analyze small houses only (fastest, ~5 min)
echo   2) Analyze ALL house sizes   (~30 min)
echo   3) Open viewer only          (needs analysis done first)
echo.
set /p choice="Enter 1, 2, or 3: "

if "%choice%"=="1" (
    echo.
    echo Running analysis for small houses...
    python "%~dp01_analyze.py" --house small
    echo.
    echo Analysis complete! Opening viewer...
    python "%~dp02_viewer.py"
)

if "%choice%"=="2" (
    echo.
    echo Running full analysis (all house sizes)...
    python "%~dp01_analyze.py" --all
    echo.
    echo Analysis complete! Opening viewer...
    python "%~dp02_viewer.py"
)

if "%choice%"=="3" (
    echo.
    python "%~dp02_viewer.py"
)

pause
