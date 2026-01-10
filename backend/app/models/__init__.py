"""
Pydantic Models Package

All data models for the Traffic Intelligence System.
Import from here for convenience.
"""

# Vehicle models
from .vehicle import (
    Position,
    Vehicle,
    VehicleSpawnRequest,
    VehicleUpdate,
)

# Junction and Signal models
from .junction import (
    SignalColor,
    SignalState,
    JunctionSignals,
    ConnectedRoads,
    JunctionMetrics,
    Junction,
    SignalChangeRequest,
    SignalOverride,
    create_default_signals,
)

# Road models
from .road import (
    RoadGeometry,
    RoadTraffic,
    RoadSegment,
    RealRoad,
)

# Live Traffic API models
from .live_traffic import (
    TrafficIncident,
    LiveTrafficData,
    TomTomFlowData,
    TrafficAPIConfig,
)

# Coordinate models
from .coordinates import (
    MapBounds,
    GPSCoordinate,
    CanvasCoordinate,
    CoordinateConverter,
    GANDHINAGAR_BOUNDS,
    GIFT_CITY_BOUNDS,
    SECTOR_5_BOUNDS,
)

# Traffic Control models
from .traffic_control import (
    TrafficDataMode,
    TrafficDataSource,
    ManualTrafficOverride,
    MapAreaMetadata,
    MapArea,
    PREDEFINED_MAP_AREAS,
    TrafficModeChangeRequest,
    LoadMapAreaRequest,
)

# Real Map (OSM) models
from .real_map import (
    RealJunction,
    OSMLoadResult,
    OSMNodeData,
    OSMWayData,
)

# Detection models
from .detection import (
    DetectionRecord,
    DetectionQuery,
    DetectionSummary,
    VehicleRoute,
)

# Violation models
from .violation import (
    ViolationEvidence,
    TrafficViolation,
    ViolationDetectionResult,
    ViolationStats,
    VIOLATION_CONFIG,
)

# Challan models
from .challan import (
    VehicleOwner,
    Challan,
    ChallanTransaction,
    ChallanStats,
    PayChallanRequest,
    IssueChallanRequest,
    MOCK_OWNERS,
)

# Emergency models
from .emergency import (
    EmergencyVehicle,
    EmergencyCorridor,
    EmergencyRequest,
    EmergencyStatus,
    CorridorCalculation,
)

# Incident models
from .incident import (
    Incident,
    RouteInference,
    IncidentReport,
    IncidentStatus,
    VehicleTrackingQuery,
)

# Prediction models
from .prediction import (
    CongestionPrediction,
    PredictionAlert,
    DensityTrend,
    PredictionConfig,
    CityPredictionSummary,
)

# System State models
from .system_state import (
    SimulationState,
    AgentState,
    PerformanceMetrics,
    SystemMode,
    SystemState,
    AgentLog,
    SystemEvent,
    HealthCheck,
    SystemStats,
)


__all__ = [
    # Vehicle
    "Position",
    "Vehicle",
    "VehicleSpawnRequest",
    "VehicleUpdate",
    
    # Junction
    "SignalColor",
    "SignalState",
    "JunctionSignals",
    "ConnectedRoads",
    "JunctionMetrics",
    "Junction",
    "SignalChangeRequest",
    "SignalOverride",
    "create_default_signals",
    
    # Road
    "RoadGeometry",
    "RoadTraffic",
    "RoadSegment",
    "RealRoad",
    
    # Live Traffic
    "TrafficIncident",
    "LiveTrafficData",
    "TomTomFlowData",
    "TrafficAPIConfig",
    
    # Coordinates
    "MapBounds",
    "GPSCoordinate",
    "CanvasCoordinate",
    "CoordinateConverter",
    "GANDHINAGAR_BOUNDS",
    "GIFT_CITY_BOUNDS",
    "SECTOR_5_BOUNDS",
    
    # Traffic Control
    "TrafficDataMode",
    "TrafficDataSource",
    "ManualTrafficOverride",
    "MapAreaMetadata",
    "MapArea",
    "PREDEFINED_MAP_AREAS",
    "TrafficModeChangeRequest",
    "LoadMapAreaRequest",
    
    # Real Map
    "RealJunction",
    "OSMLoadResult",
    "OSMNodeData",
    "OSMWayData",
    
    # Detection
    "DetectionRecord",
    "DetectionQuery",
    "DetectionSummary",
    "VehicleRoute",
    
    # Violation
    "ViolationEvidence",
    "TrafficViolation",
    "ViolationDetectionResult",
    "ViolationStats",
    "VIOLATION_CONFIG",
    
    # Challan
    "VehicleOwner",
    "Challan",
    "ChallanTransaction",
    "ChallanStats",
    "PayChallanRequest",
    "IssueChallanRequest",
    "MOCK_OWNERS",
    
    # Emergency
    "EmergencyVehicle",
    "EmergencyCorridor",
    "EmergencyRequest",
    "EmergencyStatus",
    "CorridorCalculation",
    
    # Incident
    "Incident",
    "RouteInference",
    "IncidentReport",
    "IncidentStatus",
    "VehicleTrackingQuery",
    
    # Prediction
    "CongestionPrediction",
    "PredictionAlert",
    "DensityTrend",
    "PredictionConfig",
    "CityPredictionSummary",
    
    # System State
    "SimulationState",
    "AgentState",
    "PerformanceMetrics",
    "SystemMode",
    "SystemState",
    "AgentLog",
    "SystemEvent",
    "HealthCheck",
    "SystemStats",
]
