#!/usr/bin/env python3
"""
Auto-Scaling Service for AWS ECS + Celery
Monitors queue lengths and provides scaling recommendations
"""

import asyncio
import redis
import json
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from celery import Celery
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

@dataclass
class QueueMetrics:
    """Queue performance metrics"""
    queue_name: str
    pending_tasks: int
    active_tasks: int
    processing_rate: float  # tasks per minute
    avg_processing_time: float  # seconds
    last_updated: datetime

@dataclass
class ScalingRecommendation:
    """Scaling decision recommendation"""
    action: str  # "scale_up", "scale_down", "maintain"
    target_workers: int
    current_workers: int
    reason: str
    priority: int  # 1=urgent, 2=normal, 3=low
    cost_impact: str

class AutoScalingService:
    """
    Auto-scaling service that monitors Redis queues and provides
    scaling recommendations for AWS ECS deployment
    """
    
    def __init__(self):
        self.redis_client = self._init_redis()
        self.celery_app = celery_app
        
        # SCALING CONFIGURATION
        self.scaling_config = {
            "min_workers": int(os.getenv("MIN_WORKERS", "2")),  # Always keep 2 ECS tasks minimum
            "max_workers": int(os.getenv("MAX_WORKERS", "12")), # Maximum 12 ECS tasks (96 workers total)
            "scale_up_threshold": int(os.getenv("SCALE_UP_THRESHOLD", "25")),  # Scale up when >25 pending tasks
            "scale_down_threshold": int(os.getenv("SCALE_DOWN_THRESHOLD", "5")), # Scale down when <5 pending tasks
            "scale_up_cooldown": int(os.getenv("SCALE_UP_COOLDOWN", "120")),   # Wait 2 minutes before scaling up again
            "scale_down_cooldown": int(os.getenv("SCALE_DOWN_COOLDOWN", "600")), # Wait 10 minutes before scaling down
            "emergency_threshold": int(os.getenv("EMERGENCY_THRESHOLD", "100")), # Emergency scaling when >100 pending
        }
        
        # QUEUE PRIORITIES FOR SCALING DECISIONS
        self.queue_priorities = {
            "high_priority": {"weight": 3, "max_wait_seconds": 60},
            "medium_priority": {"weight": 2, "max_wait_seconds": 300}, 
            "low_priority": {"weight": 1, "max_wait_seconds": 1800},
        }
        
        # SCALING HISTORY FOR COOLDOWN MANAGEMENT
        self.last_scale_action = None
        self.last_scale_time = None
        
    def _init_redis(self) -> redis.Redis:
        """Initialize Redis connection for queue monitoring"""
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        return redis.from_url(redis_url, decode_responses=True)
    
    async def get_queue_metrics(self) -> Dict[str, QueueMetrics]:
        """Get current metrics for all queues"""
        metrics = {}
        
        for queue_name in ["high_priority", "medium_priority", "low_priority"]:
            try:
                # Get queue length from Redis
                pending_tasks = self.redis_client.llen(queue_name)
                
                # Get active tasks from Celery inspect
                inspect = self.celery_app.control.inspect()
                active_tasks_data = inspect.active() or {}
                active_tasks = sum(len(tasks) for tasks in active_tasks_data.values())
                
                # Calculate processing rate (simplified - can be enhanced with historical data)
                processing_rate = self._calculate_processing_rate(queue_name)
                avg_processing_time = self._get_avg_processing_time(queue_name)
                
                metrics[queue_name] = QueueMetrics(
                    queue_name=queue_name,
                    pending_tasks=pending_tasks,
                    active_tasks=active_tasks,
                    processing_rate=processing_rate,
                    avg_processing_time=avg_processing_time,
                    last_updated=datetime.now()
                )
                
            except Exception as e:
                logger.error(f"Error getting metrics for queue {queue_name}: {e}")
                
        return metrics
    
    def _calculate_processing_rate(self, queue_name: str) -> float:
        """Calculate approximate processing rate for queue (tasks per minute)"""
        # This is simplified - in production, you'd track historical completion rates
        base_rates = {
            "high_priority": 12.0,  # Small tasks process fast
            "medium_priority": 4.0, # Normal bulk uploads 
            "low_priority": 2.0,    # Large files process slower
        }
        return base_rates.get(queue_name, 4.0)
    
    def _get_avg_processing_time(self, queue_name: str) -> float:
        """Get average processing time for queue (in seconds)"""
        # This is simplified - in production, you'd track actual completion times
        base_times = {
            "high_priority": 120,   # 2 minutes for small tasks
            "medium_priority": 480, # 8 minutes for normal tasks
            "low_priority": 900,    # 15 minutes for large tasks
        }
        return base_times.get(queue_name, 480)
    
    async def analyze_scaling_need(self) -> ScalingRecommendation:
        """Analyze current queue state and recommend scaling action"""
        metrics = await self.get_queue_metrics()
        
        # Calculate weighted queue pressure
        total_weighted_pressure = 0
        total_pending = 0
        high_priority_pending = 0
        
        for queue_name, queue_metrics in metrics.items():
            weight = self.queue_priorities[queue_name]["weight"]
            pending = queue_metrics.pending_tasks
            
            total_weighted_pressure += pending * weight
            total_pending += pending
            
            if queue_name == "high_priority":
                high_priority_pending = pending
        
        # Get current worker estimate (this would integrate with AWS ECS API in production)
        current_workers = self._estimate_current_workers()
        
        # SCALING DECISION LOGIC
        recommendation = self._make_scaling_decision(
            total_pending=total_pending,
            total_weighted_pressure=total_weighted_pressure,
            high_priority_pending=high_priority_pending,
            current_workers=current_workers,
            metrics=metrics
        )
        
        return recommendation
    
    def _estimate_current_workers(self) -> int:
        """Estimate current number of ECS service tasks"""
        # In production, this would call AWS ECS API to get actual task count
        # For now, we'll estimate based on active tasks and default configuration
        try:
            inspect = self.celery_app.control.inspect()
            stats = inspect.stats() or {}
            active_workers = len(stats)
            
            # Each ECS task has 8 workers, so estimate tasks
            estimated_instances = max(1, (active_workers + 7) // 8)
            return estimated_instances
            
        except Exception as e:
            logger.error(f"Error estimating current workers: {e}")
            return self.scaling_config["min_workers"]  # Fallback to minimum
    
    def _make_scaling_decision(
        self, 
        total_pending: int, 
        total_weighted_pressure: float,
        high_priority_pending: int,
        current_workers: int,
        metrics: Dict[str, QueueMetrics]
    ) -> ScalingRecommendation:
        """Make intelligent scaling decision based on multiple factors"""
        
        config = self.scaling_config
        
        # CHECK COOLDOWN PERIODS
        if self.last_scale_time:
            time_since_last_scale = (datetime.now() - self.last_scale_time).total_seconds()
            
            if (self.last_scale_action == "scale_up" and 
                time_since_last_scale < config["scale_up_cooldown"]):
                return ScalingRecommendation(
                    action="maintain",
                    target_workers=current_workers,
                    current_workers=current_workers,
                    reason=f"Scale-up cooldown active ({int(time_since_last_scale)}s ago)",
                    priority=3,
                    cost_impact="none"
                )
                
            if (self.last_scale_action == "scale_down" and 
                time_since_last_scale < config["scale_down_cooldown"]):
                return ScalingRecommendation(
                    action="maintain", 
                    target_workers=current_workers,
                    current_workers=current_workers,
                    reason=f"Scale-down cooldown active ({int(time_since_last_scale)}s ago)",
                    priority=3,
                    cost_impact="none"
                )
        
        # EMERGENCY SCALING - Immediate action needed
        if total_pending >= config["emergency_threshold"] or high_priority_pending >= 20:
            target_workers = min(config["max_workers"], current_workers + 3)
            return ScalingRecommendation(
                action="scale_up",
                target_workers=target_workers,
                current_workers=current_workers,
                reason=f"EMERGENCY: {total_pending} pending tasks ({high_priority_pending} high priority)",
                priority=1,
                cost_impact="high"
            )
        
        # SCALE UP CONDITIONS
        if total_pending >= config["scale_up_threshold"] and current_workers < config["max_workers"]:
            # Calculate optimal target based on processing capacity
            estimated_completion_time = total_pending / (current_workers * 2)  # Assuming 2 tasks per worker per minute
            
            if estimated_completion_time > 15:  # More than 15 minutes to clear queue
                additional_workers = min(
                    config["max_workers"] - current_workers,
                    max(1, total_pending // 15)  # Add roughly 1 worker per 15 pending tasks
                )
                target_workers = current_workers + additional_workers
                
                return ScalingRecommendation(
                    action="scale_up",
                    target_workers=target_workers,
                    current_workers=current_workers,
                    reason=f"Queue backlog: {total_pending} pending tasks, ETA: {estimated_completion_time:.1f} min",
                    priority=2,
                    cost_impact="medium"
                )
        
        # SCALE DOWN CONDITIONS  
        if (total_pending <= config["scale_down_threshold"] and 
            current_workers > config["min_workers"]):
            
            # Only scale down if we've been consistently low for a while
            target_workers = max(config["min_workers"], current_workers - 1)
            
            return ScalingRecommendation(
                action="scale_down",
                target_workers=target_workers,
                current_workers=current_workers,
                reason=f"Low queue utilization: {total_pending} pending tasks",
                priority=3,
                cost_impact="savings"
            )
        
        # MAINTAIN CURRENT SCALE
        return ScalingRecommendation(
            action="maintain",
            target_workers=current_workers,
            current_workers=current_workers,
            reason=f"Optimal scaling: {total_pending} pending tasks within normal range",
            priority=3,
            cost_impact="none"
        )
    
    async def execute_scaling_recommendation(self, recommendation: ScalingRecommendation) -> bool:
        """Execute scaling recommendation (integrates with AWS ECS API)"""
        try:
            if recommendation.action == "maintain":
                logger.info(f"✅ Scaling: {recommendation.reason}")
                return True
            
            # Log scaling decision
            logger.info(f"🚀 Scaling Decision: {recommendation.action.upper()}")
            logger.info(f"   Current Workers: {recommendation.current_workers}")
            logger.info(f"   Target Workers: {recommendation.target_workers}")
            logger.info(f"   Reason: {recommendation.reason}")
            logger.info(f"   Priority: {recommendation.priority}")
            logger.info(f"   Cost Impact: {recommendation.cost_impact}")
            
            # UPDATE SCALING HISTORY
            self.last_scale_action = recommendation.action
            self.last_scale_time = datetime.now()
            
            if recommendation.action in ["scale_up", "scale_down"]:
                # In production, this would call AWS ECS API to scale service
                # For now, we'll log the action and return success
                
                # AWS ECS API CALL (PSEUDOCODE):
                # ecs_client.update_service(
                #     cluster="default-rate-cluster",
                #     service="worker-service",
                #     desired_count=recommendation.target_workers
                # )
                
                logger.info(f"🎯 Would execute: ECS scale to {recommendation.target_workers} tasks")
                
                # Store scaling event for monitoring
                await self._record_scaling_event(recommendation)
                
                return True
                
        except Exception as e:
            logger.error(f"❌ Scaling execution failed: {e}")
            return False
        
        return True
    
    async def _record_scaling_event(self, recommendation: ScalingRecommendation):
        """Record scaling event for monitoring and analysis"""
        event = {
            "timestamp": datetime.now().isoformat(),
            "action": recommendation.action,
            "from_workers": recommendation.current_workers,
            "to_workers": recommendation.target_workers,
            "reason": recommendation.reason,
            "priority": recommendation.priority,
            "cost_impact": recommendation.cost_impact
        }
        
        # Store in Redis for monitoring dashboard
        try:
            self.redis_client.lpush("scaling_events", json.dumps(event))
            self.redis_client.ltrim("scaling_events", 0, 99)  # Keep last 100 events
        except Exception as e:
            logger.error(f"Failed to record scaling event: {e}")
    
    async def get_scaling_status(self) -> Dict:
        """Get current auto-scaling status for monitoring"""
        metrics = await self.get_queue_metrics()
        recommendation = await self.analyze_scaling_need()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "queue_metrics": {
                name: {
                    "pending_tasks": m.pending_tasks,
                    "active_tasks": m.active_tasks,
                    "processing_rate": m.processing_rate
                } for name, m in metrics.items()
            },
            "scaling_recommendation": {
                "action": recommendation.action,
                "current_workers": recommendation.current_workers,
                "target_workers": recommendation.target_workers,
                "reason": recommendation.reason,
                "priority": recommendation.priority
            },
            "configuration": self.scaling_config,
            "last_scale_action": self.last_scale_action,
            "last_scale_time": self.last_scale_time.isoformat() if self.last_scale_time else None
        }

# SINGLETON INSTANCE
auto_scaling_service = AutoScalingService()
