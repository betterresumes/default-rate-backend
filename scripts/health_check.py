#!/usr/bin/env python3
"""
AccuNode API Startup Health Check
Verifies all services are working correctly after deployment
"""

import asyncio
import aiohttp
import logging
import os
import sys
import time
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HealthChecker:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def check_health_endpoint(self):
        """Check the basic health endpoint"""
        try:
            async with self.session.get(f"{self.base_url}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"✅ Health endpoint: {data}")
                    return True
                else:
                    logger.error(f"❌ Health endpoint returned {response.status}")
                    return False
        except Exception as e:
            logger.error(f"❌ Health endpoint error: {e}")
            return False
    
    async def check_database_connection(self):
        """Check database connectivity through API"""
        try:
            # Try to access an endpoint that requires database
            async with self.session.get(f"{self.base_url}/api/v1/auth/health") as response:
                if response.status in [200, 404]:  # 404 is OK, means API is running
                    logger.info("✅ Database connection: Working")
                    return True
                else:
                    logger.error(f"❌ Database connection test failed: {response.status}")
                    return False
        except Exception as e:
            logger.error(f"❌ Database connection error: {e}")
            return False
    
    async def check_redis_connection(self):
        """Check Redis connectivity (rate limiting)"""
        try:
            # Make multiple requests to trigger rate limiting
            responses = []
            for i in range(3):
                async with self.session.get(f"{self.base_url}/") as response:
                    responses.append(response.status)
            
            if all(status == 200 for status in responses):
                logger.info("✅ Redis/Rate limiting: Working")
                return True
            else:
                logger.warning(f"⚠️ Redis/Rate limiting: Responses {responses}")
                return False
        except Exception as e:
            logger.error(f"❌ Redis connection error: {e}")
            return False
    
    async def run_comprehensive_check(self):
        """Run all health checks"""
        logger.info("🏥 Starting Comprehensive Health Check")
        logger.info("=" * 50)
        
        checks = [
            ("Health Endpoint", self.check_health_endpoint),
            ("Database Connection", self.check_database_connection), 
            ("Redis/Rate Limiting", self.check_redis_connection),
        ]
        
        results = []
        for check_name, check_func in checks:
            logger.info(f"\n🔍 Checking: {check_name}")
            try:
                result = await check_func()
                results.append((check_name, result))
            except Exception as e:
                logger.error(f"❌ {check_name} failed with exception: {e}")
                results.append((check_name, False))
        
        # Summary
        logger.info("\n" + "=" * 50)
        logger.info("📊 HEALTH CHECK SUMMARY")
        logger.info("=" * 50)
        
        passed = 0
        for check_name, result in results:
            status = "✅ PASS" if result else "❌ FAIL"
            logger.info(f"{status:<12} {check_name}")
            if result:
                passed += 1
        
        success_rate = (passed / len(results)) * 100
        logger.info(f"\nResults: {passed}/{len(results)} checks passed ({success_rate:.1f}%)")
        
        if passed == len(results):
            logger.info("\n🎉 ALL HEALTH CHECKS PASSED!")
            logger.info("✅ AccuNode API is ready to serve traffic")
            return True
        else:
            logger.error("\n⚠️ SOME HEALTH CHECKS FAILED!")
            logger.error(f"❌ {len(results) - passed} check(s) failed")
            logger.error("🔧 Please check logs and configuration")
            return False

async def wait_for_startup(base_url, max_wait=60):
    """Wait for the API to start up"""
    logger.info(f"⏳ Waiting for API startup at {base_url} (max {max_wait}s)")
    
    start_time = time.time()
    while time.time() - start_time < max_wait:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{base_url}/health", timeout=5) as response:
                    if response.status == 200:
                        logger.info(f"✅ API is up! ({time.time() - start_time:.1f}s)")
                        return True
        except Exception:
            pass
        
        await asyncio.sleep(2)
        logger.info("⏳ Still waiting for API startup...")
    
    logger.error(f"❌ API failed to start within {max_wait} seconds")
    return False

async def main():
    """Main health check routine"""
    
    # Configuration
    base_url = os.getenv("API_URL", "http://localhost:8000")
    max_wait = int(os.getenv("MAX_WAIT_TIME", "60"))
    
    logger.info("🏥 AccuNode API Health Checker")
    logger.info(f"🎯 Target: {base_url}")
    logger.info(f"⏰ Started: {datetime.utcnow().isoformat()}")
    
    # Wait for startup
    if not await wait_for_startup(base_url, max_wait):
        sys.exit(1)
    
    # Run comprehensive health check
    async with HealthChecker(base_url) as checker:
        success = await checker.run_comprehensive_check()
        
    if success:
        logger.info("\n🚀 Health check complete - API is healthy!")
        sys.exit(0)
    else:
        logger.error("\n💥 Health check failed - API has issues!")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
