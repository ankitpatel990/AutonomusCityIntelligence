"""
Post-Incident Vehicle Tracking Module (FRD-08)

This module provides forensic analysis capabilities for reconstructing 
vehicle movement after an incident is reported.

Components:
- DetectionHistoryLogger: Logs vehicle detections at junctions
- IncidentManager: Manages incident records and lifecycle
- VehicleInferenceEngine: Infers probable vehicle locations

Usage:
    from app.incident import (
        init_detection_logger,
        init_incident_manager,
        init_inference_engine,
        get_detection_logger,
        get_incident_manager,
        get_inference_engine
    )
    
    # Initialize components
    logger = init_detection_logger()
    engine = init_inference_engine(map_service)
    manager = init_incident_manager(engine, ws_emitter)
    
    # Report incident
    incident_id = await manager.create_incident(
        number_plate="GJ01AB1234",
        incident_time=time.time() - 3600,
        incident_type="HIT_AND_RUN"
    )
    
    # Get inference results
    result = await manager.get_inference_result(incident_id)
"""

# Detection Logger
from app.incident.detection_logger import (
    DetectionHistoryLogger,
    VehicleDetectionEvent,
    init_detection_logger,
    get_detection_logger,
    set_detection_logger
)

# Incident Manager
from app.incident.incident_manager import (
    IncidentManager,
    IncidentType,
    IncidentStatus,
    IncidentRecord,
    IncidentInferenceResult,
    ProbableLocation,
    DetectionHistoryItem,
    init_incident_manager,
    get_incident_manager,
    set_incident_manager
)

# Inference Engine
from app.incident.inference_engine import (
    VehicleInferenceEngine,
    JunctionInfo,
    init_inference_engine,
    get_inference_engine,
    set_inference_engine
)

__all__ = [
    # Detection Logger
    'DetectionHistoryLogger',
    'VehicleDetectionEvent',
    'init_detection_logger',
    'get_detection_logger',
    'set_detection_logger',
    
    # Incident Manager
    'IncidentManager',
    'IncidentType',
    'IncidentStatus',
    'IncidentRecord',
    'IncidentInferenceResult',
    'ProbableLocation',
    'DetectionHistoryItem',
    'init_incident_manager',
    'get_incident_manager',
    'set_incident_manager',
    
    # Inference Engine
    'VehicleInferenceEngine',
    'JunctionInfo',
    'init_inference_engine',
    'get_inference_engine',
    'set_inference_engine',
]
