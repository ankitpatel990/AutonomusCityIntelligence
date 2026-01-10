"""
Emergency Routes - Emergency vehicle and corridor endpoints

Implements FRD-07 FR-07.4: Emergency control APIs.

Endpoints:
- POST /api/emergency/trigger - Trigger emergency scenario
- GET /api/emergency/status - Get emergency status
- POST /api/emergency/cancel - Cancel emergency
- GET /api/emergency/corridor - Get active corridor
- GET /api/emergency/statistics - Get emergency statistics
- GET /api/emergency/history - Get emergency history
- POST /api/emergency/simulate - Simulate corridor (dry run)
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import time

from app.emergency import (
    EmergencyTracker,
    EmergencyPathfinder,
    GreenCorridorManager,
    EmergencyType,
    EmergencyStatus,
    get_emergency_tracker,
    get_emergency_pathfinder,
    get_corridor_manager,
)

router = APIRouter(prefix="/api/emergency", tags=["emergency"])


# ============================================
# Request/Response Models
# ============================================

class EmergencyTriggerRequest(BaseModel):
    """Request to trigger emergency vehicle scenario"""
    spawnPoint: str = Field(
        ...,
        description="Junction ID where ambulance spawns"
    )
    destination: str = Field(
        ...,
        description="Junction ID destination (e.g., hospital)"
    )
    vehicleType: str = Field(
        default="AMBULANCE",
        description="Type of emergency vehicle: AMBULANCE, FIRE_TRUCK, POLICE"
    )
    vehicleId: Optional[str] = Field(
        default=None,
        description="Custom vehicle ID (auto-generated if not provided)"
    )
    numberPlate: Optional[str] = Field(
        default=None,
        description="Custom number plate (auto-generated if not provided)"
    )


class EmergencyTriggerResponse(BaseModel):
    """Response from emergency trigger"""
    status: str
    sessionId: str
    vehicleId: str
    numberPlate: str
    corridorPath: List[str]
    roadPath: List[str]
    estimatedTime: float
    distance: float
    activatedAt: float
    destination: str


class EmergencyStatusResponse(BaseModel):
    """Emergency system status"""
    active: bool
    sessionId: Optional[str] = None
    vehicleId: Optional[str] = None
    vehicleType: Optional[str] = None
    numberPlate: Optional[str] = None
    status: Optional[str] = None
    corridorPath: List[str] = []
    roadPath: List[str] = []
    currentJunction: Optional[str] = None
    progress: float = 0
    estimatedArrival: Optional[float] = None
    activatedAt: Optional[float] = None
    corridorActive: bool = False
    corridor: Optional[Dict[str, Any]] = None


class CorridorResponse(BaseModel):
    """Active corridor details"""
    sessionId: str
    vehicleId: str
    junctionPath: List[str]
    roadPath: List[str]
    currentJunctionIndex: int
    junctionCount: int
    activatedAt: float
    signalOverrides: Dict[str, str]
    status: str = "ACTIVE"


class EmergencyStatisticsResponse(BaseModel):
    """Emergency system statistics"""
    totalEmergencies: int
    completedEmergencies: int
    cancelledEmergencies: int
    activeEmergencies: int
    currentSession: Optional[str] = None
    totalTimeSaved: float
    successRate: float
    corridorStats: Dict[str, Any]


class CancelRequest(BaseModel):
    """Request to cancel emergency"""
    reason: str = "Manual cancellation"


# ============================================
# Global component references
# ============================================

_emergency_tracker: Optional[EmergencyTracker] = None
_pathfinder: Optional[EmergencyPathfinder] = None
_corridor_manager: Optional[GreenCorridorManager] = None


def set_emergency_components(
    tracker: EmergencyTracker,
    pathfinder: EmergencyPathfinder,
    corridor_manager: GreenCorridorManager
):
    """Set emergency component references for API routes"""
    global _emergency_tracker, _pathfinder, _corridor_manager
    _emergency_tracker = tracker
    _pathfinder = pathfinder
    _corridor_manager = corridor_manager


def _get_tracker() -> EmergencyTracker:
    """Get emergency tracker, falling back to global"""
    global _emergency_tracker
    if _emergency_tracker:
        return _emergency_tracker
    tracker = get_emergency_tracker()
    if not tracker:
        raise HTTPException(status_code=503, detail="Emergency system not initialized")
    return tracker


def _get_pathfinder() -> EmergencyPathfinder:
    """Get pathfinder, falling back to global"""
    global _pathfinder
    if _pathfinder:
        return _pathfinder
    pathfinder = get_emergency_pathfinder()
    if not pathfinder:
        raise HTTPException(status_code=503, detail="Pathfinder not initialized")
    return pathfinder


def _get_corridor_manager() -> GreenCorridorManager:
    """Get corridor manager, falling back to global"""
    global _corridor_manager
    if _corridor_manager:
        return _corridor_manager
    manager = get_corridor_manager()
    if not manager:
        raise HTTPException(status_code=503, detail="Corridor manager not initialized")
    return manager


# ============================================
# Endpoints
# ============================================

@router.post("/trigger", response_model=EmergencyTriggerResponse)
async def trigger_emergency(request: EmergencyTriggerRequest):
    """
    Trigger emergency vehicle scenario
    
    Creates an ambulance at the spawn point and calculates
    the optimal green corridor to the destination.
    
    The system will:
    1. Spawn emergency vehicle at spawn junction
    2. Calculate shortest path using A* algorithm
    3. Preemptively turn signals green along route
    4. Track progress and update signals dynamically
    5. Transition system to EMERGENCY mode
    
    Response time: < 5 seconds
    
    Example:
    ```
    curl -X POST http://localhost:8000/api/emergency/trigger \\
      -H "Content-Type: application/json" \\
      -d '{"spawnPoint":"J-0","destination":"J-8","vehicleType":"AMBULANCE"}'
    ```
    """
    tracker = _get_tracker()
    pathfinder = _get_pathfinder()
    corridor_manager = _get_corridor_manager()
    
    try:
        # Parse emergency type
        try:
            emergency_type = EmergencyType[request.vehicleType.upper()]
        except KeyError:
            emergency_type = EmergencyType.AMBULANCE
        
        # Activate emergency tracking
        session_id = tracker.activate_emergency(
            spawn_junction=request.spawnPoint,
            destination_junction=request.destination,
            emergency_type=emergency_type,
            vehicle_id=request.vehicleId,
            number_plate=request.numberPlate
        )
        
        # Get session
        session = tracker.get_session(session_id)
        if not session:
            raise HTTPException(status_code=500, detail="Failed to create emergency session")
        
        # Activate green corridor
        await corridor_manager.activate_corridor(session_id)
        
        # Get updated session with route
        session = tracker.get_session(session_id)
        
        return EmergencyTriggerResponse(
            status="ACTIVATED",
            sessionId=session_id,
            vehicleId=session.vehicle.vehicle_id,
            numberPlate=session.vehicle.number_plate,
            corridorPath=session.calculated_route,
            roadPath=corridor_manager.active_corridor.road_path if corridor_manager.active_corridor else [],
            estimatedTime=session.estimated_time,
            distance=session.total_distance,
            activatedAt=session.activated_at,
            destination=request.destination
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to trigger emergency: {str(e)}")


@router.get("/status", response_model=EmergencyStatusResponse)
async def get_emergency_status():
    """
    Get current emergency status
    
    Returns whether an emergency is active and its progress.
    
    Response time target: < 100ms
    """
    tracker = _get_tracker()
    corridor_manager = _get_corridor_manager()
    
    # Get active emergency
    session = tracker.get_active_emergency()
    
    if not session:
        return EmergencyStatusResponse(
            active=False,
            corridorActive=False
        )
    
    # Get progress
    progress = tracker.get_progress(session.session_id)
    
    # Get corridor status
    corridor_status = corridor_manager.get_corridor_status()
    
    return EmergencyStatusResponse(
        active=True,
        sessionId=session.session_id,
        vehicleId=session.vehicle.vehicle_id,
        vehicleType=session.vehicle.type.value,
        numberPlate=session.vehicle.number_plate,
        status=session.status.value,
        corridorPath=session.calculated_route,
        roadPath=corridor_status.get('roadPath', []) if corridor_status else [],
        currentJunction=progress.get('currentJunction'),
        progress=progress.get('progress', 0),
        estimatedArrival=progress.get('estimatedArrival'),
        activatedAt=session.activated_at,
        corridorActive=corridor_manager.is_corridor_active(),
        corridor=corridor_status
    )


@router.post("/cancel")
async def cancel_emergency(
    session_id: str = Query(None, description="Session ID to cancel"),
    request: Optional[CancelRequest] = None
):
    """
    Cancel active emergency
    
    Ends the emergency scenario and restores normal signal operations.
    
    Query params:
        session_id: Optional session ID (cancels current if not provided)
    
    Body (optional):
        reason: Reason for cancellation
    """
    tracker = _get_tracker()
    corridor_manager = _get_corridor_manager()
    
    # Get session to cancel
    if session_id:
        session = tracker.get_session(session_id)
    else:
        session = tracker.get_active_emergency()
    
    if not session:
        raise HTTPException(status_code=404, detail="No active emergency to cancel")
    
    session_id = session.session_id
    reason = request.reason if request else "Manual cancellation"
    
    # Cancel emergency tracking
    tracker.cancel_emergency(session_id, reason)
    
    # Deactivate corridor
    await corridor_manager.deactivate_corridor()
    
    return {
        "status": "cancelled",
        "sessionId": session_id,
        "reason": reason,
        "timestamp": time.time()
    }


@router.post("/clear")
async def clear_emergency():
    """
    Clear emergency mode (alias for cancel)
    
    Manually ends the emergency scenario and restores
    normal signal operations.
    """
    return await cancel_emergency()


@router.get("/corridor", response_model=Optional[CorridorResponse])
async def get_active_corridor():
    """
    Get active green corridor details
    
    Returns the currently active corridor with all
    affected junctions and their signal states.
    """
    tracker = _get_tracker()
    corridor_manager = _get_corridor_manager()
    
    corridor_status = corridor_manager.get_corridor_status()
    
    if not corridor_status:
        return None
    
    # Get session for vehicle ID
    session = tracker.get_session(corridor_status.get('sessionId'))
    vehicle_id = session.vehicle.vehicle_id if session else 'unknown'
    
    return CorridorResponse(
        sessionId=corridor_status.get('sessionId'),
        vehicleId=vehicle_id,
        junctionPath=corridor_status.get('junctionPath', []),
        roadPath=corridor_status.get('roadPath', []),
        currentJunctionIndex=corridor_status.get('currentJunctionIndex', 0),
        junctionCount=corridor_status.get('junctionCount', 0),
        activatedAt=corridor_status.get('activatedAt', 0),
        signalOverrides=corridor_status.get('signalOverrides', {}),
        status="ACTIVE"
    )


@router.get("/statistics", response_model=EmergencyStatisticsResponse)
async def get_emergency_statistics():
    """
    Get emergency system statistics
    
    Returns metrics on emergency performance.
    """
    tracker = _get_tracker()
    corridor_manager = _get_corridor_manager()
    
    tracker_stats = tracker.get_statistics()
    corridor_stats = corridor_manager.get_statistics()
    
    return EmergencyStatisticsResponse(
        totalEmergencies=tracker_stats.get('totalEmergencies', 0),
        completedEmergencies=tracker_stats.get('completedEmergencies', 0),
        cancelledEmergencies=tracker_stats.get('cancelledEmergencies', 0),
        activeEmergencies=tracker_stats.get('activeEmergencies', 0),
        currentSession=tracker_stats.get('currentSession'),
        totalTimeSaved=tracker_stats.get('totalTimeSaved', 0),
        successRate=tracker_stats.get('successRate', 0),
        corridorStats=corridor_stats
    )


@router.get("/history")
async def get_emergency_history(limit: int = Query(20, ge=1, le=100)):
    """
    Get recent emergency events
    
    Returns history of recent emergency triggers for analysis.
    
    Query params:
        limit: Maximum number of events to return (default: 20)
    """
    tracker = _get_tracker()
    
    history = tracker.get_history(limit=limit)
    
    return {
        "events": history,
        "count": len(history),
        "limit": limit
    }


@router.post("/simulate")
async def simulate_emergency(
    spawn: str = Query(..., description="Spawn junction ID"),
    destination: str = Query(..., description="Destination junction ID"),
    dry_run: bool = Query(True, alias="dryRun", description="If true, don't actually trigger")
):
    """
    Simulate emergency corridor without actually triggering
    
    Useful for testing and visualization.
    If dryRun=False, actually triggers the emergency.
    
    Query params:
        spawn: Spawn junction ID
        destination: Destination junction ID
        dryRun: If true (default), only simulate without triggering
    """
    pathfinder = _get_pathfinder()
    
    # Calculate path
    path = pathfinder.find_path(spawn, destination)
    
    if not path:
        raise HTTPException(status_code=400, detail=f"No path found: {spawn} -> {destination}")
    
    # Get road segments
    roads = pathfinder.get_road_segments_in_path(path)
    
    # Calculate metrics
    distance = pathfinder.get_path_distance(path)
    estimated_time = pathfinder.estimate_travel_time(path, speed_kmh=60)
    
    result = {
        "simulated": True,
        "corridorPath": path,
        "roadPath": roads,
        "junctionCount": len(path),
        "distance": distance,
        "estimatedTime": estimated_time,
        "affectedJunctions": path,
        "dryRun": dry_run
    }
    
    if not dry_run:
        # Actually trigger the emergency
        request = EmergencyTriggerRequest(
            spawnPoint=spawn,
            destination=destination,
            vehicleType="AMBULANCE"
        )
        trigger_result = await trigger_emergency(request)
        result["triggered"] = True
        result["sessionId"] = trigger_result.sessionId
        result["vehicleId"] = trigger_result.vehicleId
    
    return result


@router.get("/path")
async def calculate_path(
    start: str = Query(..., description="Start junction ID"),
    end: str = Query(..., description="End junction ID")
):
    """
    Calculate path between two junctions
    
    Useful for testing pathfinding without triggering emergency.
    
    Query params:
        start: Starting junction ID
        end: Destination junction ID
    """
    pathfinder = _get_pathfinder()
    
    # Calculate path
    path = pathfinder.find_path(start, end)
    
    if not path:
        raise HTTPException(status_code=400, detail=f"No path found: {start} -> {end}")
    
    # Get road segments
    roads = pathfinder.get_road_segments_in_path(path)
    
    # Calculate metrics
    distance = pathfinder.get_path_distance(path)
    estimated_time = pathfinder.estimate_travel_time(path, speed_kmh=60)
    
    return {
        "path": path,
        "roads": roads,
        "junctionCount": len(path),
        "distance": distance,
        "estimatedTime": estimated_time
    }
