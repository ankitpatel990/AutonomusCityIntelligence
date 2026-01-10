"""
WebSocket Event Type Definitions

This module defines all WebSocket event types and their data structures
as specified in FRD-01 Section 2.4 (FR-10.18).

Events are categorized as:
- Server → Client: Updates pushed from backend
- Client → Server: Commands from frontend
"""

from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime


# ============================================
# Event Name Constants
# ============================================

class ServerEvent(str, Enum):
    """Events emitted from server to client"""
    
    # Connection
    CONNECTION_SUCCESS = "connection:success"
    
    # Vehicle updates
    VEHICLE_UPDATE = "vehicle:update"
    VEHICLE_SPAWNED = "vehicle:spawned"
    VEHICLE_REMOVED = "vehicle:removed"
    
    # Signal updates
    SIGNAL_CHANGE = "signal:change"
    
    # Density updates
    DENSITY_UPDATE = "density:update"
    
    # Prediction updates
    PREDICTION_UPDATE = "prediction:update"
    
    # Agent updates
    AGENT_DECISION = "agent:decision"
    AGENT_STATUS_UPDATE = "agent:status_update"
    
    # Emergency events
    EMERGENCY_ACTIVATED = "emergency:activated"
    EMERGENCY_DEACTIVATED = "emergency:deactivated"
    EMERGENCY_PROGRESS = "emergency:progress"
    
    # Safety events
    FAILSAFE_TRIGGERED = "failsafe:triggered"
    FAILSAFE_CLEARED = "failsafe:cleared"
    
    # Violation & Challan events
    VIOLATION_DETECTED = "violation:detected"
    CHALLAN_ISSUED = "challan:issued"
    CHALLAN_PAID = "challan:paid"
    
    # Traffic control events
    TRAFFIC_CONTROL_ACTIVE = "traffic:control:active"
    TRAFFIC_CONTROL_REMOVED = "traffic:control:removed"
    
    # Live traffic events (NEW v2.0)
    LIVE_TRAFFIC_UPDATED = "live:traffic:updated"
    LIVE_TRAFFIC_ERROR = "live:traffic:error"
    
    # Map events (NEW v2.0)
    MAP_LOADED = "map:loaded"
    MAP_LOADING = "map:loading"
    MAP_ERROR = "map:error"
    
    # Data mode events (NEW v2.0)
    DATA_MODE_CHANGED = "data:mode:changed"
    
    # System state
    SYSTEM_STATE_UPDATE = "system:state_update"
    SIMULATION_STATE = "simulation:state"


class ClientEvent(str, Enum):
    """Events received from client"""
    
    # Connection
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    
    # Simulation control
    SIMULATION_CONTROL = "simulation:control"
    
    # Vehicle actions
    VEHICLE_SPAWN = "vehicle:spawn"
    
    # Signal actions
    SIGNAL_OVERRIDE = "signal:override"
    
    # Traffic adjustments
    TRAFFIC_ADJUST = "traffic:adjust"
    
    # Emergency actions
    EMERGENCY_TRIGGER = "emergency:trigger"
    EMERGENCY_CLEAR = "emergency:clear"
    
    # Map actions (NEW v2.0)
    MAP_LOAD_REQUEST = "map:load:request"
    
    # Traffic mode actions (NEW v2.0)
    TRAFFIC_MODE_CHANGE = "traffic:mode:change"
    TRAFFIC_OVERRIDE_SET = "traffic:override:set"
    TRAFFIC_OVERRIDE_CLEAR = "traffic:override:clear"
    
    # Subscriptions
    SUBSCRIBE_UPDATES = "subscribe:updates"
    UNSUBSCRIBE_UPDATES = "unsubscribe:updates"


# ============================================
# Server → Client Event Data Models
# ============================================

class ConnectionSuccessData(BaseModel):
    """Data for connection:success event"""
    message: str = "Connected to Traffic Intelligence System"
    timestamp: float
    server_version: str = "1.0.0"


class VehicleUpdateData(BaseModel):
    """Data for vehicle:update event (throttled to 10 Hz)"""
    vehicleId: str
    position: Dict[str, float]  # {x, y}
    speed: float
    heading: float = 0.0
    timestamp: float
    
    # Optional GPS coordinates (for real map mode)
    lat: Optional[float] = None
    lon: Optional[float] = None


class VehicleSpawnedData(BaseModel):
    """Data for vehicle:spawned event"""
    vehicleId: str
    numberPlate: str
    type: Literal["car", "bike", "ambulance"]
    position: Dict[str, float]
    destination: str
    timestamp: float


class VehicleRemovedData(BaseModel):
    """Data for vehicle:removed event"""
    vehicleId: str
    reason: Literal["reached_destination", "despawned", "collision"]
    timestamp: float


class SignalChangeData(BaseModel):
    """Data for signal:change event"""
    junctionId: str
    direction: Literal["north", "east", "south", "west"]
    newState: Literal["RED", "YELLOW", "GREEN"]
    previousState: Optional[str] = None
    duration: float = 0.0
    timestamp: float


class DensityUpdateData(BaseModel):
    """Data for density:update event (every 1 second)"""
    roadId: str
    densityScore: float  # 0-100
    classification: Literal["LOW", "MEDIUM", "HIGH"]
    vehicleCount: int
    timestamp: float
    
    # Optional color hint for UI
    color: Optional[str] = None  # e.g., "#00ff00" for LOW


class PredictionUpdateData(BaseModel):
    """Data for prediction:update event (every 5 seconds)"""
    predictions: List[Dict[str, Any]]
    generatedAt: float
    nextUpdate: float
    modelVersion: str = "1.0.0"


class AgentDecisionData(BaseModel):
    """Data for agent:decision event"""
    timestamp: float
    decisions: List[Dict[str, Any]]  # [{junctionId, action, reason}]
    latency: float  # ms
    strategy: Literal["RL", "RULE_BASED"]
    mode: str = "NORMAL"


class AgentStatusUpdateData(BaseModel):
    """Data for agent:status_update event"""
    status: Literal["RUNNING", "PAUSED", "STOPPED"]
    strategy: Literal["RL", "RULE_BASED"]
    uptime: float
    decisions: int
    avgLatency: float


class EmergencyActivatedData(BaseModel):
    """Data for emergency:activated event"""
    vehicleId: str
    corridorPath: List[str]  # Junction IDs
    estimatedTime: float  # seconds
    destination: str
    activatedAt: float


class EmergencyDeactivatedData(BaseModel):
    """Data for emergency:deactivated event"""
    vehicleId: str
    completionTime: float
    reason: Literal["reached_destination", "cancelled", "timeout"]


class EmergencyProgressData(BaseModel):
    """Data for emergency:progress event"""
    vehicleId: str
    currentJunction: str
    progress: float  # 0-100%
    estimatedArrival: float


class FailsafeTriggeredData(BaseModel):
    """Data for failsafe:triggered event"""
    reason: str
    timestamp: float
    affectedJunctions: List[str]
    previousMode: str
    newMode: str = "FAIL_SAFE"
    signalState: str = "ALL_RED"


class ViolationDetectedData(BaseModel):
    """Data for violation:detected event"""
    id: str
    vehicleId: str
    numberPlate: str
    violationType: Literal["RED_LIGHT", "SPEEDING", "WRONG_LANE"]
    severity: Literal["LOW", "MEDIUM", "HIGH"]
    location: str
    timestamp: float
    evidence: Dict[str, Any]


class ChallanIssuedData(BaseModel):
    """Data for challan:issued event"""
    challanId: str
    numberPlate: str
    ownerName: str
    violationType: str
    fineAmount: float
    location: str
    timestamp: float


class ChallanPaidData(BaseModel):
    """Data for challan:paid event"""
    challanId: str
    transactionId: str
    amount: float
    newBalance: float
    timestamp: float


class TrafficControlActiveData(BaseModel):
    """Data for traffic:control:active event"""
    controlId: str
    junctionId: str
    direction: str
    action: str
    duration: Optional[float]
    expiresAt: Optional[float]
    createdAt: float


class TrafficControlRemovedData(BaseModel):
    """Data for traffic:control:removed event"""
    controlId: str
    reason: Literal["expired", "manual", "emergency"]


class LiveTrafficUpdatedData(BaseModel):
    """Data for live:traffic:updated event (NEW v2.0)"""
    roads: Dict[str, Dict[str, Any]]  # {roadId: LiveTrafficData}
    timestamp: str
    provider: str
    updatedCount: int


class LiveTrafficErrorData(BaseModel):
    """Data for live:traffic:error event (NEW v2.0)"""
    error: str
    provider: str
    timestamp: str
    fallbackMode: str


class MapLoadedData(BaseModel):
    """Data for map:loaded event (NEW v2.0)"""
    mapArea: Dict[str, Any]
    junctionCount: int
    roadCount: int
    loadTime: float


class DataModeChangedData(BaseModel):
    """Data for data:mode:changed event (NEW v2.0)"""
    oldMode: str
    newMode: str
    timestamp: str


class SystemStateUpdateData(BaseModel):
    """Data for system:state_update event"""
    mode: str
    simulationTime: float
    isPaused: bool
    vehicleCount: int
    avgDensity: float
    fps: float
    timestamp: float


# ============================================
# Client → Server Event Data Models
# ============================================

class SimulationControlRequest(BaseModel):
    """Request for simulation:control event"""
    action: Literal["PAUSE", "RESUME", "RESET", "START", "STOP"]
    timestamp: Optional[float] = None


class VehicleSpawnRequest(BaseModel):
    """Request for vehicle:spawn event"""
    type: Literal["car", "bike", "ambulance"] = "car"
    spawnPoint: Optional[str] = None  # Junction ID
    destination: Optional[str] = None  # Junction ID


class SignalOverrideRequest(BaseModel):
    """Request for signal:override event"""
    junctionId: str
    direction: Literal["N", "E", "S", "W"]
    action: Literal["FORCE_GREEN", "LOCK_RED", "CLEAR"]
    duration: Optional[float] = None  # seconds, None = indefinite


class TrafficAdjustRequest(BaseModel):
    """Request for traffic:adjust event"""
    targetId: str
    targetType: Literal["ROAD", "JUNCTION"]
    action: str
    parameters: Dict[str, Any] = {}


class EmergencyTriggerRequest(BaseModel):
    """Request for emergency:trigger event"""
    spawnPoint: str
    destination: str
    vehicleType: str = "ambulance"


class MapLoadRequestData(BaseModel):
    """Request for map:load:request event (NEW v2.0)"""
    method: Literal["bbox", "place", "radius", "predefined"]
    parameters: Dict[str, Any]


class TrafficModeChangeRequest(BaseModel):
    """Request for traffic:mode:change event (NEW v2.0)"""
    mode: Literal["LIVE_API", "MANUAL", "HYBRID", "SIMULATION"]
    provider: Optional[str] = None


class TrafficOverrideSetRequest(BaseModel):
    """Request for traffic:override:set event (NEW v2.0)"""
    roadId: str
    congestionLevel: Literal["LOW", "MEDIUM", "HIGH", "JAM"]
    duration: Optional[float] = None


class SubscribeRequest(BaseModel):
    """Request for subscribe:updates event"""
    channels: List[str]  # e.g., ["vehicles", "signals", "density"]

