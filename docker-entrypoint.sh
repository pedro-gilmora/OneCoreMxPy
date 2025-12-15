#!/bin/bash
# =============================================================================
# OneCoreMxPy - Docker Entrypoint Script
# Handles startup tasks before running the main application
# =============================================================================

set -e

echo "============================================="
echo "  OneCoreMxPy - Container Startup"
echo "============================================="
echo ""

# Activate virtual environment (already in PATH, but explicit for scripts)
echo "🐍 Virtual environment: $VIRTUAL_ENV"
echo "   Python: $(python --version)"
echo "   Pip: $(pip --version)"

# Wait for dependent services if needed
if [ -n "$WAIT_FOR_LOCALSTACK" ] && [ "$WAIT_FOR_LOCALSTACK" = "true" ]; then
    echo ""
    echo "⏳ Waiting for LocalStack to be ready..."
    
    LOCALSTACK_URL="${S3_ENDPOINT_URL:-http://localstack:4566}/_localstack/health"
    MAX_RETRIES=30
    RETRY_COUNT=0
    
    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        if curl -sf "$LOCALSTACK_URL" > /dev/null 2>&1; then
            echo "✅ LocalStack is ready!"
            break
        fi
        RETRY_COUNT=$((RETRY_COUNT + 1))
        echo "   Waiting... ($RETRY_COUNT/$MAX_RETRIES)"
        sleep 2
    done
    
    if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
        echo "⚠️  LocalStack health check timed out, continuing anyway..."
    fi
fi

# Wait for database if configured
if [ -n "$WAIT_FOR_DB" ] && [ "$WAIT_FOR_DB" = "true" ]; then
    echo ""
    echo "⏳ Waiting for SQL Server to be ready..."
    
    MAX_RETRIES=30
    RETRY_COUNT=0
    DB_SERVER_HOST="${DB_SERVER:-sqlserver}"
    DB_USER_NAME="${DB_USER:-sa}"
    DB_USER_PASSWORD="${DB_PASSWORD}"
    DB_DATABASE="${DB_NAME:-OneCoreMxPy}"
    
    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        # Try to connect to SQL Server (master database first)
        if python -c "
import pyodbc
import sys
try:
    conn = pyodbc.connect(
        'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=$DB_SERVER_HOST;'
        'DATABASE=master;'
        'UID=$DB_USER_NAME;'
        'PWD=$DB_USER_PASSWORD;'
        'TrustServerCertificate=yes;'
        'Connection Timeout=5;',
        autocommit=True
    )
    conn.close()
    sys.exit(0)
except Exception as e:
    print(f'Connection error: {e}', file=sys.stderr)
    sys.exit(1)
" 2>/dev/null; then
            echo "✅ SQL Server is ready!"
            
            # Create database if it doesn't exist
            echo "📦 Ensuring database '$DB_DATABASE' exists..."
            python -c "
import pyodbc
conn = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server};'
    'SERVER=$DB_SERVER_HOST;'
    'DATABASE=master;'
    'UID=$DB_USER_NAME;'
    'PWD=$DB_USER_PASSWORD;'
    'TrustServerCertificate=yes;',
    autocommit=True
)
cursor = conn.cursor()
cursor.execute(\"\"\"
    IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = '$DB_DATABASE')
    BEGIN
        CREATE DATABASE [$DB_DATABASE]
    END
\"\"\")
conn.close()
print('✅ Database ready!')
"
            break
        fi
        RETRY_COUNT=$((RETRY_COUNT + 1))
        echo "   Waiting... ($RETRY_COUNT/$MAX_RETRIES)"
        sleep 3
    done
    
    if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
        echo "⚠️  SQL Server connection timed out, continuing anyway..."
    fi
fi

echo ""
echo "🚀 Starting application..."
echo "   URL: http://0.0.0.0:8000"
echo "   Swagger UI: http://localhost:8000/docs"
echo "============================================="
echo ""

# Execute the main command
exec "$@"
