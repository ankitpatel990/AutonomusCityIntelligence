"""
Emergency Vehicle Models

Models for emergency vehicles and green corridor management.
"""

from pydantic import BaseModel, Field
from typing import Literal, Optional
from uuid import uuid4
import time

from .vehicle import Position


class EmergencyVehicle(BaseModel):
    """
    Emergency vehicle (ambulance, fire truck, police)
    
    Extended vehicle model with emergency-specific properties.
    """
    id: str = Field(default_factory=lambda: f"emv-{uuid4().hex[:8]}")
    type: Literal['ambulance', 'fire_truck', 'police'] = 'ambulance'
    number_plate: str
    
    # Position
    position: Position
    lat: Optional[float] = None           # GPS coordinates
    lon: Optional[float] = None
    
    # Route
    origin: str                           # Starting junction
    destination: str                      # Target junction (hospital, etc.)
    route: list[str] = Field(default_factory=list)  # Junction IDs
    current_route_index: int = 0
    
    # Status
    activated: bool = False
    activated_at: Optional[float] = None
    corridor_active: bool = False
    
    # ETA
    eta_seconds: Optional[float] = None   # Estimated time to destination
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "emv-abc12345",
                "type": "ambulance",
                "number_plate": "GJ18AMB001",
                "position": {"x": 200, "y": 300},
                "origin": "J-1",
                "destination": "J-9",
                "route": ["J-1", "J-2", "J-5", "J-8", "J-9"],
                "activated": True,
                "corridor_active": True
            }
        }


class EmergencyCorridor(BaseModel):
    """
    Green corridor for emergency vehicle
    
    Represents the active corridor with affected signals.
    """
    id: str = Field(default_factory=lambda: f"cor-{uuid4().hex[:8]}")
    vehicle_id: str
    
    path: list[str]                       # Junction IDs in corridor
    affected_junctions: list[str]         # Junctions with signal override
    
    # Signal overrides: junction_id -> direction that should be GREEN
    signal_overrides: dict[str, str] = Field(default_factory=dict)
    
    activated_at: float = Field(default_factory=time.time)
    estimated_clear_time: Optional[float] = None
    
    status: Literal['ACTIVE', 'COMPLETED', 'CANCELLED'] = 'ACTIVE'
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "cor-xyz789",
                "vehicle_id": "emv-abc123",
                "path": ["J-1", "J-2", "J-5", "J-8", "J-9"],
                "affected_junctions": ["J-2", "J-5", "J-8"],
                "signal_overrides": {
                    "J-2": "east",
                    "J-5": "south",
                    "J-8": "south"
                },
                "status": "ACTIVE"
            }
        }


class EmergencyRequest(BaseModel):
    """Request to trigger emergency vehicle"""
    spawn_junction: str
    destination: str
    vehicle_type: Literal['ambulance', 'fire_truck', 'police'] = 'ambulance'


class EmergencyStatus(BaseModel):
    """Current emergency system status"""
    active_emergencies: int
    active_corridors: int
    emergency_vehicles: list[str]         # Vehicle IDs
    affected_junctions: list[str]         # Junctions in emergency mode


class CorridorCalculation(BaseModel):
    """Result of corridor path calculation"""
    origin: str
    destination: str
    path: list[str]
    distance: float                       # Total distance
    estimated_time: float                 # Estimated travel time in seconds
    junctions_to_clear: list[str]         # Junctions needing signal override

