"""
Junction and Signal Data Models

Models for traffic junctions, signal states, and signal control.
Supports both simulated grid junctions and real OSM junctions.
"""

from pydantic import BaseModel, Field
from typing import Literal, Optional
from enum import Enum
import time

from .vehicle import Position


class SignalColor(str, Enum):
    """Traffic signal colors"""
    RED = "RED"
    YELLOW = "YELLOW"
    GREEN = "GREEN"


class SignalState(BaseModel):
    """
    State of a single traffic signal
    
    Tracks the current color, time remaining, and fairness metrics.
    """
    current: SignalColor
    duration: float                       # seconds remaining in current state
    last_change: float                    # timestamp of last change
    time_since_green: float = 0.0         # seconds since last green (for fairness)
    
    class Config:
        json_schema_extra = {
            "example": {
                "current": "GREEN",
                "duration": 30.0,
                "last_change": 1704067200.0,
                "time_since_green": 0.0
            }
        }


class JunctionSignals(BaseModel):
    """
    All four signals at a junction
    
    Each direction (N, E, S, W) has its own signal state.
    """
    north: SignalState
    east: SignalState
    south: SignalState
    west: SignalState
    
    def get_green_direction(self) -> Optional[str]:
        """Get the direction with green signal, if any"""
        if self.north.current == SignalColor.GREEN:
            return "north"
        if self.east.current == SignalColor.GREEN:
            return "east"
        if self.south.current == SignalColor.GREEN:
            return "south"
        if self.west.current == SignalColor.GREEN:
            return "west"
        return None
    
    def get_all_states(self) -> dict[str, SignalColor]:
        """Get all signal states as a dictionary"""
        return {
            "north": self.north.current,
            "east": self.east.current,
            "south": self.south.current,
            "west": self.west.current
        }


class ConnectedRoads(BaseModel):
    """Roads connected to a junction in each direction"""
    north: Optional[str] = None
    east: Optional[str] = None
    south: Optional[str] = None
    west: Optional[str] = None
    
    def to_list(self) -> list[str]:
        """Get list of all connected road IDs"""
        roads = []
        if self.north:
            roads.append(self.north)
        if self.east:
            roads.append(self.east)
        if self.south:
            roads.append(self.south)
        if self.west:
            roads.append(self.west)
        return roads


class JunctionMetrics(BaseModel):
    """Real-time metrics for a junction"""
    vehicle_count: int = 0                # vehicles currently at junction
    avg_wait_time: float = 0.0            # average waiting time in seconds
    density: float = 0.0                  # density score 0-100
    throughput: float = 0.0               # vehicles passed per minute


class Junction(BaseModel):
    """
    Traffic junction with signals
    
    Represents a 4-way intersection with traffic signals.
    Can be either a simulated grid junction or a real OSM junction.
    """
    id: str
    position: Position
    
    signals: JunctionSignals
    connected_roads: ConnectedRoads
    metrics: JunctionMetrics = Field(default_factory=JunctionMetrics)
    
    last_signal_change: float = Field(default_factory=time.time)
    mode: Literal['NORMAL', 'EMERGENCY', 'MANUAL'] = 'NORMAL'
    
    # For real map junctions
    osm_id: Optional[int] = None
    name: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "J-1",
                "position": {"x": 200, "y": 200},
                "mode": "NORMAL"
            }
        }


class SignalChangeRequest(BaseModel):
    """Request to change a signal state"""
    junction_id: str
    direction: Literal['north', 'east', 'south', 'west']
    new_state: SignalColor
    duration: Optional[float] = None      # Override default duration
    reason: Optional[str] = None          # Reason for change (manual, RL, emergency)


class SignalOverride(BaseModel):
    """Manual signal override configuration"""
    junction_id: str
    direction: Literal['north', 'east', 'south', 'west']
    forced_state: SignalColor
    duration: float                       # How long to maintain override
    expires_at: float                     # Timestamp when override expires
    reason: str = "MANUAL_OVERRIDE"


def create_default_signals(green_direction: str = 'north') -> JunctionSignals:
    """
    Create default signal configuration
    
    One direction is GREEN, others are RED.
    """
    now = time.time()
    
    def make_state(is_green: bool) -> SignalState:
        return SignalState(
            current=SignalColor.GREEN if is_green else SignalColor.RED,
            duration=30.0 if is_green else 30.0,
            last_change=now,
            time_since_green=0.0 if is_green else 30.0
        )
    
    return JunctionSignals(
        north=make_state(green_direction == 'north'),
        east=make_state(green_direction == 'east'),
        south=make_state(green_direction == 'south'),
        west=make_state(green_direction == 'west')
    )

