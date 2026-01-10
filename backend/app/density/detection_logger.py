"""
Vehicle Detection Logger Module

Log vehicle passages through junctions for post-incident tracking.
Implements FRD-02 FR-02.9 and provides data for FRD-08.

Features:
- Junction crossing detection
- Batch insertion for performance
- Duplicate prevention
- 24-hour retention management
"""

from typing import Dict, List, Optional, Set
from uuid import uuid4
import time
import math

from sqlalchemy.orm import Session

from app.database.models import DetectionRecord as DBDetectionRecord


class VehicleDetectionLogger:
    """
    Log vehicle detections at junctions
    
    Records each time a vehicle passes through a junction for:
    - Post-incident route reconstruction
    - Traffic pattern analysis
    - Vehicle tracking queries
    
    Uses batch insertion for performance (<10ms per batch).
    """
    
    def __init__(self, db_session: Session = None):
        """
        Initialize the detection logger
        
        Args:
            db_session: SQLAlchemy session (optional, can be set later)
        """
        self.db_session = db_session
        
        # Track last detection to prevent duplicates
        # Key: "vehicle_id-junction_id", Value: timestamp
        self.last_detections: Dict[str, float] = {}
        
        # Duplicate prevention cooldown (seconds)
        self.detection_cooldown = 5.0
        
        # Batch logging configuration
        self.batch_enabled = True
        self.batch_size = 100
        self.pending_records: List[DBDetectionRecord] = []
        
        # Detection radius (pixels from junction center)
        self.detection_radius = 30
        
        # Statistics
        self.total_detections = 0
        self.total_batches_flushed = 0
    
    def set_db_session(self, db_session: Session):
        """Set the database session"""
        self.db_session = db_session
    
    def log_detection(
        self,
        vehicle,
        junction,
        direction: str,
        incoming_road: str,
        outgoing_road: str
    ) -> Optional[str]:
        """
        Log vehicle detection at junction
        
        Args:
            vehicle: Vehicle object
            junction: Junction being crossed
            direction: Direction of travel (N/E/S/W)
            incoming_road: Road ID vehicle came from
            outgoing_road: Road ID vehicle going to
            
        Returns:
            Detection record ID if logged, None if skipped
        """
        # Get vehicle and junction IDs
        vehicle_id = vehicle.id if hasattr(vehicle, 'id') else vehicle.get('id')
        junction_id = junction.id if hasattr(junction, 'id') else junction.get('id')
        
        # Skip if recently logged at this junction (prevent duplicates)
        detection_key = f"{vehicle_id}-{junction_id}"
        current_time = time.time()
        
        if detection_key in self.last_detections:
            last_time = self.last_detections[detection_key]
            if current_time - last_time < self.detection_cooldown:
                return None
        
        # Get vehicle attributes
        number_plate = vehicle.number_plate if hasattr(vehicle, 'number_plate') else vehicle.get('number_plate', vehicle.get('numberPlate', ''))
        vehicle_type = vehicle.type if hasattr(vehicle, 'type') else vehicle.get('type', 'car')
        speed = vehicle.speed if hasattr(vehicle, 'speed') else vehicle.get('speed', 0)
        is_violating = vehicle.is_violating if hasattr(vehicle, 'is_violating') else vehicle.get('is_violating', vehicle.get('isViolating', False))
        
        # Get position
        position = vehicle.position if hasattr(vehicle, 'position') else vehicle.get('position', {})
        position_x = position.x if hasattr(position, 'x') else position.get('x', 0)
        position_y = position.y if hasattr(position, 'y') else position.get('y', 0)
        
        # Create detection record
        record_id = f"det-{uuid4().hex[:8]}"
        
        record = DBDetectionRecord(
            id=record_id,
            vehicle_id=vehicle_id,
            number_plate=number_plate,
            junction_id=junction_id,
            timestamp=current_time,
            direction=direction,
            incoming_road=incoming_road,
            outgoing_road=outgoing_road,
            speed=speed,
            position_x=position_x,
            position_y=position_y,
            vehicle_type=vehicle_type,
            violation_detected=is_violating
        )
        
        if self.batch_enabled:
            self.pending_records.append(record)
            
            # Flush if batch full
            if len(self.pending_records) >= self.batch_size:
                self.flush()
        else:
            # Immediate write
            if self.db_session:
                self.db_session.add(record)
                self.db_session.commit()
        
        # Update tracking
        self.last_detections[detection_key] = current_time
        self.total_detections += 1
        
        return record_id
    
    def detect_junction_crossing(
        self,
        vehicle,
        junctions: list
    ) -> Optional[object]:
        """
        Detect if vehicle is crossing a junction
        
        Args:
            vehicle: Vehicle object with position
            junctions: List of Junction objects
            
        Returns:
            Junction object if crossing, None otherwise
        """
        # Get vehicle position
        position = vehicle.position if hasattr(vehicle, 'position') else vehicle.get('position', {})
        vx = position.x if hasattr(position, 'x') else position.get('x', 0)
        vy = position.y if hasattr(position, 'y') else position.get('y', 0)
        
        for junction in junctions:
            # Get junction position
            j_pos = junction.position if hasattr(junction, 'position') else junction.get('position', {})
            jx = j_pos.x if hasattr(j_pos, 'x') else j_pos.get('x', 0)
            jy = j_pos.y if hasattr(j_pos, 'y') else j_pos.get('y', 0)
            
            dist = self._distance(vx, vy, jx, jy)
            if dist < self.detection_radius:
                return junction
        
        return None
    
    def _distance(self, x1: float, y1: float, x2: float, y2: float) -> float:
        """Calculate Euclidean distance between two points"""
        dx = x1 - x2
        dy = y1 - y2
        return math.sqrt(dx * dx + dy * dy)
    
    def determine_direction(self, vehicle) -> str:
        """
        Determine vehicle's travel direction based on heading
        
        Args:
            vehicle: Vehicle object with heading attribute
            
        Returns:
            Direction string: 'N', 'E', 'S', or 'W'
        """
        heading = vehicle.heading if hasattr(vehicle, 'heading') else vehicle.get('heading', 0)
        
        # Convert heading (0-360) to cardinal direction
        # 0/360 = East, 90 = North, 180 = West, 270 = South
        if 45 <= heading < 135:
            return 'N'
        elif 135 <= heading < 225:
            return 'W'
        elif 225 <= heading < 315:
            return 'S'
        else:
            return 'E'
    
    def flush(self) -> int:
        """
        Flush pending detections to database (batch write)
        
        Returns:
            Number of records written
        """
        if not self.pending_records:
            return 0
        
        if not self.db_session:
            print("[WARN] No database session - discarding pending records")
            self.pending_records.clear()
            return 0
        
        try:
            self.db_session.bulk_save_objects(self.pending_records)
            self.db_session.commit()
            
            count = len(self.pending_records)
            self.total_batches_flushed += 1
            
            print(f"[OK] Flushed {count} detection records (batch #{self.total_batches_flushed})")
            
            self.pending_records.clear()
            return count
            
        except Exception as e:
            print(f"[ERROR] Error flushing detections: {e}")
            self.db_session.rollback()
            return 0
    
    def cleanup_old_records(self, retention_hours: int = 24) -> int:
        """
        Delete detection records older than retention period
        
        Should be called periodically (e.g., hourly)
        
        Args:
            retention_hours: How long to keep records (default 24 hours)
            
        Returns:
            Number of records deleted
        """
        if not self.db_session:
            return 0
        
        cutoff_time = time.time() - (retention_hours * 3600)
        
        try:
            deleted = self.db_session.query(DBDetectionRecord)\
                .filter(DBDetectionRecord.timestamp < cutoff_time)\
                .delete()
            
            self.db_session.commit()
            
            print(f"[CLEANUP] Cleaned up {deleted} old detection records")
            return deleted
            
        except Exception as e:
            print(f"[ERROR] Error cleaning up records: {e}")
            self.db_session.rollback()
            return 0
    
    def get_vehicle_detections(
        self,
        number_plate: str,
        start_time: float = None,
        end_time: float = None,
        limit: int = 100
    ) -> List[dict]:
        """
        Query detections for a specific vehicle
        
        Args:
            number_plate: Vehicle number plate
            start_time: Start of time window (optional)
            end_time: End of time window (optional)
            limit: Maximum records to return
            
        Returns:
            List of detection records as dictionaries
        """
        if not self.db_session:
            return []
        
        query = self.db_session.query(DBDetectionRecord)\
            .filter(DBDetectionRecord.number_plate == number_plate)
        
        if start_time:
            query = query.filter(DBDetectionRecord.timestamp >= start_time)
        
        if end_time:
            query = query.filter(DBDetectionRecord.timestamp <= end_time)
        
        records = query.order_by(DBDetectionRecord.timestamp.desc())\
            .limit(limit)\
            .all()
        
        return [
            {
                'id': r.id,
                'vehicleId': r.vehicle_id,
                'numberPlate': r.number_plate,
                'junctionId': r.junction_id,
                'timestamp': r.timestamp,
                'direction': r.direction,
                'incomingRoad': r.incoming_road,
                'outgoingRoad': r.outgoing_road,
                'speed': r.speed,
                'violationDetected': r.violation_detected
            }
            for r in records
        ]
    
    def get_junction_detections(
        self,
        junction_id: str,
        duration_seconds: int = 300,
        limit: int = 100
    ) -> List[dict]:
        """
        Get recent detections at a junction
        
        Args:
            junction_id: Junction identifier
            duration_seconds: How far back to look
            limit: Maximum records to return
            
        Returns:
            List of detection records
        """
        if not self.db_session:
            return []
        
        cutoff_time = time.time() - duration_seconds
        
        records = self.db_session.query(DBDetectionRecord)\
            .filter(DBDetectionRecord.junction_id == junction_id)\
            .filter(DBDetectionRecord.timestamp >= cutoff_time)\
            .order_by(DBDetectionRecord.timestamp.desc())\
            .limit(limit)\
            .all()
        
        return [
            {
                'id': r.id,
                'vehicleId': r.vehicle_id,
                'numberPlate': r.number_plate,
                'timestamp': r.timestamp,
                'direction': r.direction,
                'speed': r.speed
            }
            for r in records
        ]
    
    def get_stats(self) -> dict:
        """Get logger statistics"""
        return {
            'totalDetections': self.total_detections,
            'totalBatchesFlushed': self.total_batches_flushed,
            'pendingRecords': len(self.pending_records),
            'batchSize': self.batch_size,
            'batchEnabled': self.batch_enabled,
            'trackedVehicles': len(self.last_detections)
        }
    
    def clear_tracking(self):
        """Clear detection tracking (for testing/reset)"""
        self.last_detections.clear()
        self.pending_records.clear()


# Global detection logger instance
_detection_logger: Optional[VehicleDetectionLogger] = None


def get_detection_logger() -> VehicleDetectionLogger:
    """Get the global VehicleDetectionLogger instance"""
    global _detection_logger
    if _detection_logger is None:
        _detection_logger = VehicleDetectionLogger()
    return _detection_logger


def init_detection_logger(db_session: Session = None) -> VehicleDetectionLogger:
    """Initialize the global detection logger with database session"""
    global _detection_logger
    _detection_logger = VehicleDetectionLogger(db_session)
    return _detection_logger

