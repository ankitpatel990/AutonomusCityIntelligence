"""
Safety Control API Endpoints

Implements FRD-05 FR-05.5: Safety control APIs.
REST API endpoints for safety and manual control operations.
"""

from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import Optional
import time

from app.safety.system_modes import SystemMode, SystemModeManager

router = APIRouter(prefix="/api/safety", tags=["safety"])

# Global instances (injected from main.py)
mode_manager: Optional[SystemModeManager] = None
watchdog = None
override_manager = None
conflict_validator = None


def set_safety_components(mode_mgr, wd, override_mgr, validator):
    """Set global safety components"""
    global mode_manager, watchdog, override_manager, conflict_validator
    mode_manager = mode_mgr
    watchdog = wd
    override_manager = override_mgr
    conflict_validator = validator


# Request models
class ModeChangeRequest(BaseModel):
    mode: str  # NORMAL, EMERGENCY, INCIDENT
    reason: str


class FailSafeExitRequest(BaseModel):
    operatorId: str


class ForceSignalRequest(BaseModel):
    junctionId: str
    direction: str
    duration: int
    operatorId: str
    reason: str


class AgentControlRequest(BaseModel):
    action: str  # disable, enable
    operatorId: str
    reason: Optional[str] = ""


class EmergencyStopRequest(BaseModel):
    operatorId: str
    reason: str


# Operator authentication (basic for hackathon)
def verify_operator(operator_id: str = Header(None, alias="X-Operator-ID")) -> str:
    """Verify operator ID from header"""
    if not operator_id:
        raise HTTPException(status_code=401, detail="Operator ID required")
    
    # TODO: Implement real authentication
    return operator_id


# Mode management endpoints

@router.get("/mode")
async def get_current_mode():
    """Get current system mode"""
    if not mode_manager:
        raise HTTPException(status_code=500, detail="Mode manager not initialized")
    
    return mode_manager.get_state_info()


@router.post("/mode/change")
async def change_mode(request: ModeChangeRequest):
    """Change system mode"""
    if not mode_manager:
        raise HTTPException(status_code=500, detail="Mode manager not initialized")
    
    try:
        mode = SystemMode[request.mode.upper()]
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Invalid mode: {request.mode}")
    
    success = mode_manager.transition_to(mode, request.reason)
    
    if not success:
        raise HTTPException(status_code=400, detail="Mode transition failed")
    
    return {
        'status': 'success',
        'newMode': mode.value,
        'timestamp': time.time()
    }


@router.get("/mode/history")
async def get_mode_history(limit: int = 10):
    """Get mode transition history"""
    if not mode_manager:
        raise HTTPException(status_code=500, detail="Mode manager not initialized")
    
    return mode_manager.get_transition_history(limit)


# Fail-safe endpoints

@router.post("/failsafe/trigger")
async def trigger_failsafe(reason: str, operator: str = Depends(verify_operator)):
    """Manually trigger fail-safe mode"""
    if not mode_manager:
        raise HTTPException(status_code=500, detail="Mode manager not initialized")
    
    mode_manager.enter_fail_safe(f"Manual trigger by {operator}: {reason}")
    
    return {
        'status': 'failsafe_triggered',
        'operator': operator,
        'reason': reason,
        'timestamp': time.time()
    }


@router.post("/failsafe/exit")
async def exit_failsafe(request: FailSafeExitRequest):
    """Exit fail-safe mode (requires operator authorization)"""
    if not mode_manager:
        raise HTTPException(status_code=500, detail="Mode manager not initialized")
    
    success = mode_manager.exit_fail_safe(request.operatorId)
    
    if not success:
        raise HTTPException(status_code=400, detail="Failed to exit fail-safe mode")
    
    return {
        'status': 'failsafe_exited',
        'operator': request.operatorId,
        'timestamp': time.time()
    }


# Manual override endpoints

@router.post("/override/signal")
async def force_signal_state(request: ForceSignalRequest):
    """Force a specific signal state"""
    if not override_manager:
        raise HTTPException(status_code=500, detail="Override manager not initialized")
    
    try:
        override_id = await override_manager.force_signal_state(
            junction_id=request.junctionId,
            direction=request.direction,
            duration=request.duration,
            operator_id=request.operatorId,
            reason=request.reason
        )
        
        return {
            'status': 'override_created',
            'overrideId': override_id,
            'timestamp': time.time()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/override/agent")
async def control_agent(request: AgentControlRequest):
    """Disable or enable autonomous agent"""
    if not override_manager:
        raise HTTPException(status_code=500, detail="Override manager not initialized")
    
    if request.action == 'disable':
        override_id = await override_manager.disable_autonomous_agent(
            operator_id=request.operatorId,
            reason=request.reason
        )
        return {
            'status': 'agent_disabled',
            'overrideId': override_id
        }
    elif request.action == 'enable':
        success = await override_manager.enable_autonomous_agent(
            operator_id=request.operatorId
        )
        if not success:
            raise HTTPException(status_code=400, detail="Failed to enable agent")
        return {'status': 'agent_enabled'}
    else:
        raise HTTPException(status_code=400, detail="Invalid action")


@router.post("/override/emergency-stop")
async def emergency_stop(request: EmergencyStopRequest):
    """Emergency stop - all signals RED"""
    if not override_manager:
        raise HTTPException(status_code=500, detail="Override manager not initialized")
    
    override_id = await override_manager.emergency_stop(
        operator_id=request.operatorId,
        reason=request.reason
    )
    
    return {
        'status': 'emergency_stop_activated',
        'overrideId': override_id,
        'timestamp': time.time()
    }


@router.delete("/override/{override_id}")
async def cancel_override(override_id: str, operator: str = Depends(verify_operator)):
    """Cancel an active override"""
    if not override_manager:
        raise HTTPException(status_code=500, detail="Override manager not initialized")
    
    success = await override_manager.cancel_override(override_id, operator)
    
    if not success:
        raise HTTPException(status_code=404, detail="Override not found or already cancelled")
    
    return {'status': 'override_cancelled'}


@router.get("/overrides")
async def get_active_overrides():
    """Get all active overrides"""
    if not override_manager:
        raise HTTPException(status_code=500, detail="Override manager not initialized")
    
    return override_manager.get_active_overrides()


@router.get("/overrides/history")
async def get_override_history(limit: int = 50):
    """Get override history (audit trail)"""
    if not override_manager:
        raise HTTPException(status_code=500, detail="Override manager not initialized")
    
    return override_manager.get_override_history(limit)


# Health monitoring endpoints

@router.get("/health")
async def get_health_status():
    """Get system health status"""
    if not watchdog:
        raise HTTPException(status_code=500, detail="Watchdog not initialized")
    
    return watchdog.get_health_status()


@router.get("/health/conflicts")
async def check_signal_conflicts():
    """Check for signal conflicts across all junctions"""
    if not conflict_validator:
        raise HTTPException(status_code=500, detail="Conflict validator not initialized")
    
    # TODO: Implement junction-by-junction conflict check
    return {'conflicts': [], 'allClear': True}

