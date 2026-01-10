"""
Real Map Models (OpenStreetMap)

Models for real-world geographic data from OpenStreetMap.
Extends the base junction and road models with GPS coordinates.
"""

from pydantic import BaseModel, Field
from typing import Optional
import time

from .junction import JunctionSignals, JunctionMetrics, create_default_signals
from .road import RoadTraffic
from .live_traffic import LiveTrafficData


class RealJunction(BaseModel):
    """
    Real OSM junction with GPS coordinates
    
    Extends the base Junction model with real-world location data.
    """
    id: str
    osm_id: int                           # OpenStreetMap node ID
    
    # GPS Coordinates
    lat: float
    lon: float
    
    # Canvas Coordinates (calculated from GPS)
    x: float = 0
    y: float = 0
    
    # Metadata from OSM
    name: Optional[str] = None
    landmark: Optional[str] = None        # Nearby landmark
    address: Optional[str] = None
    intersection_type: Optional[str] = None  # 'signalized', 'roundabout', etc.
    
    # Traffic signals
    signals: JunctionSignals = Field(default_factory=lambda: create_default_signals('north'))
    connected_roads: list[str] = Field(default_factory=list)
    metrics: JunctionMetrics = Field(default_factory=JunctionMetrics)
    
    last_signal_change: float = Field(default_factory=time.time)
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "J-OSM-123456",
                "osm_id": 123456789,
                "lat": 23.2156,
                "lon": 72.6369,
                "x": 450,
                "y": 320,
                "name": "Sector 5 Circle",
                "connected_roads": ["R-1", "R-2", "R-3", "R-4"]
            }
        }


class RealRoad(BaseModel):
    """
    Real OSM road with GPS coordinates
    
    Extends the base RoadSegment model with real-world data.
    """
    id: str
    osm_id: str                           # OpenStreetMap way ID
    
    # Junction connections
    start_junction_id: str
    end_junction_id: str
    
    # GPS Coordinates
    start_lat: float
    start_lon: float
    end_lat: float
    end_lon: float
    
    # Canvas Coordinates (calculated from GPS)
    start_x: float = 0
    start_y: float = 0
    end_x: float = 0
    end_y: float = 0
    
    # OSM Metadata
    name: str = "Unknown Road"
    length: float = 100.0                 # meters
    max_speed: float = 50.0               # km/h
    lanes: int = 2
    road_type: Optional[str] = None       # 'primary', 'secondary', 'residential'
    surface: Optional[str] = None         # 'asphalt', 'concrete'
    oneway: bool = False
    
    # Traffic state
    traffic: RoadTraffic = Field(default_factory=RoadTraffic)
    live_traffic: Optional[LiveTrafficData] = None
    
    last_update: float = Field(default_factory=time.time)
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "R-OSM-987654",
                "osm_id": "987654321",
                "start_junction_id": "J-OSM-123456",
                "end_junction_id": "J-OSM-234567",
                "start_lat": 23.2156,
                "start_lon": 72.6369,
                "end_lat": 23.2189,
                "end_lon": 72.6401,
                "name": "GH Road",
                "length": 450.0,
                "max_speed": 50.0,
                "lanes": 4,
                "road_type": "primary"
            }
        }


class OSMLoadResult(BaseModel):
    """Result of loading OSM data for an area"""
    area_id: str
    area_name: str
    
    junctions: list[RealJunction]
    roads: list[RealRoad]
    
    bounds_north: float
    bounds_south: float
    bounds_east: float
    bounds_west: float
    
    junction_count: int
    road_count: int
    
    load_time_ms: float
    cached: bool = False
    
    class Config:
        json_schema_extra = {
            "example": {
                "area_id": "sector-5",
                "area_name": "Sector 5, Gandhinagar",
                "junction_count": 15,
                "road_count": 22,
                "load_time_ms": 1250.5,
                "cached": False
            }
        }


class OSMNodeData(BaseModel):
    """Raw OSM node data (for parsing)"""
    id: int
    lat: float
    lon: float
    tags: dict = Field(default_factory=dict)


class OSMWayData(BaseModel):
    """Raw OSM way data (for parsing)"""
    id: int
    nodes: list[int]
    tags: dict = Field(default_factory=dict)
    
    @property
    def name(self) -> str:
        return self.tags.get('name', f'Way {self.id}')
    
    @property
    def max_speed(self) -> float:
        speed_str = self.tags.get('maxspeed', '50')
        try:
            return float(speed_str.replace(' km/h', '').replace(' mph', ''))
        except ValueError:
            return 50.0
    
    @property
    def lanes(self) -> int:
        try:
            return int(self.tags.get('lanes', '2'))
        except ValueError:
            return 2
    
    @property
    def road_type(self) -> str:
        return self.tags.get('highway', 'unclassified')

