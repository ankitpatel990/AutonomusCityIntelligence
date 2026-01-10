"""
Traffic Control Models

Models for traffic data source management, manual overrides,
and map area configuration.
"""

from pydantic import BaseModel, Field
from typing import Literal, Optional
from enum import Enum
import time

from .coordinates import MapBounds


class TrafficDataMode(str, Enum):
    """Traffic data source modes"""
    LIVE_API = "LIVE_API"                 # Use live API data only
    SIMULATION = "SIMULATION"             # Use simulation data only
    HYBRID = "HYBRID"                     # Combine live API with simulation
    MANUAL = "MANUAL"                     # Manual control mode


class TrafficDataSource(BaseModel):
    """
    Traffic data source configuration
    
    Tracks which data source is active and API status.
    """
    mode: TrafficDataMode = TrafficDataMode.SIMULATION
    api_provider: Optional[Literal['tomtom', 'google', 'here']] = None
    api_key_configured: bool = False
    last_api_update: Optional[str] = None
    active_overrides: int = 0
    global_multiplier: float = 1.0        # Traffic volume multiplier
    cache_hit_rate: Optional[float] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "mode": "HYBRID",
                "api_provider": "tomtom",
                "api_key_configured": True,
                "last_api_update": "2026-01-10T10:30:00Z",
                "active_overrides": 2,
                "global_multiplier": 1.0,
                "cache_hit_rate": 0.85
            }
        }


class ManualTrafficOverride(BaseModel):
    """
    Manual traffic override for demo/testing
    
    Allows manually setting congestion level for specific roads.
    """
    id: str = Field(default_factory=lambda: f"override-{int(time.time())}")
    road_id: str
    congestion_level: Literal['LOW', 'MEDIUM', 'HIGH', 'JAM']
    duration: Optional[int] = None        # Duration in minutes (None = indefinite)
    expires_at: Optional[float] = None    # Unix timestamp
    reason: Optional[str] = None          # Reason for override
    created_at: float = Field(default_factory=time.time)
    created_by: str = "system"            # User or system that created override
    
    class Config:
        json_schema_extra = {
            "example": {
                "road_id": "R-1-2",
                "congestion_level": "HIGH",
                "duration": 30,
                "reason": "Demo: Simulating rush hour"
            }
        }
    
    @property
    def is_expired(self) -> bool:
        """Check if override has expired"""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at


class MapAreaMetadata(BaseModel):
    """Additional metadata for a map area"""
    area_km2: Optional[float] = None
    population: Optional[int] = None
    description: Optional[str] = None
    landmarks: list[str] = Field(default_factory=list)


class MapArea(BaseModel):
    """
    Map area configuration
    
    Represents a loadable map area with bounds and metadata.
    """
    id: str
    name: str
    type: Literal['PREDEFINED', 'CUSTOM']
    
    bounds: MapBounds
    
    junction_count: int = 0
    road_count: int = 0
    
    loaded_at: Optional[str] = None
    cached: bool = False
    
    metadata: Optional[MapAreaMetadata] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "sector-5",
                "name": "Sector 5, Gandhinagar",
                "type": "PREDEFINED",
                "bounds": {
                    "north": 23.2300,
                    "south": 23.2100,
                    "east": 72.6500,
                    "west": 72.6200
                },
                "junction_count": 12,
                "road_count": 18,
                "cached": True
            }
        }


# Pre-defined map areas
PREDEFINED_MAP_AREAS = [
    MapArea(
        id="sector-1-5",
        name="Sectors 1-5",
        type="PREDEFINED",
        bounds=MapBounds(
            north=23.2400,
            south=23.2000,
            east=72.6600,
            west=72.6100
        ),
        metadata=MapAreaMetadata(
            description="Central Gandhinagar Sectors",
            area_km2=12.5
        )
    ),
    MapArea(
        id="gift-city",
        name="GIFT City",
        type="PREDEFINED",
        bounds=MapBounds(
            north=23.1700,
            south=23.1500,
            east=72.7000,
            west=72.6700
        ),
        metadata=MapAreaMetadata(
            description="Gujarat International Finance Tec-City",
            area_km2=3.5
        )
    ),
    MapArea(
        id="capitol-complex",
        name="Capitol Complex",
        type="PREDEFINED",
        bounds=MapBounds(
            north=23.2200,
            south=23.2050,
            east=72.6400,
            west=72.6200
        ),
        metadata=MapAreaMetadata(
            description="Government Administrative Area",
            area_km2=2.0
        )
    )
]


class TrafficModeChangeRequest(BaseModel):
    """Request to change traffic data mode"""
    mode: TrafficDataMode
    api_provider: Optional[Literal['tomtom', 'google', 'here']] = None


class LoadMapAreaRequest(BaseModel):
    """Request to load a map area"""
    area_id: Optional[str] = None         # For predefined areas
    place_name: Optional[str] = None      # For custom areas by name
    bounds: Optional[MapBounds] = None    # For custom areas by bounds

