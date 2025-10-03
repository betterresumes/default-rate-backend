#!/usr/bin/env python3
"""
Auto-Scaling API Routes
Provides endpoints for monitoring and controlling auto-scaling
"""

fro@router.post("/execute")
@rate_limit_job_control
async def execute_auto_scaling(background_tasks: BackgroundTasks):fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, List, Optional
import logging
from datetime import datetime

from app.services.auto_scaling_service import auto_scaling_service
from ...middleware.rate_limiting import (
    rate_limit_analytics, rate_limit_job_control, rate_limit_user_update, rate_limit_user_delete
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/scaling", tags=["auto-scaling"])

class ScalingConfigUpdate(BaseModel):
    """Model for updating scaling configuration"""
    min_workers: Optional[int] = None
    max_workers: Optional[int] = None
    scale_up_threshold: Optional[int] = None
    scale_down_threshold: Optional[int] = None

class ManualScalingRequest(BaseModel):
    """Model for manual scaling requests"""
    target_workers: int
    reason: str = "Manual scaling request"

@router.get("/status")
@rate_limit_analytics
async def get_scaling_status():
    """
    Get current auto-scaling status and queue metrics
    
    Returns:
    - Queue metrics for all priority levels
    - Current scaling recommendation  
    - Configuration settings
    - Recent scaling history
    """
    try:
        status = await auto_scaling_service.get_scaling_status()
        return {
            "success": True,
            "data": status
        }
    except Exception as e:
        logger.error(f"Error getting scaling status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/metrics")
@rate_limit_analytics
async def get_scaling_metrics():
    """
    Get detailed queue metrics for monitoring dashboard
    
    Returns:
    - Pending tasks by priority
    - Active tasks by queue
    - Processing rates
    - Average processing times
    """
    try:
        metrics = await auto_scaling_service.get_queue_metrics()
        
        response = {}
        for queue_name, metric in metrics.items():
            response[queue_name] = {
                "pending_tasks": metric.pending_tasks,
                "active_tasks": metric.active_tasks,
                "processing_rate": metric.processing_rate,
                "avg_processing_time": metric.avg_processing_time,
                "last_updated": metric.last_updated.isoformat()
            }
            
        return {
            "success": True,
            "data": response,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting queue metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/recommendation")
@rate_limit_analytics
async def get_scaling_recommendation():
    """
    Get current scaling recommendation without executing
    
    Returns:
    - Recommended action (scale_up/scale_down/maintain)
    - Target worker count
    - Reasoning for recommendation
    - Priority and cost impact
    """
    try:
        recommendation = await auto_scaling_service.analyze_scaling_need()
        
        return {
            "success": True,
            "data": {
                "action": recommendation.action,
                "current_workers": recommendation.current_workers,
                "target_workers": recommendation.target_workers,
                "reason": recommendation.reason,
                "priority": recommendation.priority,
                "cost_impact": recommendation.cost_impact,
                "timestamp": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting scaling recommendation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/execute")
async def execute_scaling(background_tasks: BackgroundTasks):
    """
    Execute current scaling recommendation
    
    This endpoint analyzes current queue state and executes
    the recommended scaling action (if any)
    """
    try:
        recommendation = await auto_scaling_service.analyze_scaling_need()
        
        if recommendation.action == "maintain":
            return {
                "success": True,
                "action": "maintain",
                "message": recommendation.reason,
                "executed": False
            }
        
        # Execute scaling in background
        success = await auto_scaling_service.execute_scaling_recommendation(recommendation)
        
        if success:
            return {
                "success": True,
                "action": recommendation.action,
                "current_workers": recommendation.current_workers,
                "target_workers": recommendation.target_workers,
                "reason": recommendation.reason,
                "executed": True,
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to execute scaling")
            
    except Exception as e:
        logger.error(f"Error executing scaling: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/manual")
@rate_limit_job_control
async def manual_scaling(request: ManualScalingRequest):
    """
    Trigger manual scaling to specific worker count
    
    Use with caution - bypasses auto-scaling logic
    """
    try:
        # Validate worker count
        config = auto_scaling_service.scaling_config
        if request.target_workers < config["min_workers"]:
            raise HTTPException(
                status_code=400, 
                detail=f"Target workers ({request.target_workers}) below minimum ({config['min_workers']})"
            )
        
        if request.target_workers > config["max_workers"]:
            raise HTTPException(
                status_code=400,
                detail=f"Target workers ({request.target_workers}) above maximum ({config['max_workers']})"
            )
        
        # Create manual scaling recommendation
        from app.services.auto_scaling_service import ScalingRecommendation
        
        current_workers = auto_scaling_service._estimate_current_workers()
        action = "scale_up" if request.target_workers > current_workers else "scale_down"
        if request.target_workers == current_workers:
            action = "maintain"
        
        recommendation = ScalingRecommendation(
            action=action,
            target_workers=request.target_workers,
            current_workers=current_workers,
            reason=f"Manual scaling: {request.reason}",
            priority=1,
            cost_impact="manual"
        )
        
        # Execute manual scaling
        success = await auto_scaling_service.execute_scaling_recommendation(recommendation)
        
        if success:
            return {
                "success": True,
                "action": action,
                "current_workers": current_workers,
                "target_workers": request.target_workers,
                "reason": request.reason,
                "executed": True,
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to execute manual scaling")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in manual scaling: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/config")
@rate_limit_analytics
async def get_scaling_config():
    """Get current auto-scaling configuration"""
    return {
        "success": True,
        "data": auto_scaling_service.scaling_config
    }

@router.put("/config")
@rate_limit_user_update
async def update_scaling_config(config: ScalingConfigUpdate):
    """
    Update auto-scaling configuration
    
    Allows runtime adjustment of scaling parameters
    """
    try:
        current_config = auto_scaling_service.scaling_config
        
        # Update configuration with provided values
        if config.min_workers is not None:
            if config.min_workers < 1:
                raise HTTPException(status_code=400, detail="Minimum workers must be at least 1")
            current_config["min_workers"] = config.min_workers
            
        if config.max_workers is not None:
            if config.max_workers < current_config["min_workers"]:
                raise HTTPException(
                    status_code=400, 
                    detail="Maximum workers must be greater than minimum workers"
                )
            current_config["max_workers"] = config.max_workers
            
        if config.scale_up_threshold is not None:
            if config.scale_up_threshold < 1:
                raise HTTPException(status_code=400, detail="Scale up threshold must be at least 1")
            current_config["scale_up_threshold"] = config.scale_up_threshold
            
        if config.scale_down_threshold is not None:
            if config.scale_down_threshold < 0:
                raise HTTPException(status_code=400, detail="Scale down threshold cannot be negative")
            current_config["scale_down_threshold"] = config.scale_down_threshold
        
        return {
            "success": True,
            "message": "Configuration updated successfully",
            "data": current_config
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating scaling config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history")
@rate_limit_analytics
async def get_scaling_history(limit: int = 50):
    """
    Get recent scaling events history
    
    Returns last 50 scaling actions with timestamps and reasons
    """
    try:
        # Get scaling events from Redis
        events = auto_scaling_service.redis_client.lrange("scaling_events", 0, 49)
        
        history = []
        for event_str in events:
            try:
                import json
                event = json.loads(event_str)
                history.append(event)
            except json.JSONDecodeError:
                continue
                
        return {
            "success": True,
            "data": history,
            "count": len(history)
        }
        
    except Exception as e:
        logger.error(f"Error getting scaling history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/history")
@rate_limit_user_delete
async def clear_scaling_history():
    """Clear scaling events history"""
    try:
        auto_scaling_service.redis_client.delete("scaling_events")
        return {
            "success": True,
            "message": "Scaling history cleared"
        }
    except Exception as e:
        logger.error(f"Error clearing scaling history: {e}")
        raise HTTPException(status_code=500, detail=str(e))
