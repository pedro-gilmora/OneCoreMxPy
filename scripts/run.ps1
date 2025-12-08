# =============================================================================
# OneCoreMxPy - Run Script
# Starts LocalStack Docker container and the FastAPI web API
# =============================================================================

param(
    [switch]$SkipDocker,      # Skip starting Docker containers
    [switch]$Detached,        # Run containers in detached mode (default)
    [int]$WaitTimeout = 30    # Seconds to wait for LocalStack to be ready
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  OneCoreMxPy - Application Launcher" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

# Change to project root directory
Set-Location $ProjectRoot
Write-Host "📂 Working directory: $ProjectRoot" -ForegroundColor Gray

# -----------------------------------------------------------------------------
# Step 1: Start LocalStack Docker Container
# -----------------------------------------------------------------------------
if (-not $SkipDocker) {
    Write-Host ""
    Write-Host "🐳 Starting LocalStack Docker container..." -ForegroundColor Yellow
    
    # Check if Docker is running
    try {
        $dockerInfo = docker info 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Host "❌ Docker is not running. Please start Docker Desktop first." -ForegroundColor Red
            exit 1
        }
    }
    catch {
        Write-Host "❌ Docker is not installed or not in PATH." -ForegroundColor Red
        exit 1
    }
    
    # Start containers with docker-compose
    Write-Host "   Running docker-compose up -d..." -ForegroundColor Gray
    docker-compose up -d
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Failed to start Docker containers." -ForegroundColor Red
        exit 1
    }
    
    Write-Host "✅ Docker containers started." -ForegroundColor Green
    
    # Wait for LocalStack to be ready
    Write-Host ""
    Write-Host "⏳ Waiting for LocalStack to be ready..." -ForegroundColor Yellow
    
    $localstackUrl = "http://localhost:4566/_localstack/health"
    $startTime = Get-Date
    $ready = $false
    
    while (-not $ready -and ((Get-Date) - $startTime).TotalSeconds -lt $WaitTimeout) {
        try {
            $response = Invoke-RestMethod -Uri $localstackUrl -Method Get -TimeoutSec 2 -ErrorAction SilentlyContinue
            if ($response.services.s3 -eq "running" -or $response.services.s3 -eq "available") {
                $ready = $true
            }
        }
        catch {
            Start-Sleep -Seconds 1
            Write-Host "." -NoNewline -ForegroundColor Gray
        }
    }
    
    Write-Host ""
    
    if ($ready) {
        Write-Host "✅ LocalStack is ready! S3 service is running." -ForegroundColor Green
    }
    else {
        Write-Host "⚠️  LocalStack health check timed out, but continuing anyway..." -ForegroundColor Yellow
    }
}
else {
    Write-Host ""
    Write-Host "⏭️  Skipping Docker startup (--SkipDocker flag)" -ForegroundColor Yellow
}

# -----------------------------------------------------------------------------
# Step 2: Activate Virtual Environment (if exists)
# -----------------------------------------------------------------------------
Write-Host ""
Write-Host "🐍 Checking Python virtual environment..." -ForegroundColor Yellow

$venvPath = Join-Path $ProjectRoot "venv\Scripts\Activate.ps1"
if (Test-Path $venvPath) {
    Write-Host "   Activating virtual environment..." -ForegroundColor Gray
    & $venvPath
    Write-Host "✅ Virtual environment activated." -ForegroundColor Green
}
else {
    Write-Host "⚠️  No virtual environment found at $venvPath" -ForegroundColor Yellow
    Write-Host "   Using system Python installation." -ForegroundColor Gray
}

# -----------------------------------------------------------------------------
# Step 3: Start FastAPI Application
# -----------------------------------------------------------------------------
Write-Host ""
Write-Host "🚀 Starting FastAPI application..." -ForegroundColor Yellow
Write-Host "   URL: http://localhost:8000" -ForegroundColor Cyan
Write-Host "   Swagger UI: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "   ReDoc: http://localhost:8000/redoc" -ForegroundColor Cyan
Write-Host ""
Write-Host "   Press Ctrl+C to stop the application" -ForegroundColor Gray
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

# Run uvicorn
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
