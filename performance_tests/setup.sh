#!/bin/bash

# Setup script for Authentication API Performance Testing

echo "Setting up Authentication API Performance Testing Environment..."

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed or not in PATH"
    exit 1
fi

# Check if pip is available
if ! command -v pip3 &> /dev/null; then
    echo "Error: pip3 is not installed or not in PATH"
    exit 1
fi

echo "✓ Python 3 and pip3 are available"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install requirements
echo "Installing performance testing requirements..."
pip install -r requirements.txt

if [ $? -eq 0 ]; then
    echo "✓ Requirements installed successfully"
else
    echo "✗ Failed to install requirements"
    exit 1
fi

# Make test runner executable
chmod +x run_auth_tests.py

# Create reports directory if it doesn't exist
mkdir -p reports/auth_apis

echo ""
echo "Setup completed successfully!"
echo ""
echo "Usage Examples:"
echo "  # Basic sequential tests"
echo "  python3 run_auth_tests.py --test-type basic"
echo ""
echo "  # Concurrent load test with 20 users"
echo "  python3 run_auth_tests.py --test-type concurrent --users 20"
echo ""
echo "  # Stress test ramping up to 50 users"
echo "  python3 run_auth_tests.py --test-type stress --max-users 50"
echo ""
echo "  # Full test suite"
echo "  python3 run_auth_tests.py --test-type full"
echo ""
echo "  # Test against different API URL"
echo "  python3 run_auth_tests.py --test-type basic --url http://your-api-server:8000"
echo ""
echo "Make sure your API server is running before starting tests!"
echo "Default API URL: http://localhost:8000"
