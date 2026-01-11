"""
Congestion Classifier - Classification & Alerting System
FRD-06: AI-Based Congestion Prediction - FR-06.2

Classifies predicted congestion levels and generates alerts
when congestion is predicted to exceed thresholds.

Congestion Levels:
- LOW: 0-25 density (free flow)
- MEDIUM: 25-50 density (moderate traffic)
- HIGH: 50-75 density (heavy traffic)
- CRITICAL: 75+ density (severe congestion)

Part of the Autonomous City Traffic Intelligence System.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional, TYPE_CHECKING
import time
import uuid

if TYPE_CHECKING:
    from app.prediction.prediction_engine import CongestionPrediction


class CongestionLevel(str, Enum):
    """Congestion severity levels"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AlertSeverity(str, Enum):
    """Alert severity levels"""
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


@dataclass
class CongestionAlert:
    """
    Alert for predicted congestion
    
    Generated when congestion is predicted to exceed thresholds.
    """
    alert_id: str
    road_id: str
    predicted_level: CongestionLevel
    predicted_at_time: float  # When congestion will occur
    predicted_density: float
    confidence: float
    created_at: float
    severity: AlertSeverity
    message: str = ""
    resolved: bool = False
    resolved_at: Optional[float] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses"""
        return {
            'alertId': self.alert_id,
            'roadId': self.road_id,
            'predictedLevel': self.predicted_level.value,
            'predictedAtTime': self.predicted_at_time,
            'minutesAhead': max(0, int((self.predicted_at_time - self.created_at) / 60)),
            'predictedDensity': round(self.predicted_density, 2),
            'confidence': round(self.confidence, 2),
            'severity': self.severity.value,
            'message': self.message,
            'createdAt': self.created_at,
            'resolved': self.resolved,
            'resolvedAt': self.resolved_at
        }


class CongestionClassifier:
    """
    Classify predicted congestion and generate alerts
    
    Thresholds (configurable):
    - LOW: 0-25 density
    - MEDIUM: 25-50 density
    - HIGH: 50-75 density
    - CRITICAL: 75+ density
    
    Usage:
        classifier = CongestionClassifier()
        level = classifier.classify_density(65.5)  # HIGH
        alerts = classifier.check_for_alerts(prediction)
    """
    
    # Default density thresholds
    DEFAULT_THRESHOLDS = {
        CongestionLevel.LOW: (0, 25),
        CongestionLevel.MEDIUM: (25, 50),
        CongestionLevel.HIGH: (50, 75),
        CongestionLevel.CRITICAL: (75, 100)
    }
    
    def __init__(self, config: dict = None):
        """
        Initialize congestion classifier
        
        Args:
            config: Configuration with options:
                - alertThresholds: Dict with 'high' and 'critical' thresholds
                - alertLevels: List of levels that trigger alerts
        """
        self.config = config or {}
        
        # Set thresholds from config
        alert_thresholds = self.config.get('alertThresholds', {})
        high_threshold = alert_thresholds.get('high', 50)
        critical_threshold = alert_thresholds.get('critical', 75)
        
        # Update thresholds based on config
        self.thresholds = {
            CongestionLevel.LOW: (0, high_threshold),
            CongestionLevel.MEDIUM: (high_threshold, critical_threshold),
            CongestionLevel.HIGH: (critical_threshold, 100),
            CongestionLevel.CRITICAL: (75, 100)  # Fixed at 75+
        }
        
        # Recalculate thresholds properly
        self.thresholds = {
            CongestionLevel.LOW: (0, 25),
            CongestionLevel.MEDIUM: (25, high_threshold),
            CongestionLevel.HIGH: (high_threshold, critical_threshold),
            CongestionLevel.CRITICAL: (critical_threshold, 100)
        }
        
        # Alert settings
        self.alert_levels = [CongestionLevel.HIGH, CongestionLevel.CRITICAL]
        
        # Alert history
        self.active_alerts: List[CongestionAlert] = []
        self.all_alerts: List[CongestionAlert] = []
        self.alert_counter = 0
        
        # Deduplication: Track recent alerts per road
        self.recent_alerts_per_road: Dict[str, float] = {}
        self.alert_cooldown = 60  # Seconds between alerts for same road
        
        print("[OK] Congestion Classifier initialized")
        print(f"   Thresholds: LOW < 25, MEDIUM < {high_threshold}, HIGH < {critical_threshold}, CRITICAL >= {critical_threshold}")
    
    def classify_density(self, density: float) -> CongestionLevel:
        """
        Classify density score into congestion level
        
        Args:
            density: Density score (0-100)
        
        Returns:
            CongestionLevel enum
        """
        density = max(0.0, min(100.0, density))  # Clamp to valid range
        
        for level, (min_val, max_val) in self.thresholds.items():
            if min_val <= density < max_val:
                return level
        
        # Default to CRITICAL if over 100
        return CongestionLevel.CRITICAL
    
    def classify_prediction(self, 
                            prediction: 'CongestionPrediction') -> Dict[float, CongestionLevel]:
        """
        Classify each predicted time point
        
        Args:
            prediction: CongestionPrediction object
        
        Returns:
            Dict of timestamp -> CongestionLevel
        """
        classifications = {}
        
        for timestamp, density in prediction.predictions:
            level = self.classify_density(density)
            classifications[timestamp] = level
        
        return classifications
    
    def get_max_predicted_level(self, 
                                 prediction: 'CongestionPrediction') -> CongestionLevel:
        """
        Get the maximum predicted congestion level
        
        Args:
            prediction: CongestionPrediction object
        
        Returns:
            Maximum CongestionLevel
        """
        classifications = self.classify_prediction(prediction)
        
        if not classifications:
            return CongestionLevel.LOW
        
        # Order levels by severity
        level_order = [
            CongestionLevel.LOW,
            CongestionLevel.MEDIUM,
            CongestionLevel.HIGH,
            CongestionLevel.CRITICAL
        ]
        
        max_level = CongestionLevel.LOW
        for level in classifications.values():
            if level_order.index(level) > level_order.index(max_level):
                max_level = level
        
        return max_level
    
    def check_for_alerts(self, 
                         prediction: 'CongestionPrediction') -> List[CongestionAlert]:
        """
        Check if prediction warrants an alert
        
        Generates alerts if congestion predicted to exceed threshold.
        Includes deduplication to avoid alert spam.
        
        Args:
            prediction: CongestionPrediction object
        
        Returns:
            List of newly generated alerts
        """
        new_alerts = []
        current_time = time.time()
        road_id = prediction.road_id
        
        # Check cooldown for this road
        if road_id in self.recent_alerts_per_road:
            last_alert_time = self.recent_alerts_per_road[road_id]
            if current_time - last_alert_time < self.alert_cooldown:
                return []  # Skip due to cooldown
        
        # Find first prediction that exceeds threshold
        for timestamp, density in prediction.predictions:
            level = self.classify_density(density)
            
            # Alert if level is in alert_levels
            if level in self.alert_levels:
                alert = self._create_alert(
                    road_id=road_id,
                    predicted_level=level,
                    predicted_at_time=timestamp,
                    predicted_density=density,
                    confidence=prediction.confidence
                )
                new_alerts.append(alert)
                self.active_alerts.append(alert)
                self.all_alerts.append(alert)
                
                # Update cooldown
                self.recent_alerts_per_road[road_id] = current_time
                
                # Only one alert per prediction
                break
        
        return new_alerts
    
    def _create_alert(self,
                      road_id: str,
                      predicted_level: CongestionLevel,
                      predicted_at_time: float,
                      predicted_density: float,
                      confidence: float) -> CongestionAlert:
        """Create congestion alert"""
        self.alert_counter += 1
        current_time = time.time()
        
        # Determine severity
        if predicted_level == CongestionLevel.CRITICAL:
            severity = AlertSeverity.CRITICAL
        elif predicted_level == CongestionLevel.HIGH:
            severity = AlertSeverity.WARNING
        else:
            severity = AlertSeverity.INFO
        
        # Calculate minutes ahead
        minutes_ahead = int((predicted_at_time - current_time) / 60)
        
        # Generate message
        message = f"{predicted_level.value} congestion predicted on {road_id} in {minutes_ahead} minutes (density: {predicted_density:.1f}%)"
        
        return CongestionAlert(
            alert_id=f"CONG-{self.alert_counter:05d}",
            road_id=road_id,
            predicted_level=predicted_level,
            predicted_at_time=predicted_at_time,
            predicted_density=predicted_density,
            confidence=confidence,
            created_at=current_time,
            severity=severity,
            message=message
        )
    
    def get_active_alerts(self, road_id: str = None) -> List[CongestionAlert]:
        """
        Get active congestion alerts
        
        Args:
            road_id: Filter by road ID (optional)
        
        Returns:
            List of active alerts
        """
        current_time = time.time()
        
        # Filter expired alerts (predicted time has passed)
        active = [
            alert for alert in self.active_alerts
            if alert.predicted_at_time > current_time and not alert.resolved
        ]
        
        # Update active list
        self.active_alerts = active
        
        # Filter by road if specified
        if road_id:
            active = [a for a in active if a.road_id == road_id]
        
        return active
    
    def get_alerts_by_severity(self, severity: AlertSeverity) -> List[CongestionAlert]:
        """Get active alerts of specific severity"""
        return [a for a in self.get_active_alerts() if a.severity == severity]
    
    def resolve_alert(self, alert_id: str) -> bool:
        """
        Resolve (dismiss) an alert
        
        Args:
            alert_id: Alert ID to resolve
        
        Returns:
            True if resolved, False if not found
        """
        for alert in self.active_alerts:
            if alert.alert_id == alert_id:
                alert.resolved = True
                alert.resolved_at = time.time()
                return True
        return False
    
    def clear_alerts(self, road_id: str = None):
        """
        Clear alerts for road or all alerts
        
        Args:
            road_id: Road to clear alerts for (None = all)
        """
        if road_id:
            self.active_alerts = [
                a for a in self.active_alerts 
                if a.road_id != road_id
            ]
        else:
            self.active_alerts = []
    
    def get_statistics(self) -> dict:
        """Get classifier statistics"""
        active = self.get_active_alerts()
        
        severity_counts = {
            AlertSeverity.INFO.value: 0,
            AlertSeverity.WARNING.value: 0,
            AlertSeverity.CRITICAL.value: 0
        }
        
        for alert in active:
            severity_counts[alert.severity.value] += 1
        
        return {
            'totalAlertsGenerated': len(self.all_alerts),
            'activeAlerts': len(active),
            'alertsBySeverity': severity_counts,
            'alertedRoads': len(set(a.road_id for a in active)),
            'thresholds': {
                level.value: f"{min_v}-{max_v}"
                for level, (min_v, max_v) in self.thresholds.items()
            }
        }


# Global classifier instance
_congestion_classifier: Optional[CongestionClassifier] = None


def get_congestion_classifier() -> Optional[CongestionClassifier]:
    """Get the global CongestionClassifier instance"""
    return _congestion_classifier


def init_congestion_classifier(config: dict = None) -> CongestionClassifier:
    """Initialize the global CongestionClassifier with config"""
    global _congestion_classifier
    _congestion_classifier = CongestionClassifier(config)
    return _congestion_classifier

