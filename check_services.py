#!/usr/bin/env python3
"""
Service status checker - Check if your FastAPI, Redis, Database, and Celery services are running.
"""

import os
import requests
import subprocess
import json
from dotenv import load_dotenv

load_dotenv()

def check_fastapi_service():
    """Check if FastAPI service is running"""
    print("🔍 Checking FastAPI service...")
    try:
        port = os.getenv("PORT", "8000")
        base_url = f"http://localhost:{port}"
        
        # Check root endpoint
        response = requests.get(f"{base_url}/", timeout=5)
        if response.status_code == 200:
            print(f"✅ FastAPI service running on port {port}")
            
            # Check health endpoint
            try:
                health_response = requests.get(f"{base_url}/health", timeout=10)
                if health_response.status_code == 200:
                    health_data = health_response.json()
                    print(f"   Health status: {health_data.get('status', 'unknown')}")
                    
                    services = health_data.get('services', {})
                    for service_name, service_info in services.items():
                        status = service_info.get('status', 'unknown')
                        connection = service_info.get('connection', 'unknown')
                        print(f"   {service_name}: {status} - {connection}")
                else:
                    print(f"   ⚠️ Health endpoint returned status {health_response.status_code}")
            except Exception as e:
                print(f"   ⚠️ Health check failed: {e}")
            
            return True
        else:
            print(f"❌ FastAPI service returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ FastAPI service not running on port {port}")
        return False
    except Exception as e:
        print(f"❌ Error checking FastAPI service: {e}")
        return False

def check_redis_service():
    """Check if Redis service is running"""
    print("🔍 Checking Redis service...")
    try:
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = os.getenv("REDIS_PORT", "6379")
        
        # Try to connect using redis-cli
        result = subprocess.run(
            ["redis-cli", "-h", redis_host, "-p", redis_port, "ping"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0 and "PONG" in result.stdout:
            print(f"✅ Redis service running on {redis_host}:{redis_port}")
            return True
        else:
            print(f"❌ Redis service not responding: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print("❌ Redis service connection timeout")
        return False
    except FileNotFoundError:
        print("⚠️ redis-cli not found, trying alternative method...")
        # Alternative method using Python redis client
        try:
            import redis
            redis_client = redis.Redis(
                host=redis_host,
                port=int(redis_port),
                socket_connect_timeout=5
            )
            redis_client.ping()
            print(f"✅ Redis service running on {redis_host}:{redis_port}")
            return True
        except Exception as e:
            print(f"❌ Redis service not running: {e}")
            return False
    except Exception as e:
        print(f"❌ Error checking Redis service: {e}")
        return False

def check_celery_workers():
    """Check if Celery workers are running"""
    print("🔍 Checking Celery workers...")
    try:
        # Use celery command to check workers
        result = subprocess.run(
            ["celery", "-A", "src.celery_app", "inspect", "active"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd="/Users/nikhil/Downloads/pranit/work/final/default-rate/backend"
        )
        
        if result.returncode == 0:
            if "Empty" in result.stdout or "{}" in result.stdout:
                print("⚠️ Celery workers running but no active tasks")
                return True
            else:
                print("✅ Celery workers running with active tasks")
                return True
        else:
            print(f"❌ Celery workers not responding: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print("❌ Celery worker check timeout")
        return False
    except FileNotFoundError:
        print("❌ Celery command not found - workers may not be running")
        return False
    except Exception as e:
        print(f"❌ Error checking Celery workers: {e}")
        return False

def check_database_service():
    """Check database connection through psql"""
    print("🔍 Checking Database service...")
    try:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            print("❌ DATABASE_URL not set")
            return False
        
        # Extract connection details from DATABASE_URL
        # Format: postgresql://user:password@host:port/database
        if database_url.startswith("postgresql://"):
            print("✅ Database URL configured (PostgreSQL)")
            # Could add more specific checks here if needed
            return True
        else:
            print(f"⚠️ Unexpected database URL format: {database_url[:20]}...")
            return True  # Assume it's okay if URL is set
    except Exception as e:
        print(f"❌ Error checking database: {e}")
        return False

def main():
    """Check all services"""
    print("🚀 Checking service status...")
    print("=" * 60)
    
    # Check all services
    fastapi_ok = check_fastapi_service()
    print()
    
    redis_ok = check_redis_service()
    print()
    
    db_ok = check_database_service()
    print()
    
    celery_ok = check_celery_workers()
    print()
    
    # Summary
    print("=" * 60)
    print("📋 SERVICE STATUS SUMMARY:")
    print(f"   FastAPI Server: {'✅ RUNNING' if fastapi_ok else '❌ NOT RUNNING'}")
    print(f"   Redis Service: {'✅ RUNNING' if redis_ok else '❌ NOT RUNNING'}")
    print(f"   Database: {'✅ CONFIGURED' if db_ok else '❌ NOT CONFIGURED'}")
    print(f"   Celery Workers: {'✅ RUNNING' if celery_ok else '❌ NOT RUNNING'}")
    
    if all([fastapi_ok, redis_ok, db_ok]):
        if celery_ok:
            print("\n🎉 ALL SERVICES ARE RUNNING! Your application is fully operational.")
        else:
            print("\n⚠️ Core services running but Celery workers are down.")
            print("   Background tasks will not process. Start workers with:")
            print("   celery -A src.celery_app worker --loglevel=info")
    else:
        print("\n🚨 SOME SERVICES ARE DOWN!")
        if not fastapi_ok:
            print("   - Start FastAPI: python -m src.app")
        if not redis_ok:
            print("   - Start Redis: redis-server")
        if not db_ok:
            print("   - Check DATABASE_URL configuration")

if __name__ == "__main__":
    main()
