#!/bin/bash
# =============================================================================
# OneCoreMxPy - Database Initialization Script (Linux/Container)
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "============================================="
echo "  OneCoreMxPy - Database Initialization"
echo "============================================="
echo ""

cd "$PROJECT_ROOT"

# Check virtual environment
if [ -n "$VIRTUAL_ENV" ]; then
    echo "✅ Virtual environment active: $VIRTUAL_ENV"
elif [ -d "$PROJECT_ROOT/venv" ]; then
    source "$PROJECT_ROOT/venv/bin/activate"
    echo "✅ Virtual environment activated."
fi

echo ""
echo "📦 Initializing database..."

python -c "
from app.core.database import init_db
print('Creating database tables...')
init_db()
print('✅ Database initialized successfully!')
"

echo ""
echo "============================================="
