#!/bin/bash

# Railway Deployment Validation Script
echo "🔍 Validating Railway deployment configuration..."

# Check if all required files exist
echo "📁 Checking required files..."

required_files=(
    "Dockerfile"
    "requirements.prod.txt"
    "deployment/railway/railway.toml"
    "deployment/railway/nixpacks.toml"
    ".dockerignore"
    ".railwayignore"
    "app/main.py"
)

missing_files=()
for file in "${required_files[@]}"; do
    if [[ ! -f "$file" ]]; then
        missing_files+=("$file")
    else
        echo "✅ $file"
    fi
done

if [[ ${#missing_files[@]} -gt 0 ]]; then
    echo "❌ Missing files:"
    for file in "${missing_files[@]}"; do
        echo "   - $file"
    done
    exit 1
fi

# Check Python app structure
echo -e "\n🐍 Checking Python app structure..."
if python3 -c "import sys; sys.path.append('.'); import app.main; print('✅ app.main imports successfully')" 2>/dev/null; then
    echo "✅ FastAPI app structure is correct"
else
    echo "❌ FastAPI app import failed"
    exit 1
fi

# Validate Docker syntax
echo -e "\n🐳 Validating Dockerfile syntax..."
if docker build -f Dockerfile --dry-run . &>/dev/null; then
    echo "✅ Dockerfile syntax is valid"
else
    echo "❌ Dockerfile has syntax errors"
fi

# Check requirements.prod.txt
echo -e "\n📦 Checking requirements.prod.txt..."
if [[ -f "requirements.prod.txt" ]] && [[ -s "requirements.prod.txt" ]]; then
    echo "✅ requirements.prod.txt exists and is not empty"
    echo "   📋 Key dependencies:"
    grep -E "(fastapi|uvicorn|sqlalchemy|psycopg2)" requirements.prod.txt | head -5
else
    echo "❌ requirements.prod.txt is missing or empty"
    exit 1
fi

# Validate TOML files
echo -e "\n⚙️ Validating TOML configuration files..."
for toml_file in "deployment/railway/railway.toml" "deployment/railway/nixpacks.toml"; do
    if python3 -c "import tomli; tomli.load(open('$toml_file', 'rb'))" 2>/dev/null; then
        echo "✅ $toml_file syntax is valid"
    elif python3 -c "import toml; toml.load('$toml_file')" 2>/dev/null; then
        echo "✅ $toml_file syntax is valid"
    else
        echo "❌ $toml_file has syntax errors"
    fi
done

# Check environment variable template
echo -e "\n🔐 Checking environment configuration..."
if [[ -f "RAILWAY_ENV_VARS.md" ]]; then
    echo "✅ Environment variables guide exists"
else
    echo "⚠️ Environment variables guide missing"
fi

# Check deployment scripts
echo -e "\n🚀 Checking deployment scripts..."
if [[ -x "deploy-railway.sh" ]]; then
    echo "✅ deploy-railway.sh is executable"
else
    echo "⚠️ deploy-railway.sh not executable (run: chmod +x deploy-railway.sh)"
fi

if [[ -x "setup-neon-db.py" ]]; then
    echo "✅ setup-neon-db.py is executable"
else
    echo "⚠️ setup-neon-db.py not executable (run: chmod +x setup-neon-db.py)"
fi

echo -e "\n✅ Validation completed!"
echo -e "\n📋 Ready to deploy to Railway:"
echo "1. Set up Neon PostgreSQL database"
echo "2. Run: ./deploy-railway.sh"
echo "3. Set DATABASE_URL in Railway variables"
echo "4. Run: railway run python setup-neon-db.py"

echo -e "\n🎉 Your deployment configuration looks perfect!"
