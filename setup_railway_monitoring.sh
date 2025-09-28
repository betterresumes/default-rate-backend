#!/bin/bash

echo "🚂 RAILWAY CLI SETUP & LOG MONITORING GUIDE"
echo "=============================================="

# Check if Railway CLI is already installed
if command -v railway &> /dev/null; then
    echo "✅ Railway CLI is already installed"
    railway --version
else
    echo "📦 Installing Railway CLI..."
    
    # Check if npm is available
    if command -v npm &> /dev/null; then
        echo "Installing via npm..."
        npm install -g @railway/cli
    elif command -v brew &> /dev/null; then
        echo "Installing via Homebrew..."
        brew install railway
    else
        echo "❌ Please install Node.js (for npm) or Homebrew first"
        echo "   Node.js: https://nodejs.org/"
        echo "   Homebrew: https://brew.sh/"
        exit 1
    fi
fi

echo ""
echo "🔑 RAILWAY LOGIN"
echo "==============="
echo "Please login to Railway (this will open your browser):"
railway login

echo ""
echo "📊 TESTING RAILWAY CONNECTION"
echo "============================="
echo "Current Railway user:"
railway whoami

echo ""
echo "📋 PROJECT STATUS"
echo "================="
railway status

echo ""
echo "🎯 READY FOR PERFORMANCE MONITORING!"
echo "===================================="
echo ""
echo "To monitor logs during testing:"
echo "1. Open a new terminal"
echo "2. Run: railway logs --follow"
echo "3. In another terminal, run your performance test"
echo "4. Watch real-time logs for performance metrics"
echo ""
echo "Key commands:"
echo "  railway logs --follow          # Real-time logs"
echo "  railway logs --tail 100        # Recent logs"
echo "  railway logs --since 1h        # Last hour logs"
echo ""
echo "Look for these performance indicators:"
echo "✅ Good: 'Batch completed: 500 rows in 15s (33 rows/sec)'"
echo "❌ Bad:  'Processing row 45/1000 (4.5s per row)'"
