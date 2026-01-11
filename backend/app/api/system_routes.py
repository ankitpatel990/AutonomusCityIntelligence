"""
System Routes - Core system state endpoints

Endpoints:
- GET /api/state - Complete system state
- GET /api/vehicles - All active vehicles  
- GET /api/junctions - All junctions with signals
- GET /api/roads - All road segments
- GET /api/density - Traffic density data
"""

from fastapi import APIRouter, Query
from typing import Optional, List, Dict, Any
import time

from app.models import (
    Vehicle, Junction, RoadSegment, SystemState,
    TrafficDataSource, TrafficDataMode
)
from app.models.junction import create_default_signals, SignalColor
from app.simulation import get_simulation_manager

router = APIRouter(prefix="/api", tags=["system"])

# Hardcoded junctions for Gandhinagar area
HARDCODED_JUNCTIONS = [
    {"id": "J-1", "lat": 23.207225, "lon": 72.617206, "name": "GH-2 Circle"},
    {"id": "J-2", "lat": 23.203569, "lon": 72.624094, "name": "GH-3 Circle"},
    {"id": "J-3", "lat": 23.201914, "lon": 72.632327, "name": "GH-4 Circle"},
    {"id": "J-4", "lat": 23.208244, "lon": 72.636048, "name": "GH-5 Circle"},
    {"id": "J-5", "lat": 23.211664, "lon": 72.629002, "name": "Central Junction"},
    {"id": "J-6", "lat": 23.215302, "lon": 72.622431, "name": "GH-6 Circle"},
    {"id": "J-7", "lat": 23.223669, "lon": 72.627419, "name": "Sachivalay Circle"},
    {"id": "J-8", "lat": 23.220104, "lon": 72.634228, "name": "Sector 22/28 Circle"},
    {"id": "J-9", "lat": 23.216482, "lon": 72.640956, "name": "Sector 16 Circle"},
]

# Junction lookup helper
_JUNCTION_MAP = {j["id"]: j for j in HARDCODED_JUNCTIONS}

def _create_road(road_id: str, start_jid: str, end_jid: str, name: str):
    """Helper to create a road between two junctions"""
    start = _JUNCTION_MAP[start_jid]
    end = _JUNCTION_MAP[end_jid]
    return {
        "id": road_id,
        "startJunction": start_jid,
        "endJunction": end_jid,
        "name": name,
        "startLat": start["lat"],
        "startLon": start["lon"],
        "endLat": end["lat"],
        "endLon": end["lon"],
        "geometry": {
            "startPos": {"x": start["lon"], "y": start["lat"]},
            "endPos": {"x": end["lon"], "y": end["lat"]},
            "length": 500,  # approximate length in meters
            "lanes": 2
        },
        "traffic": {
            "density": "LOW",
            "vehicleCount": 0,
            "avgSpeed": 40.0,
            "congestionLevel": "LOW",
            "densityScore": 0.2,
            "currentVehicles": [],
            "capacity": 50,
            "speedLimit": 50
        },
        "maxSpeed": 50,
        "roadType": "secondary",
        "oneway": False,
        "lastUpdate": time.time()
    }

# Hardcoded roads forming a 3x3 grid
# Grid layout:
#   J-7 --- J-8 --- J-9  (top row)
#    |       |       |
#   J-6 --- J-5 --- J-4  (middle row)
#    |       |       |
#   J-1 --- J-2 --- J-3  (bottom row)
HARDCODED_ROADS = [
    # Horizontal roads (bottom row)
    _create_road("R-1-2", "J-1", "J-2", "GH-2 to GH-3 Road"),
    _create_road("R-2-3", "J-2", "J-3", "GH-3 to GH-4 Road"),
    # Horizontal roads (middle row)
    _create_road("R-6-5", "J-6", "J-5", "GH-6 to Central Road"),
    _create_road("R-5-4", "J-5", "J-4", "Central to GH-5 Road"),
    # Horizontal roads (top row)
    _create_road("R-7-8", "J-7", "J-8", "Sachivalay to Sector 22/28 Road"),
    _create_road("R-8-9", "J-8", "J-9", "Sector 22/28 to Sector 16 Road"),
    # Vertical roads (left column)
    _create_road("R-1-6", "J-1", "J-6", "GH-2 to GH-6 Road"),
    _create_road("R-6-7", "J-6", "J-7", "GH-6 to Sachivalay Road"),
    # Vertical roads (middle column)
    _create_road("R-2-5", "J-2", "J-5", "GH-3 to Central Road"),
    _create_road("R-5-8", "J-5", "J-8", "Central to Sector 22/28 Road"),
    # Vertical roads (right column)
    _create_road("R-3-4", "J-3", "J-4", "GH-4 to GH-5 Road"),
    _create_road("R-4-9", "J-4", "J-9", "GH-5 to Sector 16 Road"),
]

# Validate hardcoded roads on module load
if len(HARDCODED_ROADS) == 0:
    print("[WARNING] HARDCODED_ROADS list is empty!")
else:
    print(f"[system_routes] Initialized {len(HARDCODED_ROADS)} hardcoded roads")


@router.get("/state", response_model=Dict[str, Any])
async def get_system_state():
    """
    Get complete system state
    
    Returns current mode, simulation state, agent status, 
    performance metrics, and data source configuration.
    
    Response time target: < 100ms
    """
    sim = get_simulation_manager()
    status = sim.get_status()
    
    return {
        "mode": "NORMAL",
        "simulation": {
            "time": status["currentTime"],
            "timeMultiplier": status["timeMultiplier"],
            "isPaused": status["paused"],
            "isRunning": status["running"],
            "startTime": status["startTime"]
        },
        "agent": {
            "status": "RUNNING" if status["running"] else "STOPPED",
            "strategy": "RL",
            "loopCount": 0,
            "lastDecisionTime": time.time(),
            "avgDecisionLatency": 0
        },
        "performance": {
            "fps": 60,
            "vehicleCount": status["totalVehicles"],
            "avgDensity": 35.5,
            "congestionPoints": 2,
            "throughput": status["vehiclesReached"]
        },
        "dataSource": {
            "mode": "SIMULATION",
            "apiKeyConfigured": False,
            "activeOverrides": 0,
            "globalMultiplier": 1.0
        }
    }


@router.get("/vehicles", response_model=List[Dict[str, Any]])
async def get_all_vehicles(
    type: Optional[str] = Query(None, description="Filter by vehicle type: car, bike, ambulance"),
    junction: Optional[str] = Query(None, description="Filter by junction ID")
):
    """
    Get all active vehicles
    
    Optionally filter by type or current junction.
    
    Response time target: < 100ms
    """
    sim = get_simulation_manager()
    vehicles = sim.get_vehicles(vehicle_type=type, junction=junction)
    
    return [
        {
            "id": v.id,
            "numberPlate": v.number_plate,
            "type": v.type,
            "position": {"x": v.position.x, "y": v.position.y},
            "speed": v.speed,
            "heading": v.heading,
            "currentRoad": v.current_road,
            "currentJunction": v.current_junction,
            "destination": v.destination,
            "path": v.path,
            "isEmergency": v.is_emergency,
            "isViolating": v.is_violating,
            "waitingTime": v.waiting_time,
            "spawnTime": v.spawn_time,
            "lastUpdate": v.last_update,
            "lat": v.lat,
            "lon": v.lon,
            "source": v.source
        }
        for v in vehicles
    ]


@router.get("/vehicles/{vehicle_id}", response_model=Dict[str, Any])
async def get_vehicle(vehicle_id: str):
    """Get specific vehicle by ID"""
    sim = get_simulation_manager()
    v = sim.get_vehicle(vehicle_id)
    
    if not v:
        return {
            "id": vehicle_id,
            "error": "Vehicle not found"
        }
    
    return {
        "id": v.id,
        "numberPlate": v.number_plate,
        "type": v.type,
        "position": {"x": v.position.x, "y": v.position.y},
        "speed": v.speed,
        "heading": v.heading,
        "currentRoad": v.current_road,
        "currentJunction": v.current_junction,
        "destination": v.destination,
        "path": v.path,
        "isEmergency": v.is_emergency,
        "isViolating": v.is_violating,
        "waitingTime": v.waiting_time,
        "spawnTime": v.spawn_time,
        "lastUpdate": v.last_update
    }


@router.get("/junctions", response_model=List[Dict[str, Any]])
async def get_all_junctions():
    """
    Get all junctions with current signal states
    
    Returns junction positions, signal states, connected roads, and metrics.
    
    Response time target: < 100ms
    """
    # Create default signals for each junction (alternating green directions)
    default_signals = create_default_signals('north')
    
    # Return hardcoded junctions with proper signal structure
    result = []
    for idx, j in enumerate(HARDCODED_JUNCTIONS):
        # Alternate green direction for variety
        green_dir = ['north', 'east', 'south', 'west'][idx % 4]
        signals = create_default_signals(green_dir)
        
        # Convert signals to dict format for JSON response
        signals_dict = {
            "north": {
                "current": signals.north.current.value,
                "duration": signals.north.duration,
                "lastChange": signals.north.last_change,
                "timeSinceGreen": signals.north.time_since_green
            },
            "east": {
                "current": signals.east.current.value,
                "duration": signals.east.duration,
                "lastChange": signals.east.last_change,
                "timeSinceGreen": signals.east.time_since_green
            },
            "south": {
                "current": signals.south.current.value,
                "duration": signals.south.duration,
                "lastChange": signals.south.last_change,
                "timeSinceGreen": signals.south.time_since_green
            },
            "west": {
                "current": signals.west.current.value,
                "duration": signals.west.duration,
                "lastChange": signals.west.last_change,
                "timeSinceGreen": signals.west.time_since_green
            }
        }
        
        result.append({
            "id": j["id"],
            "name": j["name"],
            "lat": j["lat"],
            "lon": j["lon"],
            "position": {"x": j["lon"], "y": j["lat"]},
            "signals": signals_dict,
            "connectedRoads": [],
            "metrics": {
                "vehicleCount": 0,
                "avgWaitTime": 0,
                "density": 0.0
            },
            "signalState": signals.get_green_direction() or "GREEN",
            "greenPhase": "NS",
            "phaseTime": 30,
            "vehicleCount": 0,
            "avgWaitTime": 0
        })
    
    return result


@router.get("/junctions/{junction_id}", response_model=Dict[str, Any])
async def get_junction(junction_id: str):
    """Get specific junction by ID"""
    # Look up from hardcoded junctions
    for idx, j in enumerate(HARDCODED_JUNCTIONS):
        if j["id"] == junction_id:
            # Create signals for this junction
            green_dir = ['north', 'east', 'south', 'west'][idx % 4]
            signals = create_default_signals(green_dir)
            
            # Convert signals to dict format
            signals_dict = {
                "north": {
                    "current": signals.north.current.value,
                    "duration": signals.north.duration,
                    "lastChange": signals.north.last_change,
                    "timeSinceGreen": signals.north.time_since_green
                },
                "east": {
                    "current": signals.east.current.value,
                    "duration": signals.east.duration,
                    "lastChange": signals.east.last_change,
                    "timeSinceGreen": signals.east.time_since_green
                },
                "south": {
                    "current": signals.south.current.value,
                    "duration": signals.south.duration,
                    "lastChange": signals.south.last_change,
                    "timeSinceGreen": signals.south.time_since_green
                },
                "west": {
                    "current": signals.west.current.value,
                    "duration": signals.west.duration,
                    "lastChange": signals.west.last_change,
                    "timeSinceGreen": signals.west.time_since_green
                }
            }
            
            return {
                "id": j["id"],
                "name": j["name"],
                "lat": j["lat"],
                "lon": j["lon"],
                "position": {"x": j["lon"], "y": j["lat"]},
                "signals": signals_dict,
                "connectedRoads": [],
                "metrics": {
                    "vehicleCount": 0,
                    "avgWaitTime": 0,
                    "density": 0.0
                },
                "signalState": signals.get_green_direction() or "GREEN",
                "greenPhase": "NS",
                "phaseTime": 30,
                "vehicleCount": 0,
                "avgWaitTime": 0
            }
    
    return {
        "id": junction_id,
        "error": "Junction not found"
    }


@router.get("/roads", response_model=List[Dict[str, Any]])
async def get_all_roads():
    """
    Get all road segments
    
    Returns road geometry, traffic state, and connected junctions.
    
    Response time target: < 100ms
    """
    print(f"[system_routes] /api/roads called, returning {len(HARDCODED_ROADS)} hardcoded roads")
    
    # Always return hardcoded roads only (single source of truth)
    # Filter out any demo roads from simulation
    import re
    try:
        sim = get_simulation_manager()
        sim_roads = sim.get_roads()
        # Only include simulation roads that match hardcoded format (R-X-Y)
        if sim_roads and len(sim_roads) > 0:
            hardcoded_format_roads = [r for r in sim_roads if re.match(r'^R-\d+-\d+$', r.get("id", ""))]
            # Use HARDCODED_ROADS as source of truth, only add simulation roads that match format
            all_roads = HARDCODED_ROADS.copy()
            existing_ids = {r["id"] for r in HARDCODED_ROADS}
            for road in hardcoded_format_roads:
                if road.get("id") not in existing_ids:
                    all_roads.append(road)
            print(f"[system_routes] Returning {len(all_roads)} roads ({len(HARDCODED_ROADS)} hardcoded + {len(all_roads) - len(HARDCODED_ROADS)} matching from sim)")
            return all_roads
    except Exception as e:
        # If simulation manager fails, return hardcoded roads
        print(f"[system_routes] Error getting roads from simulation: {e}, returning hardcoded roads")
    
    # Default: return hardcoded roads only
    print(f"[system_routes] Returning {len(HARDCODED_ROADS)} hardcoded roads")
    return HARDCODED_ROADS


@router.get("/roads/{road_id}", response_model=Dict[str, Any])
async def get_road(road_id: str):
    """Get specific road segment by ID"""
    sim = get_simulation_manager()
    road = sim.get_road(road_id)
    
    if not road:
        return {
            "id": road_id,
            "error": "Road not found"
        }
    
    return road


@router.get("/density", response_model=Dict[str, Any])
async def get_density_data():
    """
    Get current traffic density data
    
    Returns city-wide average and per-junction/road density scores.
    
    Response time target: < 100ms
    """
    sim = get_simulation_manager()
    roads = sim.get_roads()
    
    # Calculate densities using hardcoded junctions
    per_junction = {}
    for j in HARDCODED_JUNCTIONS:
        per_junction[j["id"]] = {
            "density": 0.3 + (hash(j["id"]) % 50) / 100,  # Mock density
            "vehicleCount": hash(j["id"]) % 10
        }
    
    per_road = {}
    for r in roads:
        per_road[r["id"]] = {
            "density": 0.2 + (hash(r["id"]) % 60) / 100,
            "vehicleCount": hash(r["id"]) % 15
        }
    
    return {
        "citywide": 0.42,
        "perJunction": per_junction,
        "perRoad": per_road,
        "timestamp": time.time()
    }


@router.get("/density/roads", response_model=List[Dict[str, Any]])
async def get_road_densities():
    """Get density data for all roads"""
    sim = get_simulation_manager()
    roads = sim.get_roads()
    
    return [
        {
            "roadId": r["id"],
            "densityScore": 0.2 + (hash(r["id"]) % 60) / 100,
            "classification": "MEDIUM" if hash(r["id"]) % 2 == 0 else "LOW",
            "vehicleCount": hash(r["id"]) % 15,
            "timestamp": time.time()
        }
        for r in roads
    ]


@router.get("/density/junctions", response_model=List[Dict[str, Any]])
async def get_junction_densities():
    """Get density data for all junctions"""
    return [
        {
            "junctionId": j["id"],
            "junctionName": j["name"],
            "densityScore": 0.3 + (hash(j["id"]) % 50) / 100,
            "classification": "MEDIUM" if hash(j["id"]) % 2 == 0 else "LOW",
            "vehicleCount": hash(j["id"]) % 10,
            "timestamp": time.time()
        }
        for j in HARDCODED_JUNCTIONS
    ]


@router.get("/density/road/{road_id}", response_model=Dict[str, Any])
async def get_road_density(road_id: str):
    """Get density data for specific road"""
    return {
        "roadId": road_id,
        "densityScore": 0.35,
        "classification": "MEDIUM",
        "vehicleCount": 5,
        "timestamp": time.time()
    }


@router.get("/density/history/{road_id}", response_model=Dict[str, Any])
async def get_density_history(
    road_id: str,
    duration: int = Query(300, description="History duration in seconds")
):
    """Get historical density data for a road"""
    return {
        "roadId": road_id,
        "duration": duration,
        "snapshots": [],
        "avgDensity": 0.35,
        "maxDensity": 0.65,
        "minDensity": 0.15
    }


@router.get("/density/export")
async def export_density_csv(
    duration: int = Query(600, description="Export duration in seconds")
):
    """Export density data as CSV"""
    from fastapi.responses import PlainTextResponse
    
    csv_content = "road_id,timestamp,density_score,classification,vehicle_count\n"
    
    return PlainTextResponse(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=density_export.csv"}
    )
