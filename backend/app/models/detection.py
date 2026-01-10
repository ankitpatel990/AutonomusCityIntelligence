"""
Detection Record Models

Models for vehicle detection at junctions.
Used for tracking vehicle movements and post-incident reconstruction.
"""

from pydantic import BaseModel, Field
from typing import Literal, Optional
from uuid import uuid4
import time


class DetectionRecord(BaseModel):
    """
    Vehicle detection at a junction
    
    Records each time a vehicle passes through a junction.
    Used for route reconstruction and traffic analysis.
    """
    id: str = Field(default_factory=lambda: f"det-{uuid4().hex[:8]}")
    
    # Vehicle info
    vehicle_id: str
    number_plate: str
    vehicle_type: Literal['car', 'bike', 'ambulance']
    
    # Location
    junction_id: str
    direction: Literal['N', 'E', 'S', 'W']  # Direction vehicle was heading
    
    # Movement
    incoming_road: str                    # Road vehicle came from
    outgoing_road: str                    # Road vehicle is going to
    
    # Metrics
    timestamp: float = Field(default_factory=time.time)
    speed: float = 0.0                    # Speed at detection point
    
    # GPS coordinates (for real map mode)
    lat: Optional[float] = None
    lon: Optional[float] = None
    junction_name: Optional[str] = None   # Human-readable junction name
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "det-abc12345",
                "vehicle_id": "v-xyz789",
                "number_plate": "GJ18AB1234",
                "vehicle_type": "car",
                "junction_id": "J-5",
                "direction": "E",
                "incoming_road": "R-4-5",
                "outgoing_road": "R-5-6",
                "speed": 35.5
            }
        }


class DetectionQuery(BaseModel):
    """Query parameters for detection records"""
    number_plate: Optional[str] = None
    junction_id: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    limit: int = 100
    offset: int = 0


class DetectionSummary(BaseModel):
    """Summary of detections for a time period"""
    total_detections: int
    unique_vehicles: int
    by_junction: dict[str, int]           # Junction ID -> count
    by_vehicle_type: dict[str, int]       # Vehicle type -> count
    avg_speed: float
    time_range_start: float
    time_range_end: float


class VehicleRoute(BaseModel):
    """Reconstructed route from detection records"""
    vehicle_id: str
    number_plate: str
    
    route: list[str]                      # Junction IDs in order
    route_names: list[str]                # Junction names (for real map)
    
    timestamps: list[float]               # Detection timestamps
    speeds: list[float]                   # Speeds at each point
    
    total_distance: Optional[float] = None  # Estimated distance
    total_time: float                     # Time from first to last detection
    avg_speed: float
    
    start_time: float
    end_time: float
    
    gps_points: Optional[list[tuple[float, float]]] = None  # (lat, lon) pairs

