"""
Detection History Logger (FRD-08)

Logs vehicle detections at junctions for post-incident reconstruction.
Each time a vehicle passes through a junction, it is recorded with:
- Vehicle ID and number plate
- Junction ID and direction
- Timestamp and position
- Speed and vehicle type

Privacy principles:
- 24-hour retention policy
- Junction-based only (not continuous GPS tracking)
- Used only for incident-triggered investigations
"""

import time
import uuid
from dataclasses import dataclass
from typing import List, Optional
import asyncio

from app.database.models import DetectionRecord
from app.database.database import SessionLocal


@dataclass
class VehicleDetectionEvent:
    """Single vehicle detection event at a junction"""
    vehicle_id: str
    number_plate: str
    junction_id: str
    direction: str  # N, E, S, W
    timestamp: float
    position_x: float
    position_y: float
    speed: float
    vehicle_type: str
    incoming_road: Optional[str] = None
    outgoing_road: Optional[str] = None


class DetectionHistoryLogger:
    """
    Log vehicle detections for post-incident reconstruction (FRD-08)
    
    Features:
    - Batch inserts for performance
    - 24-hour retention policy
    - In-memory buffer with periodic flush
    - Statistics tracking
    
    Usage:
        logger = DetectionHistoryLogger()
        logger.log_detection(vehicle_id, junction_id, ...)
    """
    
    def __init__(
        self,
        buffer_size: int = 100,
        flush_interval: float = 5.0,
        retention_hours: int = 24
    ):
        """
        Initialize detection logger
        
        Args:
            buffer_size: Number of detections before flush
            flush_interval: Max seconds between flushes
            retention_hours: Hours to retain records
        """
        self.buffer_size = buffer_size
        self.flush_interval = flush_interval
        self.retention_hours = retention_hours
        
        # In-memory buffer for batch inserts
        self._buffer: List[VehicleDetectionEvent] = []
        self._buffer_lock = asyncio.Lock()
        
        # Statistics
        self.total_detections = 0
        self.total_flushes = 0
        self.last_flush_time = time.time()
        
        # Background task
        self._flush_task: Optional[asyncio.Task] = None
        self._running = False
        
        print("[OK] Detection History Logger initialized")
    
    async def start(self):
        """Start background flush task"""
        if self._running:
            return
        
        self._running = True
        self._flush_task = asyncio.create_task(self._periodic_flush())
        print("[DETECTION] Background flush task started")
    
    async def stop(self):
        """Stop logger and flush remaining buffer"""
        self._running = False
        
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        
        # Final flush
        await self._flush_buffer()
        print("[DETECTION] Logger stopped, buffer flushed")
    
    def log_detection(
        self,
        vehicle_id: str,
        number_plate: str,
        junction_id: str,
        direction: str,
        position_x: float,
        position_y: float,
        speed: float = 0.0,
        vehicle_type: str = "CAR",
        incoming_road: Optional[str] = None,
        outgoing_road: Optional[str] = None
    ):
        """
        Log a vehicle detection at a junction (synchronous wrapper)
        
        Args:
            vehicle_id: Unique vehicle identifier
            number_plate: Vehicle registration number
            junction_id: Junction where detected
            direction: Direction of travel (N/E/S/W)
            position_x: X coordinate
            position_y: Y coordinate
            speed: Vehicle speed
            vehicle_type: Type of vehicle
            incoming_road: Road entering from
            outgoing_road: Road exiting to
        """
        detection = VehicleDetectionEvent(
            vehicle_id=vehicle_id,
            number_plate=number_plate,
            junction_id=junction_id,
            direction=direction,
            timestamp=time.time(),
            position_x=position_x,
            position_y=position_y,
            speed=speed,
            vehicle_type=vehicle_type,
            incoming_road=incoming_road,
            outgoing_road=outgoing_road
        )
        
        # Add to buffer (thread-safe for sync context)
        self._buffer.append(detection)
        self.total_detections += 1
        
        # Check if buffer needs flush
        if len(self._buffer) >= self.buffer_size:
            # Schedule async flush
            asyncio.create_task(self._flush_buffer())
    
    async def log_detection_async(
        self,
        vehicle_id: str,
        number_plate: str,
        junction_id: str,
        direction: str,
        position_x: float,
        position_y: float,
        speed: float = 0.0,
        vehicle_type: str = "CAR",
        incoming_road: Optional[str] = None,
        outgoing_road: Optional[str] = None
    ):
        """Async version of log_detection"""
        detection = VehicleDetectionEvent(
            vehicle_id=vehicle_id,
            number_plate=number_plate,
            junction_id=junction_id,
            direction=direction,
            timestamp=time.time(),
            position_x=position_x,
            position_y=position_y,
            speed=speed,
            vehicle_type=vehicle_type,
            incoming_road=incoming_road,
            outgoing_road=outgoing_road
        )
        
        async with self._buffer_lock:
            self._buffer.append(detection)
            self.total_detections += 1
            
            if len(self._buffer) >= self.buffer_size:
                await self._flush_buffer()
    
    async def _periodic_flush(self):
        """Background task to periodically flush buffer"""
        while self._running:
            try:
                await asyncio.sleep(self.flush_interval)
                
                if self._buffer:
                    await self._flush_buffer()
                
                # Cleanup old records periodically
                await self._cleanup_old_records()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[DETECTION] Periodic flush error: {e}")
    
    async def _flush_buffer(self):
        """Flush detection buffer to database"""
        async with self._buffer_lock:
            if not self._buffer:
                return
            
            buffer_copy = self._buffer.copy()
            self._buffer = []
        
        db = SessionLocal()
        
        try:
            # Convert to DB records
            records = [
                DetectionRecord(
                    id=f"det-{uuid.uuid4().hex[:12]}",
                    vehicle_id=d.vehicle_id,
                    number_plate=d.number_plate,
                    junction_id=d.junction_id,
                    direction=d.direction,
                    timestamp=d.timestamp,
                    position_x=d.position_x,
                    position_y=d.position_y,
                    speed=d.speed,
                    vehicle_type=d.vehicle_type,
                    incoming_road=d.incoming_road,
                    outgoing_road=d.outgoing_road,
                    violation_detected=False
                )
                for d in buffer_copy
            ]
            
            # Batch insert
            db.bulk_save_objects(records)
            db.commit()
            
            self.total_flushes += 1
            self.last_flush_time = time.time()
            
            print(f"📝 [DETECTION] Flushed {len(records)} detections to database")
            
        except Exception as e:
            print(f"[ERROR] [DETECTION] Flush error: {e}")
            db.rollback()
            
            # Re-add failed records to buffer
            async with self._buffer_lock:
                self._buffer = buffer_copy + self._buffer
        finally:
            db.close()
    
    async def _cleanup_old_records(self):
        """Remove records older than retention period"""
        cutoff_time = time.time() - (self.retention_hours * 3600)
        
        db = SessionLocal()
        
        try:
            deleted = db.query(DetectionRecord)\
                .filter(DetectionRecord.timestamp < cutoff_time)\
                .delete(synchronize_session=False)
            
            if deleted > 0:
                db.commit()
                print(f"🗑️ [DETECTION] Cleaned up {deleted} old records")
        except Exception as e:
            print(f"[DETECTION] Cleanup error: {e}")
            db.rollback()
        finally:
            db.close()
    
    def get_statistics(self) -> dict:
        """Get logging statistics"""
        return {
            'totalDetections': self.total_detections,
            'totalFlushes': self.total_flushes,
            'bufferSize': len(self._buffer),
            'lastFlushTime': self.last_flush_time,
            'retentionHours': self.retention_hours
        }
    
    async def force_flush(self):
        """Force flush buffer (e.g., on shutdown)"""
        await self._flush_buffer()


# ============================================
# Global Instance Management
# ============================================

_detection_logger: Optional[DetectionHistoryLogger] = None


def init_detection_logger(config: dict = None) -> DetectionHistoryLogger:
    """Initialize global detection logger"""
    global _detection_logger
    
    config = config or {}
    
    _detection_logger = DetectionHistoryLogger(
        buffer_size=config.get('bufferSize', 100),
        flush_interval=config.get('flushInterval', 5.0),
        retention_hours=config.get('retentionHours', 24)
    )
    
    return _detection_logger


def get_detection_logger() -> Optional[DetectionHistoryLogger]:
    """Get global detection logger"""
    return _detection_logger


def set_detection_logger(logger: DetectionHistoryLogger):
    """Set global detection logger"""
    global _detection_logger
    _detection_logger = logger

