#!/bin/bash
# Railway CLI Setup and Log Monitoring Script
# This script helps you set up Railway CLI and monitor logs during performance testing

echo "🚂 RAILWAY CLI SETUP AND LOG MONITORING"
echo "========================================"

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install it first:"
    echo "   https://nodejs.org/"
    exit 1
fi

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo "❌ npm is not installed. Please install Node.js with npm:"
    echo "   https://nodejs.org/"
    exit 1
fi

echo "✅ Node.js and npm are installed"

# Install Railway CLI
echo "📦 Installing Railway CLI..."
npm install -g @railway/cli

if [ $? -ne 0 ]; then
    echo "❌ Failed to install Railway CLI"
    echo "💡 Try using sudo: sudo npm install -g @railway/cli"
    exit 1
fi

echo "✅ Railway CLI installed successfully"

# Check Railway CLI version
echo "🔍 Railway CLI version:"
railway --version

# Login to Railway
echo "🔑 Please login to Railway..."
railway login

if [ $? -ne 0 ]; then
    echo "❌ Railway login failed"
    exit 1
fi

echo "✅ Railway login successful"

# Show current user
echo "👤 Current Railway user:"
railway whoami

# Show project status
echo "📋 Railway project status:"
railway status

echo ""
echo "🎯 READY FOR LOG MONITORING!"
echo "Now you can:"
echo "1. Start log monitoring: railway logs --follow"
echo "2. Monitor specific service: railway logs --follow --service <service-name>"
echo "3. Get recent logs: railway logs --tail 100"
echo ""
echo "📊 To monitor during performance testing:"
echo "1. Open a new terminal"
echo "2. Run: railway logs --follow"
echo "3. In another terminal, run your performance test"
echo "4. Watch real-time logs for performance metrics"
