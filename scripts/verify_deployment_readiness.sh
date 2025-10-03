#!/bin/bash

# 🚀 Pre-Deployment Verification Script for AccuNode
# Verifies all components are ready for production deployment

echo "🔍 AccuNode Deployment Readiness Verification"
echo "============================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASS=0
FAIL=0

check_pass() {
    echo -e "${GREEN}✅ PASS${NC}: $1"
    ((PASS++))
}

check_fail() {
    echo -e "${RED}❌ FAIL${NC}: $1"
    ((FAIL++))
}

check_warn() {
    echo -e "${YELLOW}⚠️ WARN${NC}: $1"
}

echo "📦 1. DEPENDENCY VERIFICATION"
echo "=============================="

# Check critical dependencies
DEPS=("fastapi" "slowapi" "redis" "boto3" "celery" "uvicorn" "psycopg2-binary" "sqlalchemy")
for dep in "${DEPS[@]}"; do
    if grep -q "$dep" requirements.prod.txt; then
        check_pass "Dependency $dep found in requirements.prod.txt"
    else
        check_fail "Dependency $dep MISSING from requirements.prod.txt"
    fi
done

echo ""
echo "🏗️ 2. APPLICATION STRUCTURE VERIFICATION"
echo "========================================"

# Check critical files exist
CRITICAL_FILES=(
    "app/main.py"
    "app/middleware/rate_limiting.py"
    "app/middleware/security_headers.py"
    "app/core/database.py"
    "Dockerfile"
    ".github/workflows/ci-cd.yml"
    "requirements.prod.txt"
)

for file in "${CRITICAL_FILES[@]}"; do
    if [ -f "$file" ]; then
        check_pass "Critical file exists: $file"
    else
        check_fail "Critical file MISSING: $file"
    fi
done

echo ""
echo "🔧 3. CONFIGURATION VERIFICATION"
echo "================================"

# Check main.py configuration
if grep -q "setup_rate_limiting" app/main.py; then
    check_pass "Rate limiting middleware configured in main.py"
else
    check_fail "Rate limiting middleware NOT configured in main.py"
fi

if grep -q "setup_security_headers" app/main.py; then
    check_pass "Security headers middleware configured in main.py"
else
    check_fail "Security headers middleware NOT configured in main.py"
fi

# Check rate limiting decorators
RATE_LIMIT_COUNT=$(grep -r "@rate_limit_" app/api/v1/ --include="*.py" | wc -l)
if [ "$RATE_LIMIT_COUNT" -gt 50 ]; then
    check_pass "Rate limiting decorators applied to $RATE_LIMIT_COUNT endpoints"
else
    check_fail "Insufficient rate limiting coverage: only $RATE_LIMIT_COUNT endpoints"
fi

echo ""
echo "🔐 4. SECURITY VERIFICATION"
echo "=========================="

# Check security headers implementation
SECURITY_HEADERS=("X-Frame-Options" "X-Content-Type-Options" "X-XSS-Protection" "Strict-Transport-Security" "Content-Security-Policy")
for header in "${SECURITY_HEADERS[@]}"; do
    if grep -q "$header" app/middleware/security_headers.py; then
        check_pass "Security header implemented: $header"
    else
        check_fail "Security header MISSING: $header"
    fi
done

echo ""
echo "🏭 5. DOCKER & CI/CD VERIFICATION"
echo "================================="

# Check Dockerfile
if grep -q "requirements.prod.txt" Dockerfile; then
    check_pass "Dockerfile uses production requirements"
else
    check_fail "Dockerfile does NOT use production requirements"
fi

# Check CI/CD pipeline
if grep -q "requirements.prod.txt" .github/workflows/ci-cd.yml; then
    check_pass "CI/CD pipeline uses production requirements"
else
    check_fail "CI/CD pipeline does NOT use production requirements"
fi

if grep -q "bandit" .github/workflows/ci-cd.yml; then
    check_pass "CI/CD pipeline includes security scanning"
else
    check_fail "CI/CD pipeline does NOT include security scanning"
fi

echo ""
echo "☁️ 6. AWS INFRASTRUCTURE VERIFICATION"
echo "===================================="

# Check ECS services (requires AWS CLI)
if command -v aws &> /dev/null; then
    # Check ECS cluster
    CLUSTER_STATUS=$(aws ecs describe-clusters --clusters AccuNode-Production --query 'clusters[0].status' --output text 2>/dev/null || echo "ERROR")
    if [ "$CLUSTER_STATUS" = "ACTIVE" ]; then
        check_pass "ECS Cluster AccuNode-Production is ACTIVE"
    else
        check_fail "ECS Cluster AccuNode-Production is not active (Status: $CLUSTER_STATUS)"
    fi
    
    # Check API service
    API_SERVICE_STATUS=$(aws ecs describe-services --cluster AccuNode-Production --services accunode-api-service --query 'services[0].status' --output text 2>/dev/null || echo "ERROR")
    if [ "$API_SERVICE_STATUS" = "ACTIVE" ]; then
        check_pass "ECS API Service is ACTIVE"
    else
        check_fail "ECS API Service is not active (Status: $API_SERVICE_STATUS)"
    fi
    
    # Check RDS database
    DB_STATUS=$(aws rds describe-db-instances --db-instance-identifier accunode-postgres --query 'DBInstances[0].DBInstanceStatus' --output text 2>/dev/null || echo "ERROR")
    if [ "$DB_STATUS" = "available" ]; then
        check_pass "RDS Database is available"
    else
        check_fail "RDS Database is not available (Status: $DB_STATUS)"
    fi
    
    # Check ElastiCache Redis
    REDIS_STATUS=$(aws elasticache describe-cache-clusters --cache-cluster-id accunode-redis --query 'CacheClusters[0].CacheClusterStatus' --output text 2>/dev/null || echo "ERROR")
    if [ "$REDIS_STATUS" = "available" ]; then
        check_pass "ElastiCache Redis is available"
    else
        check_fail "ElastiCache Redis is not available (Status: $REDIS_STATUS)"
    fi
else
    check_warn "AWS CLI not available - skipping infrastructure checks"
fi

echo ""
echo "🎯 7. FINAL DEPLOYMENT READINESS"
echo "================================"

# Calculate readiness score
TOTAL=$((PASS + FAIL))
if [ "$TOTAL" -gt 0 ]; then
    SCORE=$(( (PASS * 100) / TOTAL ))
else
    SCORE=0
fi

echo "📊 DEPLOYMENT READINESS SCORE: $SCORE%"
echo "   ✅ Passed: $PASS checks"
echo "   ❌ Failed: $FAIL checks"
echo ""

if [ "$SCORE" -ge 90 ]; then
    echo -e "${GREEN}🚀 DEPLOYMENT APPROVED${NC}"
    echo "   Status: Ready for production deployment"
    echo "   Confidence: High"
elif [ "$SCORE" -ge 80 ]; then
    echo -e "${YELLOW}⚠️ DEPLOYMENT WITH CAUTION${NC}"
    echo "   Status: Minor issues detected"
    echo "   Confidence: Medium - Address failures before deployment"
else
    echo -e "${RED}🛑 DEPLOYMENT NOT RECOMMENDED${NC}"
    echo "   Status: Critical issues detected"
    echo "   Confidence: Low - Fix failures before deployment"
fi

echo ""
echo "📋 Next Steps:"
if [ "$FAIL" -eq 0 ]; then
    echo "   ✅ All checks passed - proceed with deployment"
    echo "   🚀 Run: git push origin prod (to trigger CI/CD)"
else
    echo "   🔧 Fix the $FAIL failed check(s) above"
    echo "   🔄 Re-run this verification script"
    echo "   ✅ Deploy only after all checks pass"
fi

echo ""
echo "🔗 Resources:"
echo "   📖 Full audit: docs/DEPLOYMENT_READINESS_AUDIT.md"
echo "   🔒 Security report: docs/SECURITY_FIXES_COMPLETE.md"
echo "   📊 Infrastructure: AWS ECS Console"
echo ""

# Exit with appropriate code
if [ "$FAIL" -eq 0 ]; then
    exit 0
else
    exit 1
fi
