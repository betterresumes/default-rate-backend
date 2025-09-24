#!/usr/bin/env python3

import os
import sys
import uvicorn
from dotenv import load_dotenv

load_dotenv()

def main():
    """Start the application server."""
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    environment = os.getenv("ENVIRONMENT", "development").lower()
    
    try:
        from app.main import app
    except ImportError as e:
        print(f"Error importing application: {e}")
        sys.exit(1)
    
    if environment == "production":
        uvicorn.run(
            "app.main:app",
            host=host,
            port=port,
            workers=int(os.getenv("WORKERS", "4")),
            log_level=os.getenv("LOG_LEVEL", "warning").lower(),
            access_log=True,
            use_colors=False,
            server_header=False,
        )
    else:
        uvicorn.run(
            "app.main:app",
            host=host,
            port=port,
            reload=True,
            log_level="info",
            access_log=True,
            use_colors=True,
        )


if __name__ == "__main__":
    main()
    debug = os.getenv("DEBUG", "false").lower() == "true"
    workers = int(os.getenv("WORKERS", "1"))
    
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
    
    uvicorn.run(**config)


if __name__ == "__main__":
    main()
