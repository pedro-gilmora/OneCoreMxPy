@echo off
REM =============================================================================
REM OneCoreMxPy - Run Script (Batch)
REM Starts LocalStack Docker container and the FastAPI web API
REM =============================================================================

setlocal enabledelayedexpansion

echo =============================================
echo   OneCoreMxPy - Application Launcher
echo =============================================
echo.

cd /d "%~dp0.."
echo Working directory: %CD%

REM -----------------------------------------------------------------------------
REM Step 1: Start LocalStack Docker Container
REM -----------------------------------------------------------------------------
echo.
echo Starting LocalStack Docker container...

REM Check if Docker is running
docker info >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Docker is not running. Please start Docker Desktop first.
    exit /b 1
)

REM Start containers with docker-compose
echo Running docker-compose up -d...
docker-compose up -d
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to start Docker containers.
    exit /b 1
)
echo Docker containers started successfully.

REM Wait a few seconds for LocalStack to initialize
echo.
echo Waiting for LocalStack to be ready...
timeout /t 5 /nobreak >nul
echo LocalStack should be ready now.

REM -----------------------------------------------------------------------------
REM Step 2: Activate Virtual Environment (if exists)
REM -----------------------------------------------------------------------------
echo.
echo Checking Python virtual environment...

if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
    echo Virtual environment activated.
) else (
    echo WARNING: No virtual environment found. Using system Python.
)

REM -----------------------------------------------------------------------------
REM Step 3: Start FastAPI Application
REM -----------------------------------------------------------------------------
echo.
echo Starting FastAPI application...
echo    URL: http://localhost:8000
echo    Swagger UI: http://localhost:8000/docs
echo    ReDoc: http://localhost:8000/redoc
echo.
echo    Press Ctrl+C to stop the application
echo =============================================
echo.

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
