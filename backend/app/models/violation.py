"""
Traffic Violation Models

Models for detecting and recording traffic violations.
"""

from pydantic import BaseModel, Field
from typing import Literal, Optional, Any
from uuid import uuid4
import time


class ViolationEvidence(BaseModel):
    """Evidence for a traffic violation"""
    speed: Optional[float] = None         # Recorded speed
    speed_limit: Optional[float] = None   # Applicable speed limit
    signal_state: Optional[str] = None    # Signal state at time of violation
    snapshot: Optional[dict] = None       # Additional evidence data
    
    class Config:
        json_schema_extra = {
            "example": {
                "speed": 72.5,
                "speed_limit": 50.0,
                "signal_state": "RED"
            }
        }


class TrafficViolation(BaseModel):
    """
    Traffic violation record
    
    Records detected traffic violations before challan generation.
    """
    id: str = Field(default_factory=lambda: f"vio-{uuid4().hex[:8]}")
    
    # Vehicle info
    vehicle_id: str
    number_plate: str
    
    # Violation details
    violation_type: Literal['RED_LIGHT', 'SPEEDING', 'WRONG_LANE', 'NO_STOPPING']
    severity: Literal['LOW', 'MEDIUM', 'HIGH'] = 'MEDIUM'
    
    # Location
    location: str                         # Junction/Road ID
    location_name: Optional[str] = None   # Human-readable name
    junction_id: Optional[str] = None
    road_id: Optional[str] = None
    
    # GPS (for real map mode)
    lat: Optional[float] = None
    lon: Optional[float] = None
    
    # Timing
    timestamp: float = Field(default_factory=time.time)
    
    # Evidence
    evidence: ViolationEvidence = Field(default_factory=ViolationEvidence)
    
    # Processing status
    processed: bool = False
    challan_id: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "vio-abc12345",
                "vehicle_id": "v-xyz789",
                "number_plate": "GJ18AB1234",
                "violation_type": "RED_LIGHT",
                "severity": "HIGH",
                "location": "J-5",
                "processed": False
            }
        }


class ViolationDetectionResult(BaseModel):
    """Result of violation detection check"""
    is_violation: bool
    violation_type: Optional[Literal['RED_LIGHT', 'SPEEDING', 'WRONG_LANE', 'NO_STOPPING']] = None
    severity: Optional[Literal['LOW', 'MEDIUM', 'HIGH']] = None
    evidence: Optional[ViolationEvidence] = None
    message: Optional[str] = None


class ViolationStats(BaseModel):
    """Statistics about violations"""
    total_violations: int
    by_type: dict[str, int]               # Violation type -> count
    by_severity: dict[str, int]           # Severity -> count
    processed_count: int
    unprocessed_count: int
    time_range_start: float
    time_range_end: float


# Violation severity and fine mapping
VIOLATION_CONFIG = {
    'RED_LIGHT': {
        'severity': 'HIGH',
        'fine_amount': 1000.0,
        'description': 'Running a red light'
    },
    'SPEEDING': {
        'severity': 'MEDIUM',
        'fine_amount': 2000.0,
        'description': 'Exceeding speed limit'
    },
    'WRONG_LANE': {
        'severity': 'MEDIUM',
        'fine_amount': 500.0,
        'description': 'Driving in wrong lane'
    },
    'NO_STOPPING': {
        'severity': 'LOW',
        'fine_amount': 300.0,
        'description': 'No stopping at stop sign'
    }
}

