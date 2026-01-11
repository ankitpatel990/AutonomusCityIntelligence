"""
Violation Detection Engine (FRD-09)

Real-time detection of traffic violations including:
- Red light running
- Speeding
- Wrong direction

Integrates with simulation to monitor vehicles and detect violations.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Dict, Any
import time
import json

from app.models import (
    Vehicle,
    Junction,
    SignalColor,
    TrafficViolation,
    ViolationEvidence,
    VIOLATION_CONFIG,
)


class ViolationType(str, Enum):
    """Types of traffic violations"""
    RED_LIGHT = "RED_LIGHT"
    SPEEDING = "SPEEDING"
    WRONG_DIRECTION = "WRONG_DIRECTION"
    NO_STOPPING = "NO_STOPPING"


@dataclass
class ViolationEvent:
    """Traffic violation event data"""
    violation_id: str
    vehicle_id: str
    number_plate: str
    violation_type: ViolationType
    location: tuple  # (x, y)
    junction_id: Optional[str]
    road_id: Optional[str]
    location_name: Optional[str]
    lat: Optional[float]
    lon: Optional[float]
    timestamp: float
    evidence: dict
    fine_amount: float
    severity: str


class ViolationDetector:
    """
    Detect traffic violations in real-time
    
    Monitors:
    - Vehicles running red lights at junctions
    - Speeding violations on roads
    - Wrong-way driving (future)
    
    Integrates with the autonomous agent loop to check
    violations on each simulation step.
    """
    
    # Fine amounts from config
    FINES = {
        ViolationType.RED_LIGHT: VIOLATION_CONFIG['RED_LIGHT']['fine_amount'],
        ViolationType.SPEEDING: VIOLATION_CONFIG['SPEEDING']['fine_amount'],
        ViolationType.WRONG_DIRECTION: VIOLATION_CONFIG.get('WRONG_LANE', VIOLATION_CONFIG.get('WRONG_DIRECTION', {'fine_amount': 500}))['fine_amount'],
        ViolationType.NO_STOPPING: VIOLATION_CONFIG['NO_STOPPING']['fine_amount']
    }
    
    # Severity levels
    SEVERITY = {
        ViolationType.RED_LIGHT: 'HIGH',
        ViolationType.SPEEDING: 'MEDIUM',
        ViolationType.WRONG_DIRECTION: 'MEDIUM',
        ViolationType.NO_STOPPING: 'LOW'
    }
    
    # Speed limits (km/h)
    SPEED_LIMIT_ROAD = 50
    SPEED_LIMIT_JUNCTION = 30
    
    # Junction detection radius (canvas units)
    JUNCTION_RADIUS = 30
    
    def __init__(self, config: dict = None):
        """
        Initialize violation detector
        
        Args:
            config: Optional configuration overrides
        """
        self.config = config or {}
        
        # Apply config overrides
        if 'speedLimits' in self.config:
            self.SPEED_LIMIT_ROAD = self.config['speedLimits'].get('road', self.SPEED_LIMIT_ROAD)
            self.SPEED_LIMIT_JUNCTION = self.config['speedLimits'].get('junction', self.SPEED_LIMIT_JUNCTION)
        
        # Detected violations
        self.violations: List[ViolationEvent] = []
        self.violation_counter = 0
        
        # Statistics
        self.total_violations = 0
        self.violations_by_type: Dict[ViolationType, int] = {vtype: 0 for vtype in ViolationType}
        
        # Tracking to prevent duplicate violations
        self._recent_violations: Dict[str, float] = {}  # key: "vehicle_id:type" -> timestamp
        
        # WebSocket emitter for real-time notifications
        self._ws_emitter = None
        
        print("[OK] Violation Detector initialized")
    
    def set_ws_emitter(self, emitter):
        """Set WebSocket emitter for real-time notifications"""
        self._ws_emitter = emitter
    
    def check_violations(
        self,
        vehicles: List[Vehicle],
        junctions: List[Junction]
    ) -> List[ViolationEvent]:
        """
        Check for violations (called each simulation step)
        
        Args:
            vehicles: List of current vehicles
            junctions: List of junctions with signal states
        
        Returns:
            List of newly detected violations
        """
        new_violations = []
        
        for vehicle in vehicles:
            # Skip emergency vehicles
            if vehicle.is_emergency:
                continue
            
            # Check red light violation at each junction
            for junction in junctions:
                violation = self._check_red_light(vehicle, junction)
                if violation:
                    new_violations.append(violation)
            
            # Check speeding
            violation = self._check_speeding(vehicle, junctions)
            if violation:
                new_violations.append(violation)
        
        return new_violations
    
    def _check_red_light(
        self,
        vehicle: Vehicle,
        junction: Junction
    ) -> Optional[ViolationEvent]:
        """
        Check if vehicle ran red light
        
        Logic: 
        - Vehicle is within junction radius
        - Signal in vehicle's direction is RED
        - Vehicle speed > minimum threshold (moving)
        """
        # Calculate distance to junction
        distance = self._calculate_distance(
            vehicle.position.x, vehicle.position.y,
            junction.position.x, junction.position.y
        )
        
        # Check if within junction radius
        if distance > self.JUNCTION_RADIUS:
            return None
        
        # Determine vehicle's direction at junction
        direction = self._get_vehicle_direction(vehicle.heading)
        if not direction:
            return None
        
        # Get signal state for that direction
        signal_state = self._get_signal_state(junction, direction)
        
        # Check for violation: RED signal and vehicle moving
        if signal_state == SignalColor.RED and vehicle.speed > 5:
            # Check for duplicate violation (within 10 seconds)
            if self._has_recent_violation(vehicle.id, ViolationType.RED_LIGHT, 10):
                return None
            
            # Record violation
            violation = self._record_violation(
                vehicle=vehicle,
                violation_type=ViolationType.RED_LIGHT,
                location=(vehicle.position.x, vehicle.position.y),
                junction_id=junction.id,
                junction_name=junction.name,
                lat=junction.lat,
                lon=junction.lon,
                evidence={
                    'signalState': signal_state.value,
                    'direction': direction,
                    'speed': vehicle.speed,
                    'junctionId': junction.id,
                    'junctionName': junction.name
                }
            )
            
            print(f"🚨 RED LIGHT violation: {vehicle.number_plate} at {junction.id}")
            
            return violation
        
        return None
    
    def _check_speeding(
        self,
        vehicle: Vehicle,
        junctions: List[Junction]
    ) -> Optional[ViolationEvent]:
        """
        Check if vehicle is speeding
        
        Speed limits:
        - Road: 50 km/h (default)
        - Junction area: 30 km/h (default)
        """
        # Determine if at junction
        is_at_junction = self._is_vehicle_at_junction(vehicle, junctions)
        speed_limit = self.SPEED_LIMIT_JUNCTION if is_at_junction else self.SPEED_LIMIT_ROAD
        
        # Check if exceeding limit
        if vehicle.speed > speed_limit:
            # Calculate severity based on excess speed
            excess = vehicle.speed - speed_limit
            if excess > 30:
                severity = 'HIGH'
                fine_multiplier = 3
            elif excess > 15:
                severity = 'MEDIUM'
                fine_multiplier = 2
            else:
                severity = 'LOW'
                fine_multiplier = 1
            
            # Check for duplicate (within 30 seconds)
            if self._has_recent_violation(vehicle.id, ViolationType.SPEEDING, 30):
                return None
            
            # Record violation
            violation = self._record_violation(
                vehicle=vehicle,
                violation_type=ViolationType.SPEEDING,
                location=(vehicle.position.x, vehicle.position.y),
                road_id=vehicle.current_road,
                evidence={
                    'speed': vehicle.speed,
                    'speedLimit': speed_limit,
                    'excess': excess,
                    'severity': severity
                },
                fine_multiplier=fine_multiplier,
                severity_override=severity
            )
            
            print(f"🚨 SPEEDING violation: {vehicle.number_plate} ({vehicle.speed:.0f} km/h in {speed_limit} zone)")
            
            return violation
        
        return None
    
    def _record_violation(
        self,
        vehicle: Vehicle,
        violation_type: ViolationType,
        location: tuple,
        junction_id: Optional[str] = None,
        junction_name: Optional[str] = None,
        road_id: Optional[str] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        evidence: dict = None,
        fine_multiplier: float = 1.0,
        severity_override: Optional[str] = None
    ) -> ViolationEvent:
        """Record a violation"""
        import uuid
        self.violation_counter += 1
        # Use UUID to ensure uniqueness across instances
        violation_id = f"VIO-{uuid.uuid4().hex[:8].upper()}"
        
        # Calculate fine
        base_fine = self.FINES.get(violation_type, 500.0)
        fine_amount = base_fine * fine_multiplier
        
        # Get severity
        severity = severity_override or self.SEVERITY.get(violation_type, 'MEDIUM')
        
        violation = ViolationEvent(
            violation_id=violation_id,
            vehicle_id=vehicle.id,
            number_plate=vehicle.number_plate,
            violation_type=violation_type,
            location=location,
            junction_id=junction_id,
            road_id=road_id,
            location_name=junction_name,
            lat=lat or vehicle.lat,
            lon=lon or vehicle.lon,
            timestamp=time.time(),
            evidence=evidence or {},
            fine_amount=fine_amount,
            severity=severity
        )
        
        # Store violation
        self.violations.append(violation)
        self.total_violations += 1
        self.violations_by_type[violation_type] += 1
        
        # Track for duplicate prevention
        key = f"{vehicle.id}:{violation_type.value}"
        self._recent_violations[key] = time.time()
        
        # Emit WebSocket notification
        if self._ws_emitter:
            try:
                import asyncio
                asyncio.create_task(
                    self._ws_emitter.emit('violation:detected', {
                        'violationId': violation.violation_id,
                        'vehicleId': violation.vehicle_id,
                        'numberPlate': violation.number_plate,
                        'type': violation.violation_type.value,
                        'severity': violation.severity,
                        'location': violation.location,
                        'junctionId': violation.junction_id,
                        'fineAmount': violation.fine_amount,
                        'timestamp': violation.timestamp,
                        'evidence': violation.evidence
                    })
                )
            except Exception as e:
                print(f"[WARN] Failed to emit violation event: {e}")
        
        return violation
    
    def _has_recent_violation(
        self,
        vehicle_id: str,
        violation_type: ViolationType,
        seconds: float
    ) -> bool:
        """Check if vehicle has recent violation of same type"""
        key = f"{vehicle_id}:{violation_type.value}"
        
        if key not in self._recent_violations:
            return False
        
        time_diff = time.time() - self._recent_violations[key]
        return time_diff < seconds
    
    def _calculate_distance(self, x1: float, y1: float, x2: float, y2: float) -> float:
        """Calculate distance between two points"""
        return ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5
    
    def _get_vehicle_direction(self, heading: float) -> Optional[str]:
        """
        Determine vehicle's direction from heading angle
        
        0° = North, 90° = East, 180° = South, 270° = West
        """
        # Normalize heading to 0-360
        heading = heading % 360
        
        if 315 <= heading or heading < 45:
            return 'north'
        elif 45 <= heading < 135:
            return 'east'
        elif 135 <= heading < 225:
            return 'south'
        elif 225 <= heading < 315:
            return 'west'
        
        return None
    
    def _get_signal_state(self, junction: Junction, direction: str) -> SignalColor:
        """Get signal state for direction at junction"""
        direction_map = {
            'north': junction.signals.north,
            'east': junction.signals.east,
            'south': junction.signals.south,
            'west': junction.signals.west
        }
        
        signal = direction_map.get(direction)
        return signal.current if signal else SignalColor.RED
    
    def _is_vehicle_at_junction(self, vehicle: Vehicle, junctions: List[Junction]) -> bool:
        """Check if vehicle is at any junction"""
        for junction in junctions:
            distance = self._calculate_distance(
                vehicle.position.x, vehicle.position.y,
                junction.position.x, junction.position.y
            )
            
            if distance < self.JUNCTION_RADIUS:
                return True
        
        return False
    
    def get_recent_violations(self, limit: int = 50) -> List[ViolationEvent]:
        """Get recent violations"""
        return self.violations[-limit:]
    
    def get_violations_for_vehicle(self, vehicle_id: str) -> List[ViolationEvent]:
        """Get all violations for a specific vehicle"""
        return [v for v in self.violations if v.vehicle_id == vehicle_id]
    
    def get_unprocessed_violations(self) -> List[ViolationEvent]:
        """Get violations not yet processed into challans"""
        # This will be managed by the auto-challan service
        # For now, return recent violations
        return self.violations[-100:]
    
    def get_statistics(self) -> dict:
        """Get violation statistics"""
        return {
            'totalViolations': self.total_violations,
            'violationsByType': {
                vtype.value: count 
                for vtype, count in self.violations_by_type.items()
            },
            'recentCount': len(self.violations)
        }
    
    def to_traffic_violation(self, event: ViolationEvent) -> TrafficViolation:
        """Convert ViolationEvent to TrafficViolation model"""
        return TrafficViolation(
            id=event.violation_id,
            vehicle_id=event.vehicle_id,
            number_plate=event.number_plate,
            violation_type=event.violation_type.value,
            severity=event.severity,
            location=event.junction_id or event.road_id or 'UNKNOWN',
            location_name=event.location_name,
            junction_id=event.junction_id,
            road_id=event.road_id,
            lat=event.lat,
            lon=event.lon,
            timestamp=event.timestamp,
            evidence=ViolationEvidence(
                speed=event.evidence.get('speed'),
                speed_limit=event.evidence.get('speedLimit'),
                signal_state=event.evidence.get('signalState'),
                snapshot=event.evidence
            )
        )
    
    def clear_old_violations(self, max_age_seconds: float = 3600):
        """Clear violations older than max age"""
        current_time = time.time()
        self.violations = [
            v for v in self.violations
            if current_time - v.timestamp < max_age_seconds
        ]
        
        # Clean up recent violations tracking
        self._recent_violations = {
            k: v for k, v in self._recent_violations.items()
            if current_time - v < 60  # Keep 60 seconds of tracking
        }


# Global instance
_violation_detector: Optional[ViolationDetector] = None


def init_violation_detector(config: dict = None) -> ViolationDetector:
    """Initialize global violation detector"""
    global _violation_detector
    _violation_detector = ViolationDetector(config)
    return _violation_detector


def get_violation_detector() -> Optional[ViolationDetector]:
    """Get global violation detector instance"""
    return _violation_detector

