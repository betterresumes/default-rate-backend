#!/usr/bin/env python3
"""
Startup script for Railway deployment
This handles the path issues and starts the FastAPI app
"""

import sys
import os

# Add src directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')
sys.path.insert(0, src_dir)

# Change to src directory and run the app
os.chdir(src_dir)

# Import and run the FastAPI app
if __name__ == "__main__":
    import app
    # The app.py file will handle the rest
