# =============================================================================
# OneCoreMxPy - Stop Script
# Stops LocalStack Docker containers
# =============================================================================

param(
    [switch]$RemoveVolumes    # Also remove volumes (clears all data)
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  OneCoreMxPy - Stop Containers" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

# Change to project root directory
Set-Location $ProjectRoot

Write-Host "🛑 Stopping Docker containers..." -ForegroundColor Yellow

if ($RemoveVolumes) {
    Write-Host "   (Also removing volumes)" -ForegroundColor Gray
    docker-compose down -v
}
else {
    docker-compose down
}

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Containers stopped successfully." -ForegroundColor Green
}
else {
    Write-Host "❌ Error stopping containers." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
