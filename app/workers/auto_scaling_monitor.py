#!/usr/bin/env python3
"""
Auto-Scaling Background Task
Continuously monitors queues and executes scaling decisions
"""

import asyncio
import logging
from datetime import datetime, timedelta
from app.services.auto_scaling_service import auto_scaling_service

logger = logging.getLogger(__name__)

class AutoScalingMonitor:
    """Background service that continuously monitors and executes scaling"""
    
    def __init__(self):
        self.is_running = False
        self.monitor_interval = 60  # Check every 60 seconds
        self.last_health_check = None
        
    async def start_monitoring(self):
        """Start the auto-scaling monitoring loop"""
        if self.is_running:
            logger.warning("Auto-scaling monitor is already running")
            return
            
        self.is_running = True
        logger.info("🚀 Starting Auto-Scaling Monitor")
        logger.info(f"   Monitor Interval: {self.monitor_interval} seconds")
        logger.info(f"   Min Workers: {auto_scaling_service.scaling_config['min_workers']}")
        logger.info(f"   Max Workers: {auto_scaling_service.scaling_config['max_workers']}")
        
        try:
            while self.is_running:
                await self._monitoring_cycle()
                await asyncio.sleep(self.monitor_interval)
                
        except Exception as e:
            logger.error(f"❌ Auto-scaling monitor crashed: {e}")
            self.is_running = False
            raise
    
    async def _monitoring_cycle(self):
        """Single monitoring cycle - check queues and execute scaling"""
        try:
            cycle_start = datetime.now()
            
            # 1. GET CURRENT METRICS
            metrics = await auto_scaling_service.get_queue_metrics()
            total_pending = sum(m.pending_tasks for m in metrics.values())
            total_active = sum(m.active_tasks for m in metrics.values())
            
            # 2. ANALYZE SCALING NEED
            recommendation = await auto_scaling_service.analyze_scaling_need()
            
            # 3. LOG CURRENT STATE
            logger.info(f"📊 Queue Status: {total_pending} pending, {total_active} active")
            logger.info(f"   High Priority: {metrics.get('high_priority', {}).pending_tasks} pending")
            logger.info(f"   Medium Priority: {metrics.get('medium_priority', {}).pending_tasks} pending") 
            logger.info(f"   Low Priority: {metrics.get('low_priority', {}).pending_tasks} pending")
            
            # 4. EXECUTE SCALING DECISION
            if recommendation.action != "maintain":
                logger.info(f"🎯 Scaling Action: {recommendation.action.upper()}")
                logger.info(f"   From {recommendation.current_workers} to {recommendation.target_workers} workers")
                logger.info(f"   Reason: {recommendation.reason}")
                
                success = await auto_scaling_service.execute_scaling_recommendation(recommendation)
                if success:
                    logger.info("✅ Scaling executed successfully")
                else:
                    logger.error("❌ Scaling execution failed")
            else:
                logger.debug(f"✅ No scaling needed: {recommendation.reason}")
            
            # 5. HEALTH CHECK
            cycle_duration = (datetime.now() - cycle_start).total_seconds()
            self.last_health_check = datetime.now()
            
            if cycle_duration > 30:  # Warn if cycle takes too long
                logger.warning(f"⚠️ Monitoring cycle took {cycle_duration:.1f} seconds")
            
            # 6. STORE METRICS FOR MONITORING
            await self._store_monitoring_metrics(metrics, recommendation, cycle_duration)
            
        except Exception as e:
            logger.error(f"❌ Error in monitoring cycle: {e}")
            # Continue monitoring even if one cycle fails
    
    async def _store_monitoring_metrics(self, metrics, recommendation, cycle_duration):
        """Store monitoring metrics for dashboard and analysis"""
        try:
            monitoring_data = {
                "timestamp": datetime.now().isoformat(),
                "cycle_duration": cycle_duration,
                "queue_metrics": {
                    name: {
                        "pending": metric.pending_tasks,
                        "active": metric.active_tasks,
                        "processing_rate": metric.processing_rate
                    } for name, metric in metrics.items()
                },
                "scaling_recommendation": {
                    "action": recommendation.action,
                    "current_workers": recommendation.current_workers,
                    "target_workers": recommendation.target_workers,
                    "priority": recommendation.priority
                }
            }
            
            # Store in Redis for monitoring dashboard (keep last 100 data points)
            import json
            auto_scaling_service.redis_client.lpush(
                "monitoring_metrics", 
                json.dumps(monitoring_data)
            )
            auto_scaling_service.redis_client.ltrim("monitoring_metrics", 0, 99)
            
        except Exception as e:
            logger.error(f"Failed to store monitoring metrics: {e}")
    
    def stop_monitoring(self):
        """Stop the auto-scaling monitoring"""
        if self.is_running:
            logger.info("🛑 Stopping Auto-Scaling Monitor")
            self.is_running = False
        else:
            logger.warning("Auto-scaling monitor is not running")
    
    def get_monitor_status(self):
        """Get current monitor status"""
        return {
            "is_running": self.is_running,
            "monitor_interval": self.monitor_interval,
            "last_health_check": self.last_health_check.isoformat() if self.last_health_check else None,
            "uptime": (datetime.now() - self.last_health_check).total_seconds() if self.last_health_check else 0
        }

# SINGLETON INSTANCE
auto_scaling_monitor = AutoScalingMonitor()

# STARTUP TASK
async def start_auto_scaling_monitor():
    """Start auto-scaling monitor as background task"""
    try:
        await auto_scaling_monitor.start_monitoring()
    except Exception as e:
        logger.error(f"Failed to start auto-scaling monitor: {e}")
        raise
