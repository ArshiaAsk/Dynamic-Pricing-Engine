#!/bin/bash
# Run smoke tests against deployed API

set -e

# Configuration
API_URL="${API_URL:-http://localhost:8000}"
MAX_RETRIES=30
RETRY_DELAY=2

echo "=================================================="
echo "  Smoke Test Runner"
echo "=================================================="
echo "API URL: $API_URL"
echo ""

# Wait for API to be ready
echo "⏳ Waiting for API to be ready..."
for i in $(seq 1 $MAX_RETRIES); do
    if curl -sf "$API_URL/v1/health/ready" > /dev/null 2>&1; then
        echo "✅ API is ready"
        break
    fi
    
    if [ $i -eq $MAX_RETRIES ]; then
        echo "❌ API not ready after $MAX_RETRIES attempts"
        exit 1
    fi
    
    echo "   Attempt $i/$MAX_RETRIES - waiting ${RETRY_DELAY}s..."
    sleep $RETRY_DELAY
done

echo ""
echo "🚀 Running smoke tests..."
echo ""

# Run smoke tests
python3 tests/smoke_tests.py

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "✅ All smoke tests passed!"
    exit 0
else
    echo ""
    echo "❌ Smoke tests failed!"
    exit 1
fi
