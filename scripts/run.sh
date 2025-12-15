#!/bin/bash
# =============================================================================
# OneCoreMxPy - Run Script (Linux/Container)
# Starts the FastAPI web API inside Docker container
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "============================================="
echo "  OneCoreMxPy - Application Launcher"
echo "============================================="
echo ""

cd "$PROJECT_ROOT"
echo "📂 Working directory: $PROJECT_ROOT"

# -----------------------------------------------------------------------------
# Check Virtual Environment
# -----------------------------------------------------------------------------
echo ""
echo "🐍 Checking Python virtual environment..."

if [ -n "$VIRTUAL_ENV" ]; then
    echo "✅ Virtual environment active: $VIRTUAL_ENV"
elif [ -d "$PROJECT_ROOT/venv" ]; then
    echo "   Activating virtual environment..."
    source "$PROJECT_ROOT/venv/bin/activate"
    echo "✅ Virtual environment activated."
else
    echo "⚠️  No virtual environment found."
    echo "   Using system Python installation."
fi

echo "   Python: $(python --version)"

# -----------------------------------------------------------------------------
# Start FastAPI Application
# -----------------------------------------------------------------------------
echo ""
echo "🚀 Starting FastAPI application..."
echo "   URL: http://0.0.0.0:8000"
echo "   Swagger UI: http://localhost:8000/docs"
echo "   ReDoc: http://localhost:8000/redoc"
echo ""
echo "   Press Ctrl+C to stop the application"
echo "============================================="
echo ""

# Run uvicorn
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 "$@"
