"""
System State Models

Models for overall system state, agent status, and performance metrics.
"""

from pydantic import BaseModel, Field
from typing import Literal, Optional
import time

from .traffic_control import TrafficDataSource, TrafficDataMode


class SimulationState(BaseModel):
    """Current simulation state"""
    time: float = 0.0                     # Simulation time in seconds
    time_multiplier: int = 1              # 1x, 5x, 10x
    is_paused: bool = False
    is_running: bool = False
    start_time: float = 0.0               # Real-time start timestamp


class AgentState(BaseModel):
    """Autonomous agent state"""
    status: Literal['RUNNING', 'PAUSED', 'STOPPED'] = 'STOPPED'
    strategy: Literal['RL', 'RULE_BASED', 'MANUAL'] = 'RL'
    loop_count: int = 0                   # Total decision cycles
    last_decision_time: float = 0.0       # Timestamp of last decision
    avg_decision_latency: float = 0.0     # Average latency in ms


class PerformanceMetrics(BaseModel):
    """System performance metrics"""
    fps: float = 60.0                     # Simulation frames per second
    vehicle_count: int = 0
    avg_density: float = 0.0              # City-wide average density
    congestion_points: int = 0            # Number of HIGH/JAM roads
    throughput: float = 0.0               # Vehicles/minute reaching destination
    
    # Additional metrics
    avg_wait_time: float = 0.0            # Average waiting time at signals
    total_vehicles_spawned: int = 0
    vehicles_reached_destination: int = 0


class SystemMode(BaseModel):
    """Current system operating mode"""
    mode: Literal['NORMAL', 'EMERGENCY', 'INCIDENT', 'FAIL_SAFE', 'MANUAL'] = 'NORMAL'
    mode_since: float = Field(default_factory=time.time)
    mode_reason: Optional[str] = None


class SystemState(BaseModel):
    """
    Complete system state
    
    Aggregates all subsystem states for dashboard display.
    """
    # Core mode
    mode: Literal['NORMAL', 'EMERGENCY', 'INCIDENT', 'FAIL_SAFE', 'MANUAL'] = 'NORMAL'
    
    # Subsystem states
    simulation: SimulationState = Field(default_factory=SimulationState)
    agent: AgentState = Field(default_factory=AgentState)
    performance: PerformanceMetrics = Field(default_factory=PerformanceMetrics)
    
    # Traffic data source
    data_source: TrafficDataSource = Field(
        default_factory=lambda: TrafficDataSource(mode=TrafficDataMode.SIMULATION)
    )
    
    # Emergency status
    active_emergency: bool = False
    emergency_vehicle_id: Optional[str] = None
    
    # Live API stats
    api_data_age: Optional[float] = None  # Seconds since last API update
    live_roads_count: Optional[int] = None  # Roads with live data
    
    # Timestamp
    last_update: float = Field(default_factory=time.time)
    
    class Config:
        json_schema_extra = {
            "example": {
                "mode": "NORMAL",
                "simulation": {
                    "time": 3600.0,
                    "time_multiplier": 5,
                    "is_paused": False,
                    "is_running": True
                },
                "agent": {
                    "status": "RUNNING",
                    "strategy": "RL",
                    "loop_count": 1250,
                    "avg_decision_latency": 45.5
                },
                "performance": {
                    "fps": 60,
                    "vehicle_count": 85,
                    "avg_density": 42.5,
                    "congestion_points": 3
                },
                "active_emergency": False
            }
        }


class AgentLog(BaseModel):
    """Log entry for agent decision"""
    id: Optional[int] = None
    timestamp: float = Field(default_factory=time.time)
    
    mode: str
    strategy: str
    
    decision_latency: float               # ms
    decisions_json: Optional[str] = None  # JSON of signal decisions
    state_summary_json: Optional[str] = None  # JSON of perceived state


class SystemEvent(BaseModel):
    """System event log entry"""
    id: Optional[int] = None
    timestamp: float = Field(default_factory=time.time)
    
    event_type: str                       # MODE_CHANGE, ERROR, ALERT, etc.
    severity: Literal['INFO', 'WARNING', 'ERROR', 'CRITICAL']
    
    message: str
    metadata_json: Optional[str] = None


class HealthCheck(BaseModel):
    """System health check result"""
    status: Literal['healthy', 'degraded', 'unhealthy']
    timestamp: float = Field(default_factory=time.time)
    
    database: bool = True
    websocket: bool = True
    agent: bool = True
    simulation: bool = True
    
    uptime: float = 0.0
    version: str = "1.0.0"


class SystemStats(BaseModel):
    """Comprehensive system statistics"""
    uptime_seconds: float
    total_vehicles_processed: int
    total_violations_detected: int
    total_challans_issued: int
    total_emergencies_handled: int
    total_agent_decisions: int
    
    current_vehicle_count: int
    current_density: float
    current_throughput: float

