#!/bin/bash
set -e

# ==============================================================================
# End-to-End Production Smoke Test Suite
# ==============================================================================

BASE_URL="${1:-http://localhost}"

echo "=================================================="
echo "🧪 Running End-to-End Smoke Tests on $BASE_URL"
echo "=================================================="

FAILED=0

# Helper test function
test_endpoint() {
    local name="$1"
    local path="$2"
    local expected_code="$3"
    local url="${BASE_URL}${path}"

    printf "%-40s " "Testing $name..."

    HTTP_CODE="000"

    # 1. Native curl if present
    if command -v curl >/dev/null 2>&1; then
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$url" || echo "000")
    # 2. Native python3 if present
    elif command -v python3 >/dev/null 2>&1; then
        HTTP_CODE=$(python3 -c "
import urllib.request
try:
    req = urllib.request.Request('$url')
    with urllib.request.urlopen(req, timeout=5) as r:
        print(r.status)
except urllib.error.HTTPError as e:
    print(e.code)
except Exception:
    print('000')
" 2>/dev/null || echo "000")
    # 3. Docker container python fallback (always available in our production environment)
    elif docker ps | grep -q "self_study_backend_prod"; then
        # Inside docker network, query nginx container
        CONTAINER_URL="http://nginx${path}"
        HTTP_CODE=$(docker exec self_study_backend_prod python -c "
import urllib.request
try:
    req = urllib.request.Request('$CONTAINER_URL')
    with urllib.request.urlopen(req, timeout=5) as r:
        print(r.status)
except urllib.error.HTTPError as e:
    print(e.code)
except Exception:
    print('000')
" 2>/dev/null || echo "000")
    fi

    if [ "$HTTP_CODE" = "$expected_code" ]; then
        echo "✅ PASS (HTTP $HTTP_CODE)"
    else
        echo "❌ FAIL (Expected $expected_code, Got '$HTTP_CODE')"
        FAILED=$((FAILED + 1))
    fi
}

# 1. Nginx Gateway
test_endpoint "Nginx Gateway Health" "/health-nginx" "200"

# 2. Backend Liveness
test_endpoint "Backend Liveness Probe" "/health/live" "200"

# 3. Backend Readiness (DB & pgvector)
test_endpoint "Backend Readiness Probe" "/health/ready" "200"

# 4. Backend Skills API
test_endpoint "Backend Skills REST API" "/api/v1/skills" "200"

# 5. Frontend Next.js SSR
test_endpoint "Frontend Application Root" "/" "200"

echo "=================================================="
if [ $FAILED -eq 0 ]; then
    echo "🎉 ALL END-TO-END SMOKE TESTS PASSED!"
    echo "=================================================="
    exit 0
else
    echo "❌ $FAILED TEST(S) FAILED!"
    echo "=================================================="
    exit 1
fi
