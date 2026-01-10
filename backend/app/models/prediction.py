"""
Congestion Prediction Models

Models for traffic congestion prediction and alerts.
"""

from pydantic import BaseModel, Field
from typing import Literal, Optional
import time


class CongestionPrediction(BaseModel):
    """
    Congestion prediction for a location
    
    Predicts future traffic density for roads and junctions.
    """
    location_id: str
    location_type: Literal['ROAD', 'JUNCTION']
    location_name: Optional[str] = None   # Human-readable name
    
    # Current state
    current_density: float                # 0-100
    current_classification: Literal['LOW', 'MEDIUM', 'HIGH', 'JAM']
    
    # Prediction
    predicted_density: float              # 0-100
    predicted_classification: Literal['LOW', 'MEDIUM', 'HIGH', 'JAM']
    
    # Time to high density
    time_to_high_density: Optional[float] = None  # minutes (None if N/A)
    
    # Confidence
    confidence: float                     # 0-100
    
    # Metadata
    timestamp: float = Field(default_factory=time.time)
    prediction_horizon: int = 5           # minutes (3, 5, or 10)
    algorithm: str = "exponential_smoothing"
    
    class Config:
        json_schema_extra = {
            "example": {
                "location_id": "R-1-2",
                "location_type": "ROAD",
                "location_name": "GH Road Sector 5",
                "current_density": 45.0,
                "current_classification": "MEDIUM",
                "predicted_density": 72.0,
                "predicted_classification": "HIGH",
                "time_to_high_density": 8.5,
                "confidence": 78.5,
                "prediction_horizon": 10
            }
        }


class PredictionAlert(BaseModel):
    """
    Congestion prediction alert
    
    Generated when high congestion is predicted.
    """
    id: str = Field(default_factory=lambda: f"alert-{int(time.time())}")
    
    location_id: str
    location_type: Literal['ROAD', 'JUNCTION']
    location_name: Optional[str] = None
    
    alert_type: Literal['CONGESTION_WARNING', 'CONGESTION_IMMINENT', 'CONGESTION_CLEARING']
    severity: Literal['LOW', 'MEDIUM', 'HIGH']
    
    message: str
    
    current_density: float
    predicted_density: float
    time_to_event: Optional[float] = None  # minutes
    
    timestamp: float = Field(default_factory=time.time)
    acknowledged: bool = False
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "alert-1704067200",
                "location_id": "J-5",
                "location_type": "JUNCTION",
                "alert_type": "CONGESTION_IMMINENT",
                "severity": "HIGH",
                "message": "High congestion expected at J-5 in 5 minutes",
                "current_density": 55.0,
                "predicted_density": 85.0,
                "time_to_event": 5.0
            }
        }


class DensityTrend(BaseModel):
    """Density trend for a location over time"""
    location_id: str
    timestamps: list[float]
    densities: list[float]
    trend: Literal['INCREASING', 'STABLE', 'DECREASING']
    trend_strength: float                 # 0-1


class PredictionConfig(BaseModel):
    """Configuration for prediction engine"""
    prediction_horizon: int = 10          # minutes
    update_interval: int = 30             # seconds
    history_window: int = 300             # seconds of history to analyze
    algorithm: Literal['moving_average', 'linear_trend', 'exponential_smoothing'] = 'exponential_smoothing'
    alert_threshold_high: float = 70.0    # density threshold for high alert
    alert_threshold_critical: float = 85.0


class CityPredictionSummary(BaseModel):
    """City-wide prediction summary"""
    total_locations: int
    locations_at_risk: int                # Predicted to hit HIGH in next N minutes
    predictions: list[CongestionPrediction]
    active_alerts: list[PredictionAlert]
    timestamp: float = Field(default_factory=time.time)

