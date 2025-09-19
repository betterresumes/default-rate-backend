#!/usr/bin/env python3
"""
Application startup script for development and production.
"""

import os
import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the FastAPI app for direct uvicorn access
from app.main import app

def main():
    """Start the application server."""
    # Get configuration from environment
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    workers = int(os.getenv("WORKERS", "1"))
    
    # Configure uvicorn
    config = {
        "app": "app.main:app",
        "host": host,
        "port": port,
        "reload": debug,
        "log_level": "info" if not debug else "debug",
        "access_log": True,
    }
    
    if not debug and workers > 1:
        config["workers"] = workers
    
    print(f"🚀 Starting Financial Risk API on {host}:{port}")
    print(f"📊 Debug mode: {debug}")
    print(f"👥 Workers: {workers if not debug else '1 (reload mode)'}")
    print(f"📖 Documentation: http://{host}:{port}/docs")
    
    # Start server
    uvicorn.run(**config)


if __name__ == "__main__":
    main()
