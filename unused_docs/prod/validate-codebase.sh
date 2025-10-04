#!/bin/bash
# Codebase Validation Script for CI/CD Readiness

echo "🔍 Validating Codebase for CI/CD..."
echo "=================================="

# Check required files
echo "📁 Checking required files..."
required_files=(
    "Dockerfile"
    "requirements.txt" 
    "requirements.prod.txt"
    "main.py"
    "start.sh"
    ".gitignore"
    "deployment/ecs-api-task-definition.json"
    "deployment/ecs-worker-task-definition.json"
    "aws/ci-cd-iam-policy.json"
)

all_present=true
for file in "${required_files[@]}"; do
    if [[ -f "$file" ]]; then
        echo "✅ $file"
    else
        echo "❌ $file - MISSING"
        all_present=false
    fi
done

# Check directory structure
echo ""
echo "📂 Checking directory structure..."
required_dirs=(
    "app"
    "app/api"
    "app/core"
    "app/services"
    "app/workers"
    "deployment"
    "aws"
)

for dir in "${required_dirs[@]}"; do
    if [[ -d "$dir" ]]; then
        echo "✅ $dir/"
    else
        echo "❌ $dir/ - MISSING"
        all_present=false
    fi
done

# Check for unwanted files
echo ""
echo "🧹 Checking for unwanted files..."
unwanted_patterns=(
    "*.tmp"
    "test_*"
    "*debug*"
    "*.backup"
    "build-*"
)

found_unwanted=false
for pattern in "${unwanted_patterns[@]}"; do
    if ls $pattern 1> /dev/null 2>&1; then
        echo "⚠️  Found unwanted files: $pattern"
        found_unwanted=true
    fi
done

if [ "$found_unwanted" = false ]; then
    echo "✅ No unwanted files found"
fi

# Check Python syntax
echo ""
echo "🐍 Checking Python syntax..."
if python3 -m py_compile main.py app/main.py 2>/dev/null; then
    echo "✅ Python syntax is valid"
else
    echo "❌ Python syntax errors found"
    all_present=false
fi

# Final result
echo ""
echo "=================================="
if [ "$all_present" = true ] && [ "$found_unwanted" = false ]; then
    echo "🎉 CODEBASE VALIDATION PASSED!"
    echo "✅ Ready for CI/CD pipeline setup"
    exit 0
else
    echo "❌ CODEBASE VALIDATION FAILED!"
    echo "⚠️  Please fix the issues above before proceeding"
    exit 1
fi
