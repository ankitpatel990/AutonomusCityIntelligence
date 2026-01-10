"""
Road Segment Data Models

Models for road segments connecting junctions.
Includes traffic state, geometry, and density tracking.
"""

from pydantic import BaseModel, Field
from typing import Literal, Optional
import time

from .vehicle import Position


class RoadGeometry(BaseModel):
    """Physical geometry of a road segment"""
    start_pos: Position
    end_pos: Position
    length: float                         # length in pixels (or meters for real roads)
    lanes: int = 2                        # number of lanes
    
    def get_direction_vector(self) -> tuple[float, float]:
        """Get normalized direction vector from start to end"""
        dx = self.end_pos.x - self.start_pos.x
        dy = self.end_pos.y - self.start_pos.y
        mag = (dx**2 + dy**2) ** 0.5
        if mag == 0:
            return (0, 0)
        return (dx / mag, dy / mag)


class RoadTraffic(BaseModel):
    """Traffic state of a road segment"""
    current_vehicles: list[str] = Field(default_factory=list)  # Vehicle IDs
    capacity: int = 20                    # Max vehicles before congestion
    density: Literal['LOW', 'MEDIUM', 'HIGH'] = 'LOW'
    density_score: float = 0.0            # 0-100 score
    speed_limit: float = 50.0             # km/h
    
    @property
    def vehicle_count(self) -> int:
        """Get current number of vehicles on road"""
        return len(self.current_vehicles)
    
    @property
    def congestion_ratio(self) -> float:
        """Get congestion ratio (0-1)"""
        if self.capacity == 0:
            return 0
        return min(1.0, self.vehicle_count / self.capacity)


class RoadSegment(BaseModel):
    """
    Road segment connecting two junctions
    
    Represents a bidirectional road with traffic state tracking.
    """
    id: str
    start_junction: str                   # Junction ID
    end_junction: str                     # Junction ID
    
    geometry: RoadGeometry
    traffic: RoadTraffic = Field(default_factory=RoadTraffic)
    
    last_update: float = Field(default_factory=time.time)
    
    # For real map roads
    osm_id: Optional[str] = None
    name: Optional[str] = None
    road_type: Optional[str] = None       # e.g., 'primary', 'secondary'
    
    # GPS coordinates (for real map mode)
    start_lat: Optional[float] = None
    start_lon: Optional[float] = None
    end_lat: Optional[float] = None
    end_lon: Optional[float] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "R-1-2",
                "start_junction": "J-1",
                "end_junction": "J-2",
                "geometry": {
                    "start_pos": {"x": 200, "y": 200},
                    "end_pos": {"x": 400, "y": 200},
                    "length": 200,
                    "lanes": 2
                }
            }
        }
    
    def add_vehicle(self, vehicle_id: str):
        """Add a vehicle to this road"""
        if vehicle_id not in self.traffic.current_vehicles:
            self.traffic.current_vehicles.append(vehicle_id)
            self._update_density()
    
    def remove_vehicle(self, vehicle_id: str):
        """Remove a vehicle from this road"""
        if vehicle_id in self.traffic.current_vehicles:
            self.traffic.current_vehicles.remove(vehicle_id)
            self._update_density()
    
    def _update_density(self):
        """Update density classification based on vehicle count"""
        ratio = self.traffic.congestion_ratio
        self.traffic.density_score = ratio * 100
        
        if ratio < 0.4:
            self.traffic.density = 'LOW'
        elif ratio < 0.7:
            self.traffic.density = 'MEDIUM'
        else:
            self.traffic.density = 'HIGH'
        
        self.last_update = time.time()


class RealRoad(BaseModel):
    """
    Real OSM road with GPS coordinates
    
    Extended road model for real map integration.
    Includes both GPS and canvas coordinates.
    """
    id: str
    osm_id: str
    
    start_junction_id: str
    end_junction_id: str
    
    # GPS coordinates
    start_lat: float
    start_lon: float
    end_lat: float
    end_lon: float
    
    # Canvas coordinates (calculated from GPS)
    start_x: float = 0
    start_y: float = 0
    end_x: float = 0
    end_y: float = 0
    
    # OSM metadata
    name: str = "Unknown Road"
    length: float = 100.0                 # meters
    max_speed: float = 50.0               # km/h
    lanes: int = 2
    road_type: Optional[str] = None       # 'primary', 'secondary', 'residential'
    
    # Traffic state
    traffic: RoadTraffic = Field(default_factory=RoadTraffic)
    
    last_update: float = Field(default_factory=time.time)
    
    def to_road_segment(self) -> RoadSegment:
        """Convert to standard RoadSegment model"""
        return RoadSegment(
            id=self.id,
            start_junction=self.start_junction_id,
            end_junction=self.end_junction_id,
            geometry=RoadGeometry(
                start_pos=Position(x=self.start_x, y=self.start_y),
                end_pos=Position(x=self.end_x, y=self.end_y),
                length=self.length,
                lanes=self.lanes
            ),
            traffic=self.traffic,
            last_update=self.last_update,
            osm_id=self.osm_id,
            name=self.name,
            road_type=self.road_type,
            start_lat=self.start_lat,
            start_lon=self.start_lon,
            end_lat=self.end_lat,
            end_lon=self.end_lon
        )

