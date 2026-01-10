"""
Agent Routes - Autonomous agent control endpoints

Implements FRD-03 FR-03.6: Agent control interface.

Endpoints:
- POST /api/agent/start - Start agent loop
- POST /api/agent/stop - Stop agent loop
- POST /api/agent/pause - Pause agent
- POST /api/agent/resume - Resume agent
- GET /api/agent/status - Get agent status
- GET /api/agent/logs - Get decision logs
- GET /api/agent/logs/{log_id} - Get specific log
- GET /api/agent/stats - Get module statistics
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Literal
import time
import json

from app.database.database import get_db
from app.database.models import AgentLog
from app.agent import get_agent, AgentStrategy, AgentStatus

router = APIRouter(prefix="/api/agent", tags=["agent"])


# ============================================
# Request/Response Models
# ============================================

class AgentStartRequest(BaseModel):
    """Request body for starting the agent"""
    strategy: Literal["RL", "RULE_BASED", "MANUAL"] = "RL"


class AgentResponse(BaseModel):
    """Standard agent response"""
    status: str
    message: str = ""
    timestamp: float


class AgentStatusResponse(BaseModel):
    """Agent status response"""
    status: Literal["RUNNING", "PAUSED", "STOPPED"]
    strategy: Literal["RL", "RULE_BASED", "MANUAL"]
    uptime: float
    decisions: int
    avgLatency: float
    loopCount: int
    lastDecisionTime: float
    errorsCount: int = 0


# ============================================
# Endpoints
# ============================================

@router.post("/start", response_model=AgentResponse)
async def start_agent(request: AgentStartRequest):
    """
    Start the autonomous agent loop
    
    The agent will begin making traffic signal decisions based on
    the specified strategy (RL, RULE_BASED, or MANUAL).
    
    Response time target: < 100ms
    """
    agent = get_agent()
    
    if not agent:
        raise HTTPException(
            status_code=500, 
            detail="Agent not initialized. Server may still be starting."
        )
    
    try:
        # Map string to enum
        strategy_map = {
            "RL": AgentStrategy.RL,
            "RULE_BASED": AgentStrategy.RULE_BASED,
            "MANUAL": AgentStrategy.MANUAL
        }
        strategy = strategy_map.get(request.strategy.upper(), AgentStrategy.RL)
        
        await agent.start(strategy)
        
        return AgentResponse(
            status="started",
            message=f"Agent started with {strategy.value} strategy",
            timestamp=time.time()
        )
        
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop", response_model=AgentResponse)
async def stop_agent():
    """
    Stop the agent loop
    
    Stops all autonomous decision-making. Signals will remain
    in their current state until manually changed or agent restarted.
    """
    agent = get_agent()
    
    if not agent:
        raise HTTPException(status_code=500, detail="Agent not initialized")
    
    await agent.stop()
    
    return AgentResponse(
        status="stopped",
        message="Agent stopped successfully",
        timestamp=time.time()
    )


@router.post("/pause", response_model=AgentResponse)
async def pause_agent():
    """
    Pause the agent loop
    
    Temporarily pauses decision-making while maintaining state.
    Use /resume to continue.
    """
    agent = get_agent()
    
    if not agent:
        raise HTTPException(status_code=500, detail="Agent not initialized")
    
    await agent.pause()
    
    return AgentResponse(
        status="paused",
        message="Agent paused",
        timestamp=time.time()
    )


@router.post("/resume", response_model=AgentResponse)
async def resume_agent():
    """
    Resume the agent loop
    
    Continues decision-making from where it was paused.
    """
    agent = get_agent()
    
    if not agent:
        raise HTTPException(status_code=500, detail="Agent not initialized")
    
    await agent.resume()
    
    return AgentResponse(
        status="resumed",
        message="Agent resumed",
        timestamp=time.time()
    )


@router.get("/status", response_model=AgentStatusResponse)
async def get_agent_status():
    """
    Get current agent status
    
    Returns running state, strategy, uptime, decision count,
    and average latency metrics.
    
    Response time target: < 100ms
    """
    agent = get_agent()
    
    if not agent:
        # Return default status if agent not initialized
        return AgentStatusResponse(
            status="STOPPED",
            strategy="RL",
            uptime=0,
            decisions=0,
            avgLatency=0,
            loopCount=0,
            lastDecisionTime=time.time(),
            errorsCount=0
        )
    
    stats = agent.get_statistics()
    
    return AgentStatusResponse(
        status=stats['status'],
        strategy=stats['strategy'],
        uptime=stats['uptime'],
        decisions=stats['decisionsCount'],
        avgLatency=stats['avgLatency'],
        loopCount=stats['loopCount'],
        lastDecisionTime=stats['lastDecisionTime'],
        errorsCount=stats['errorsCount']
    )


@router.get("/stats")
async def get_agent_module_stats():
    """
    Get detailed statistics from all agent modules
    
    Returns stats from perception, decision, action, and monitoring modules.
    """
    agent = get_agent()
    
    if not agent:
        return {"error": "Agent not initialized"}
    
    stats = {
        'agent': agent.get_statistics(),
        'perception': agent.perception.get_stats() if agent.perception else None,
        'decision': agent.decision.get_stats() if agent.decision else None,
        'action': agent.action.get_statistics() if agent.action else None,
        'monitoring': agent.monitor.get_statistics() if agent.monitor else None,
        'timestamp': time.time()
    }
    
    return stats


@router.get("/logs", response_model=List[Dict[str, Any]])
async def get_agent_logs(
    limit: int = Query(100, ge=1, le=1000, description="Number of logs to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    strategy: Optional[str] = Query(None, description="Filter by strategy"),
    mode: Optional[str] = Query(None, description="Filter by mode"),
    db: Session = Depends(get_db)
):
    """
    Get agent decision logs
    
    Returns historical decision records from the database.
    Useful for debugging and analyzing agent behavior.
    
    Response time target: < 200ms
    """
    query = db.query(AgentLog)
    
    # Apply filters
    if strategy:
        query = query.filter(AgentLog.strategy == strategy.upper())
    if mode:
        query = query.filter(AgentLog.mode == mode.upper())
    
    logs = query\
        .order_by(AgentLog.timestamp.desc())\
        .limit(limit)\
        .offset(offset)\
        .all()
    
    return [
        {
            "id": log.id,
            "timestamp": log.timestamp,
            "mode": log.mode,
            "strategy": log.strategy,
            "latency": log.decision_latency,
            "decisionsCount": len(json.loads(log.decisions_json)) if log.decisions_json else 0,
            "createdAt": log.created_at.isoformat() if log.created_at else None
        }
        for log in logs
    ]


@router.get("/logs/count")
async def get_agent_logs_count(
    strategy: Optional[str] = Query(None, description="Filter by strategy"),
    mode: Optional[str] = Query(None, description="Filter by mode"),
    db: Session = Depends(get_db)
):
    """Get total count of agent logs"""
    query = db.query(AgentLog)
    
    if strategy:
        query = query.filter(AgentLog.strategy == strategy.upper())
    if mode:
        query = query.filter(AgentLog.mode == mode.upper())
    
    count = query.count()
    return {"count": count}


@router.get("/logs/{log_id}", response_model=Dict[str, Any])
async def get_agent_log(log_id: int, db: Session = Depends(get_db)):
    """Get specific agent log by ID with full details"""
    log = db.query(AgentLog).filter(AgentLog.id == log_id).first()
    
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    
    return {
        "id": log.id,
        "timestamp": log.timestamp,
        "mode": log.mode,
        "strategy": log.strategy,
        "latency": log.decision_latency,
        "decisions": json.loads(log.decisions_json) if log.decisions_json else [],
        "stateSummary": json.loads(log.state_summary_json) if log.state_summary_json else {},
        "createdAt": log.created_at.isoformat() if log.created_at else None
    }


@router.get("/last-state")
async def get_last_state():
    """
    Get the last perceived state from the agent
    
    Returns the most recent state snapshot from the perception module.
    """
    agent = get_agent()
    
    if not agent:
        return {"error": "Agent not initialized"}
    
    state = agent.get_last_state()
    
    if not state:
        return {"message": "No state available yet"}
    
    return state.to_dict()


@router.get("/last-decisions")
async def get_last_decisions():
    """
    Get the last decisions made by the agent
    
    Returns the most recent set of signal decisions.
    """
    agent = get_agent()
    
    if not agent:
        return {"error": "Agent not initialized"}
    
    decisions = agent.get_last_decisions()
    
    if not decisions:
        return {"message": "No decisions available yet"}
    
    return decisions.to_dict()


@router.post("/strategy")
async def set_agent_strategy(request: AgentStartRequest):
    """
    Change agent strategy without restart
    
    Updates the decision-making strategy while agent is running.
    """
    agent = get_agent()
    
    if not agent:
        raise HTTPException(status_code=500, detail="Agent not initialized")
    
    strategy_map = {
        "RL": AgentStrategy.RL,
        "RULE_BASED": AgentStrategy.RULE_BASED,
        "MANUAL": AgentStrategy.MANUAL
    }
    
    new_strategy = strategy_map.get(request.strategy.upper(), AgentStrategy.RL)
    agent.strategy = new_strategy
    
    return {
        "status": "updated",
        "strategy": new_strategy.value,
        "timestamp": time.time()
    }


@router.delete("/logs")
async def cleanup_agent_logs(
    retention_days: int = Query(7, ge=1, le=30, description="Days to retain"),
    db: Session = Depends(get_db)
):
    """
    Clean up old agent logs
    
    Deletes logs older than the specified retention period.
    """
    cutoff_time = time.time() - (retention_days * 24 * 3600)
    
    deleted = db.query(AgentLog)\
        .filter(AgentLog.timestamp < cutoff_time)\
        .delete()
    
    db.commit()
    
    return {
        "deleted": deleted,
        "retentionDays": retention_days,
        "timestamp": time.time()
    }
