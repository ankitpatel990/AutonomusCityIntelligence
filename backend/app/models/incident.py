"""
Incident Models

Models for post-incident vehicle tracking and route reconstruction.
"""

from pydantic import BaseModel, Field
from typing import Literal, Optional
from uuid import uuid4
import time


class Incident(BaseModel):
    """
    Traffic incident report
    
    Used for post-incident investigation and vehicle tracking.
    """
    id: str = Field(default_factory=lambda: f"inc-{uuid4().hex[:8]}")
    
    # Target vehicle
    number_plate: str
    
    # Incident details
    incident_time: float                  # Approximate time of incident
    incident_type: Literal['HIT_AND_RUN', 'THEFT', 'SUSPICIOUS', 'OTHER']
    
    # Location
    location: str                         # Junction/Road ID
    location_name: Optional[str] = None   # Human-readable name
    lat: Optional[float] = None
    lon: Optional[float] = None
    
    # Description
    description: str = ""
    
    # Timestamps
    reported_at: float = Field(default_factory=time.time)
    
    # Status
    status: Literal['PROCESSING', 'COMPLETED', 'CANCELLED'] = 'PROCESSING'
    inference_result_id: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "inc-abc12345",
                "number_plate": "GJ18AB1234",
                "incident_time": 1704067200.0,
                "incident_type": "HIT_AND_RUN",
                "location": "J-5",
                "description": "Vehicle fled scene after minor collision",
                "status": "PROCESSING"
            }
        }


class RouteInference(BaseModel):
    """
    Inferred route from detection records
    
    Result of post-incident vehicle tracking.
    """
    id: str = Field(default_factory=lambda: f"inf-{uuid4().hex[:8]}")
    incident_id: str
    number_plate: str
    
    # Time range analyzed
    start_time: float
    end_time: float
    
    # Inferred route
    route: list[str]                      # Junction IDs in order
    route_names: list[str] = Field(default_factory=list)  # Human-readable names
    
    # Detection details
    detection_count: int
    detections: list[dict] = Field(default_factory=list)  # Raw detection records
    
    # Timing analysis
    first_detection: Optional[float] = None
    last_detection: Optional[float] = None
    
    # Confidence
    confidence: float = 0.0               # 0-100
    gaps_in_route: int = 0                # Number of gaps in tracking
    
    # Status
    status: Literal['COMPLETE', 'PARTIAL', 'NO_DATA'] = 'PARTIAL'
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "inf-xyz789",
                "incident_id": "inc-abc123",
                "number_plate": "GJ18AB1234",
                "route": ["J-3", "J-6", "J-9"],
                "detection_count": 3,
                "confidence": 85.0,
                "status": "COMPLETE"
            }
        }


class IncidentReport(BaseModel):
    """Request to file an incident report"""
    number_plate: str
    incident_time: float
    incident_type: Literal['HIT_AND_RUN', 'THEFT', 'SUSPICIOUS', 'OTHER']
    location: str
    description: Optional[str] = None


class IncidentStatus(BaseModel):
    """Status update for an incident"""
    incident_id: str
    status: Literal['PROCESSING', 'COMPLETED', 'CANCELLED']
    route_found: bool
    detection_count: int
    last_known_location: Optional[str] = None
    last_detection_time: Optional[float] = None


class VehicleTrackingQuery(BaseModel):
    """Query for tracking a vehicle"""
    number_plate: str
    start_time: float
    end_time: Optional[float] = None      # Defaults to now
    include_detections: bool = True

