"""
Vehicle Data Models

Core vehicle model for the traffic simulation system.
Includes both simulated and live API vehicle representations.
"""

from pydantic import BaseModel, Field
from typing import Literal, Optional
from uuid import uuid4
import time


class Position(BaseModel):
    """2D position in canvas coordinates"""
    x: float
    y: float
    
    class Config:
        json_schema_extra = {
            "example": {"x": 100.0, "y": 200.0}
        }


class Vehicle(BaseModel):
    """
    Core vehicle data model
    
    Represents any vehicle in the simulation including cars, bikes, and ambulances.
    Tracks position, movement, route, and violation status.
    """
    # Identity
    id: str = Field(default_factory=lambda: f"v-{uuid4().hex[:8]}")
    number_plate: str
    type: Literal['car', 'bike', 'ambulance']
    
    # Position & Movement
    position: Position
    speed: float = 0.0                    # km/h
    acceleration: float = 0.0             # m/s^2
    heading: float = 0.0                  # degrees 0-360
    
    # Route
    current_road: Optional[str] = None
    current_junction: Optional[str] = None
    destination: str
    path: list[str] = Field(default_factory=list)
    path_index: int = 0
    
    # State
    is_emergency: bool = False
    is_violating: bool = False
    waiting_time: float = 0.0             # seconds waiting at signal
    
    # Timestamps
    spawn_time: float = Field(default_factory=time.time)
    last_update: float = Field(default_factory=time.time)
    
    # GPS Coordinates (for real map mode)
    lat: Optional[float] = None
    lon: Optional[float] = None
    
    # Source tracking
    source: Optional[Literal['SIMULATION', 'LIVE_TRAFFIC_API']] = 'SIMULATION'
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "v-abc12345",
                "number_plate": "GJ18AB1234",
                "type": "car",
                "position": {"x": 100.0, "y": 200.0},
                "speed": 30.0,
                "heading": 90.0,
                "destination": "J-9",
                "path": ["J-1", "J-2", "J-5", "J-8", "J-9"],
                "is_emergency": False
            }
        }
    
    def update_position(self, new_x: float, new_y: float):
        """Update vehicle position and timestamp"""
        self.position.x = new_x
        self.position.y = new_y
        self.last_update = time.time()
    
    def increment_waiting_time(self, delta: float):
        """Increment waiting time when stopped at signal"""
        self.waiting_time += delta


class VehicleSpawnRequest(BaseModel):
    """Request model for spawning a new vehicle"""
    type: Literal['car', 'bike', 'ambulance'] = 'car'
    spawn_junction: str
    destination: str
    number_plate: Optional[str] = None
    is_emergency: bool = False


class VehicleUpdate(BaseModel):
    """Partial update for vehicle state"""
    position: Optional[Position] = None
    speed: Optional[float] = None
    heading: Optional[float] = None
    current_road: Optional[str] = None
    current_junction: Optional[str] = None
    is_violating: Optional[bool] = None

