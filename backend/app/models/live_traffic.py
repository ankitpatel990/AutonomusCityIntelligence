"""
Live Traffic API Data Models

Models for handling real-time traffic data from external APIs
like TomTom, Google Maps, and HERE.
"""

from pydantic import BaseModel, Field
from typing import Literal, Optional
from datetime import datetime


class TrafficIncident(BaseModel):
    """Traffic incident from API"""
    type: str                             # 'ACCIDENT', 'CONSTRUCTION', 'ROAD_CLOSURE'
    description: str
    severity: str                         # 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
    
    class Config:
        json_schema_extra = {
            "example": {
                "type": "ACCIDENT",
                "description": "Minor collision blocking one lane",
                "severity": "MEDIUM"
            }
        }


class LiveTrafficData(BaseModel):
    """
    Live traffic data from external API
    
    Contains real-time traffic flow data for a road segment.
    Can come from TomTom, Google, or HERE APIs.
    """
    road_id: str
    
    # Traffic metrics from API
    current_speed: float                  # km/h - actual current speed
    free_flow_speed: float                # km/h - speed with no traffic
    congestion_level: Literal['LOW', 'MEDIUM', 'HIGH', 'JAM']
    confidence: float                     # 0-100 confidence percentage
    
    # Timing
    timestamp: str                        # ISO format timestamp
    expires_at: Optional[float] = None    # Unix timestamp when data expires
    
    # Source tracking
    source: Literal['API', 'SIMULATION', 'MANUAL', 'ADJUSTED']
    provider: Optional[Literal['tomtom', 'google', 'here']] = None
    
    # Additional data
    incidents: list[TrafficIncident] = Field(default_factory=list)
    road_closure: bool = False
    
    class Config:
        json_schema_extra = {
            "example": {
                "road_id": "R-1-2",
                "current_speed": 25.0,
                "free_flow_speed": 50.0,
                "congestion_level": "MEDIUM",
                "confidence": 85.0,
                "timestamp": "2026-01-10T10:30:00Z",
                "source": "API",
                "provider": "tomtom"
            }
        }
    
    @property
    def speed_ratio(self) -> float:
        """Get ratio of current speed to free flow speed"""
        if self.free_flow_speed == 0:
            return 1.0
        return self.current_speed / self.free_flow_speed
    
    @property
    def is_expired(self) -> bool:
        """Check if this data has expired"""
        if self.expires_at is None:
            return False
        import time
        return time.time() > self.expires_at
    
    @classmethod
    def calculate_congestion_level(cls, current_speed: float, free_flow_speed: float) -> str:
        """Calculate congestion level from speeds"""
        if free_flow_speed == 0:
            return 'JAM'
        
        ratio = current_speed / free_flow_speed
        
        if ratio > 0.8:
            return 'LOW'
        elif ratio > 0.5:
            return 'MEDIUM'
        elif ratio > 0.2:
            return 'HIGH'
        else:
            return 'JAM'


class TomTomFlowData(BaseModel):
    """
    Raw TomTom Traffic Flow API response structure
    
    Used to parse and convert TomTom API responses.
    """
    current_speed: float = Field(alias='currentSpeed')
    free_flow_speed: float = Field(alias='freeFlowSpeed')
    current_travel_time: Optional[int] = Field(None, alias='currentTravelTime')
    free_flow_travel_time: Optional[int] = Field(None, alias='freeFlowTravelTime')
    confidence: float = 0.5
    road_closure: bool = Field(False, alias='roadClosure')
    
    class Config:
        populate_by_name = True
    
    def to_live_traffic_data(self, road_id: str) -> LiveTrafficData:
        """Convert to our internal LiveTrafficData format"""
        return LiveTrafficData(
            road_id=road_id,
            current_speed=self.current_speed,
            free_flow_speed=self.free_flow_speed,
            congestion_level=LiveTrafficData.calculate_congestion_level(
                self.current_speed, self.free_flow_speed
            ),
            confidence=self.confidence * 100,
            timestamp=datetime.now().isoformat(),
            source='API',
            provider='tomtom',
            road_closure=self.road_closure
        )


class TrafficAPIConfig(BaseModel):
    """Configuration for traffic API integration"""
    provider: Literal['tomtom', 'google', 'here']
    api_key: str
    base_url: str
    rate_limit: int = 100                 # requests per minute
    cache_ttl: int = 60                   # seconds
    timeout: float = 5.0                  # seconds
    enabled: bool = True

