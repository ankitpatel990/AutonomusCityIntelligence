"""
Simulation Routes - Traffic simulation control endpoints

Endpoints:
- POST /api/simulation/start - Start simulation
- POST /api/simulation/stop - Stop simulation
- POST /api/simulation/pause - Pause simulation
- POST /api/simulation/resume - Resume simulation
- POST /api/simulation/reset - Reset to initial state
- POST /api/simulation/speed - Set speed multiplier
- GET /api/simulation/status - Get simulation status
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Literal, Dict, Any
import time

from app.simulation import get_simulation_manager

router = APIRouter(prefix="/api/simulation", tags=["simulation"])


# ============================================
# Request/Response Models
# ============================================

class SimulationResponse(BaseModel):
    """Standard simulation response"""
    status: str
    timestamp: float


class SpeedRequest(BaseModel):
    """Request body for setting simulation speed"""
    multiplier: Literal[1, 5, 10] = Field(
        default=1,
        description="Speed multiplier: 1x (real-time), 5x, or 10x"
    )


class SimulationStatusResponse(BaseModel):
    """Simulation status response"""
    running: bool
    paused: bool
    currentTime: float
    timeMultiplier: int
    totalVehicles: int
    vehiclesSpawned: int
    vehiclesReached: int
    startTime: float


# ============================================
# Endpoints
# ============================================

@router.post("/start", response_model=SimulationResponse)
async def start_simulation():
    """
    Start the traffic simulation
    
    Begins spawning vehicles, running physics updates,
    and processing traffic flow.
    """
    sim = get_simulation_manager()
    sim.start()
    
    return SimulationResponse(
        status="started",
        timestamp=time.time()
    )


@router.post("/stop", response_model=SimulationResponse)
async def stop_simulation():
    """
    Stop the traffic simulation
    
    Stops all simulation activity. Use /reset to clear state.
    """
    sim = get_simulation_manager()
    sim.stop()
    
    return SimulationResponse(
        status="stopped",
        timestamp=time.time()
    )


@router.post("/pause", response_model=SimulationResponse)
async def pause_simulation():
    """
    Pause the simulation
    
    Freezes all vehicle movement and signal changes.
    Use /resume to continue.
    """
    sim = get_simulation_manager()
    sim.pause()
    
    return SimulationResponse(
        status="paused",
        timestamp=time.time()
    )


@router.post("/resume", response_model=SimulationResponse)
async def resume_simulation():
    """
    Resume the simulation
    
    Continues from paused state.
    """
    sim = get_simulation_manager()
    sim.resume()
    
    return SimulationResponse(
        status="resumed",
        timestamp=time.time()
    )


@router.post("/reset", response_model=SimulationResponse)
async def reset_simulation():
    """
    Reset the simulation to initial state
    
    Clears all vehicles, resets signals, and restarts timing.
    WARNING: This will clear all in-memory simulation data.
    """
    sim = get_simulation_manager()
    sim.reset()
    
    return SimulationResponse(
        status="reset",
        timestamp=time.time()
    )


@router.post("/speed", response_model=Dict[str, Any])
async def set_simulation_speed(request: SpeedRequest):
    """
    Set simulation speed multiplier
    
    Allows running simulation faster for testing.
    - 1x: Real-time
    - 5x: 5 times faster
    - 10x: 10 times faster
    """
    sim = get_simulation_manager()
    sim.set_speed(request.multiplier)
    
    return {
        "status": "speed_set",
        "multiplier": request.multiplier,
        "timestamp": time.time()
    }


@router.get("/status", response_model=SimulationStatusResponse)
async def get_simulation_status():
    """
    Get current simulation status
    
    Returns running state, timing, and vehicle counts.
    
    Response time target: < 100ms
    """
    sim = get_simulation_manager()
    status = sim.get_status()
    
    return SimulationStatusResponse(
        running=status["running"],
        paused=status["paused"],
        currentTime=status["currentTime"],
        timeMultiplier=status["timeMultiplier"],
        totalVehicles=status["totalVehicles"],
        vehiclesSpawned=status["vehiclesSpawned"],
        vehiclesReached=status["vehiclesReached"],
        startTime=status["startTime"]
    )


@router.post("/spawn", response_model=Dict[str, Any])
async def spawn_vehicle(
    vehicle_type: Literal["car", "bike", "ambulance"] = "car",
    start_junction: str = None,
    end_junction: str = None
):
    """
    Manually spawn a vehicle
    
    Creates a new vehicle at the specified start junction
    with a route to the end junction.
    """
    sim = get_simulation_manager()
    
    try:
        vehicle = sim.spawn_vehicle(
            vehicle_type=vehicle_type,
            start_junction=start_junction,
            end_junction=end_junction
        )
        
        return {
            "status": "spawned",
            "vehicleId": vehicle.id,
            "type": vehicle.type,
            "numberPlate": vehicle.number_plate,
            "startJunction": vehicle.current_junction,
            "endJunction": vehicle.destination,
            "timestamp": time.time()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
