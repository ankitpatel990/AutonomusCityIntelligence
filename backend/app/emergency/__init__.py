"""
Emergency Green Corridor System

Implements FRD-07: Emergency vehicle priority and green corridor management.

Components:
- EmergencyTracker: Track emergency vehicles and sessions
- EmergencyPathfinder: A* pathfinding for route calculation
- GreenCorridorManager: Signal control for green corridor
"""

from .emergency_tracker import (
    EmergencyTracker,
    EmergencyVehicle,
    EmergencySession,
    EmergencyType,
    EmergencyStatus,
    get_emergency_tracker,
    init_emergency_tracker,
)

from .pathfinder import (
    EmergencyPathfinder,
    get_emergency_pathfinder,
    init_emergency_pathfinder,
)

from .corridor_manager import (
    GreenCorridorManager,
    ActiveCorridor,
    get_corridor_manager,
    init_corridor_manager,
)


__all__ = [
    # Tracker
    "EmergencyTracker",
    "EmergencyVehicle",
    "EmergencySession",
    "EmergencyType",
    "EmergencyStatus",
    "get_emergency_tracker",
    "init_emergency_tracker",
    
    # Pathfinder
    "EmergencyPathfinder",
    "get_emergency_pathfinder",
    "init_emergency_pathfinder",
    
    # Corridor Manager
    "GreenCorridorManager",
    "ActiveCorridor",
    "get_corridor_manager",
    "init_corridor_manager",
]
