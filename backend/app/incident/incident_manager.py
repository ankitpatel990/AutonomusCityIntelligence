"""
Incident Manager (FRD-08)

Manages traffic incident records for post-incident vehicle tracking.
Provides CRUD operations for incidents and triggers inference processing.

Features:
- Create and track incidents
- Associate vehicles with incidents
- Trigger inference engine
- Status management
- Resolution tracking
"""

import time
import uuid
import asyncio
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
import json

from app.database.database import SessionLocal
from app.database.models import Incident as IncidentModel, InferenceResult as InferenceResultModel


class IncidentType(str, Enum):
    """Types of traffic incidents"""
    HIT_AND_RUN = "HIT_AND_RUN"
    THEFT = "THEFT"
    SUSPICIOUS = "SUSPICIOUS"
    ACCIDENT = "ACCIDENT"
    OTHER = "OTHER"


class IncidentStatus(str, Enum):
    """Incident processing status"""
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    RESOLVED = "RESOLVED"
    FAILED = "FAILED"


@dataclass
class ProbableLocation:
    """A probable current location of the vehicle"""
    junction_id: str
    junction_name: str
    lat: float
    lon: float
    confidence: float  # 0-100
    distance_from_last: int  # junction hops
    estimated_travel_time: float  # seconds


@dataclass
class DetectionHistoryItem:
    """Single detection record in history"""
    junction_id: str
    junction_name: Optional[str]
    timestamp: float
    direction: str
    lat: Optional[float] = None
    lon: Optional[float] = None


@dataclass
class IncidentInferenceResult:
    """Result of vehicle inference for an incident"""
    incident_id: str
    number_plate: str
    
    last_known_junction: Optional[str]
    last_known_junction_name: Optional[str]
    last_seen_time: Optional[float]
    last_seen_lat: Optional[float]
    last_seen_lon: Optional[float]
    
    time_elapsed: float  # seconds since last detection
    
    probable_locations: List[ProbableLocation]
    search_radius: float  # km
    search_center_lat: Optional[float]
    search_center_lon: Optional[float]
    
    detection_history: List[DetectionHistoryItem]
    detection_count: int
    
    overall_confidence: float  # 0-100
    inference_time_ms: float
    generated_at: float


@dataclass
class IncidentRecord:
    """Complete incident record"""
    id: str
    number_plate: str
    incident_type: IncidentType
    incident_time: float
    
    location_junction: Optional[str]
    location_road: Optional[str]
    location_name: Optional[str]
    location_lat: Optional[float]
    location_lon: Optional[float]
    
    description: Optional[str]
    
    status: IncidentStatus
    reported_at: float
    processed_at: Optional[float]
    resolved_at: Optional[float]
    resolution_notes: Optional[str]
    
    inference_result: Optional[IncidentInferenceResult] = None


class IncidentManager:
    """
    Manage traffic incidents (FRD-08)
    
    Responsibilities:
    - Create and track incidents
    - Query detection history
    - Trigger inference engine
    - Manage incident lifecycle
    
    Usage:
        manager = IncidentManager(inference_engine)
        incident_id = await manager.create_incident(...)
        result = await manager.get_inference_result(incident_id)
    """
    
    def __init__(self, inference_engine=None, ws_emitter=None):
        """
        Initialize incident manager
        
        Args:
            inference_engine: VehicleInferenceEngine instance
            ws_emitter: WebSocket emitter for real-time updates
        """
        self.inference_engine = inference_engine
        self.ws_emitter = ws_emitter
        
        # In-memory cache for active incidents
        self._active_incidents: Dict[str, IncidentRecord] = {}
        
        # Statistics
        self.total_incidents = 0
        self.total_resolved = 0
        
        print("[OK] Incident Manager initialized")
    
    def set_inference_engine(self, engine):
        """Set inference engine after initialization"""
        self.inference_engine = engine
    
    def set_ws_emitter(self, emitter):
        """Set WebSocket emitter"""
        self.ws_emitter = emitter
    
    async def create_incident(
        self,
        number_plate: str,
        incident_time: float,
        incident_type: str = "HIT_AND_RUN",
        location_junction: Optional[str] = None,
        location_road: Optional[str] = None,
        location_name: Optional[str] = None,
        location_lat: Optional[float] = None,
        location_lon: Optional[float] = None,
        description: Optional[str] = None
    ) -> str:
        """
        Create a new incident and trigger inference
        
        Args:
            number_plate: Vehicle number plate to track
            incident_time: When incident occurred (timestamp)
            incident_type: Type of incident
            location_*: Location details
            description: Additional description
        
        Returns:
            incident_id: Unique incident identifier
        """
        # Generate unique ID
        incident_id = f"inc-{uuid.uuid4().hex[:12]}"
        
        # Parse incident type
        try:
            inc_type = IncidentType(incident_type.upper())
        except ValueError:
            inc_type = IncidentType.OTHER
        
        # Create incident record
        incident = IncidentRecord(
            id=incident_id,
            number_plate=number_plate.upper().replace(" ", ""),
            incident_type=inc_type,
            incident_time=incident_time,
            location_junction=location_junction,
            location_road=location_road,
            location_name=location_name,
            location_lat=location_lat,
            location_lon=location_lon,
            description=description,
            status=IncidentStatus.PROCESSING,
            reported_at=time.time(),
            processed_at=None,
            resolved_at=None,
            resolution_notes=None
        )
        
        # Store in cache
        self._active_incidents[incident_id] = incident
        self.total_incidents += 1
        
        # Save to database
        await self._save_incident_to_db(incident)
        
        print(f"📋 [INCIDENT] Created: {incident_id}")
        print(f"   Plate: {number_plate}")
        print(f"   Type: {inc_type.value}")
        print(f"   Time: {time.ctime(incident_time)}")
        
        # Trigger inference asynchronously
        asyncio.create_task(self._process_incident(incident))
        
        # Emit WebSocket event
        if self.ws_emitter:
            await self.ws_emitter.emit('incident:created', {
                'incidentId': incident_id,
                'numberPlate': number_plate,
                'type': inc_type.value,
                'status': 'PROCESSING'
            })
        
        return incident_id
    
    async def _process_incident(self, incident: IncidentRecord):
        """Process incident through inference engine"""
        if not self.inference_engine:
            print(f"[INCIDENT] No inference engine - skipping {incident.id}")
            incident.status = IncidentStatus.FAILED
            await self._update_incident_in_db(incident)
            return
        
        try:
            # Run inference
            result = await self.inference_engine.process_incident(
                incident_id=incident.id,
                number_plate=incident.number_plate,
                incident_time=incident.incident_time,
                incident_location=(incident.location_lat, incident.location_lon)
                if incident.location_lat else None
            )
            
            if result:
                incident.inference_result = result
                incident.status = IncidentStatus.COMPLETED
                incident.processed_at = time.time()
                
                print(f"[OK] [INCIDENT] {incident.id} processed - "
                      f"{len(result.probable_locations)} locations found")
                
                # Emit completion event
                if self.ws_emitter:
                    await self.ws_emitter.emit('incident:completed', {
                        'incidentId': incident.id,
                        'status': 'COMPLETED',
                        'lastKnownLocation': result.last_known_junction,
                        'probableLocationsCount': len(result.probable_locations),
                        'confidence': result.overall_confidence
                    })
            else:
                incident.status = IncidentStatus.COMPLETED
                incident.processed_at = time.time()
                print(f"[WARN] [INCIDENT] {incident.id} - no detection history found")
            
        except Exception as e:
            print(f"[ERROR] [INCIDENT] Processing error for {incident.id}: {e}")
            incident.status = IncidentStatus.FAILED
        
        # Update in database
        await self._update_incident_in_db(incident)
    
    async def get_incident(self, incident_id: str) -> Optional[IncidentRecord]:
        """Get incident by ID"""
        # Check cache first
        if incident_id in self._active_incidents:
            return self._active_incidents[incident_id]
        
        # Load from database
        return await self._load_incident_from_db(incident_id)
    
    async def get_inference_result(self, incident_id: str) -> Optional[IncidentInferenceResult]:
        """Get inference result for incident"""
        incident = await self.get_incident(incident_id)
        
        if incident:
            return incident.inference_result
        
        return None
    
    async def resolve_incident(
        self,
        incident_id: str,
        resolution_notes: Optional[str] = None
    ) -> bool:
        """Mark incident as resolved"""
        incident = await self.get_incident(incident_id)
        
        if not incident:
            return False
        
        incident.status = IncidentStatus.RESOLVED
        incident.resolved_at = time.time()
        incident.resolution_notes = resolution_notes
        
        self.total_resolved += 1
        
        await self._update_incident_in_db(incident)
        
        print(f"[OK] [INCIDENT] {incident_id} resolved")
        
        # Emit event
        if self.ws_emitter:
            await self.ws_emitter.emit('incident:resolved', {
                'incidentId': incident_id,
                'resolvedAt': incident.resolved_at,
                'resolution': resolution_notes
            })
        
        return True
    
    async def list_incidents(
        self,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[IncidentRecord]:
        """List incidents with optional status filter"""
        db = SessionLocal()
        
        try:
            query = db.query(IncidentModel)
            
            if status:
                query = query.filter(IncidentModel.status == status.upper())
            
            query = query.order_by(IncidentModel.reported_at.desc())
            query = query.offset(offset).limit(limit)
            
            db_incidents = query.all()
            
            incidents = []
            for db_inc in db_incidents:
                incident = self._db_to_record(db_inc)
                incidents.append(incident)
            
            return incidents
            
        finally:
            db.close()
    
    async def _save_incident_to_db(self, incident: IncidentRecord):
        """Save incident to database"""
        db = SessionLocal()
        
        try:
            db_incident = IncidentModel(
                id=incident.id,
                number_plate=incident.number_plate,
                incident_type=incident.incident_type.value,
                incident_time=incident.incident_time,
                location_junction=incident.location_junction,
                location_road=incident.location_road,
                location_name=incident.location_name,
                location_lat=incident.location_lat,
                location_lon=incident.location_lon,
                description=incident.description,
                status=incident.status.value,
                reported_at=incident.reported_at
            )
            
            db.add(db_incident)
            db.commit()
            
        except Exception as e:
            print(f"[INCIDENT] DB save error: {e}")
            db.rollback()
        finally:
            db.close()
    
    async def _update_incident_in_db(self, incident: IncidentRecord):
        """Update incident in database"""
        db = SessionLocal()
        
        try:
            db_incident = db.query(IncidentModel).filter_by(id=incident.id).first()
            
            if db_incident:
                db_incident.status = incident.status.value
                db_incident.processed_at = incident.processed_at
                db_incident.resolved_at = incident.resolved_at
                db_incident.resolution_notes = incident.resolution_notes
                
                # Save inference result if available
                if incident.inference_result:
                    await self._save_inference_result(incident.inference_result)
                    db_incident.inference_result_id = incident.inference_result.incident_id
                
                db.commit()
            
        except Exception as e:
            print(f"[INCIDENT] DB update error: {e}")
            db.rollback()
        finally:
            db.close()
    
    async def _save_inference_result(self, result: IncidentInferenceResult):
        """Save inference result to database"""
        db = SessionLocal()
        
        try:
            result_id = f"inf-{result.incident_id}"
            
            db_result = InferenceResultModel(
                id=result_id,
                incident_id=result.incident_id,
                number_plate=result.number_plate,
                last_known_junction=result.last_known_junction,
                last_seen_time=result.last_seen_time,
                last_seen_lat=result.last_seen_lat,
                last_seen_lon=result.last_seen_lon,
                time_elapsed=result.time_elapsed,
                probable_locations_json=json.dumps([
                    {
                        'junctionId': loc.junction_id,
                        'junctionName': loc.junction_name,
                        'lat': loc.lat,
                        'lon': loc.lon,
                        'confidence': loc.confidence,
                        'distance': loc.distance_from_last,
                        'travelTime': loc.estimated_travel_time
                    }
                    for loc in result.probable_locations
                ]),
                search_radius=result.search_radius,
                search_center_lat=result.search_center_lat,
                search_center_lon=result.search_center_lon,
                detection_history_json=json.dumps([
                    {
                        'junctionId': det.junction_id,
                        'junctionName': det.junction_name,
                        'timestamp': det.timestamp,
                        'direction': det.direction,
                        'lat': det.lat,
                        'lon': det.lon
                    }
                    for det in result.detection_history
                ]),
                detection_count=result.detection_count,
                overall_confidence=result.overall_confidence,
                inference_time_ms=result.inference_time_ms,
                generated_at=result.generated_at
            )
            
            db.merge(db_result)  # Use merge for upsert
            db.commit()
            
        except Exception as e:
            print(f"[INCIDENT] Inference result save error: {e}")
            db.rollback()
        finally:
            db.close()
    
    async def _load_incident_from_db(self, incident_id: str) -> Optional[IncidentRecord]:
        """Load incident from database"""
        db = SessionLocal()
        
        try:
            db_incident = db.query(IncidentModel).filter_by(id=incident_id).first()
            
            if db_incident:
                incident = self._db_to_record(db_incident)
                
                # Load inference result if available
                if db_incident.inference_result_id:
                    db_result = db.query(InferenceResultModel)\
                        .filter_by(id=db_incident.inference_result_id).first()
                    
                    if db_result:
                        incident.inference_result = self._db_to_inference_result(db_result)
                
                return incident
            
            return None
            
        finally:
            db.close()
    
    def _db_to_record(self, db_incident: IncidentModel) -> IncidentRecord:
        """Convert DB model to dataclass"""
        return IncidentRecord(
            id=db_incident.id,
            number_plate=db_incident.number_plate,
            incident_type=IncidentType(db_incident.incident_type),
            incident_time=db_incident.incident_time,
            location_junction=db_incident.location_junction,
            location_road=db_incident.location_road,
            location_name=db_incident.location_name,
            location_lat=db_incident.location_lat,
            location_lon=db_incident.location_lon,
            description=db_incident.description,
            status=IncidentStatus(db_incident.status),
            reported_at=db_incident.reported_at,
            processed_at=db_incident.processed_at,
            resolved_at=db_incident.resolved_at,
            resolution_notes=db_incident.resolution_notes
        )
    
    def _db_to_inference_result(self, db_result: InferenceResultModel) -> IncidentInferenceResult:
        """Convert DB inference result to dataclass"""
        # Parse JSON fields
        probable_locations = []
        if db_result.probable_locations_json:
            for loc in json.loads(db_result.probable_locations_json):
                probable_locations.append(ProbableLocation(
                    junction_id=loc['junctionId'],
                    junction_name=loc.get('junctionName', ''),
                    lat=loc.get('lat', 0),
                    lon=loc.get('lon', 0),
                    confidence=loc['confidence'],
                    distance_from_last=loc.get('distance', 0),
                    estimated_travel_time=loc.get('travelTime', 0)
                ))
        
        detection_history = []
        if db_result.detection_history_json:
            for det in json.loads(db_result.detection_history_json):
                detection_history.append(DetectionHistoryItem(
                    junction_id=det['junctionId'],
                    junction_name=det.get('junctionName'),
                    timestamp=det['timestamp'],
                    direction=det['direction'],
                    lat=det.get('lat'),
                    lon=det.get('lon')
                ))
        
        return IncidentInferenceResult(
            incident_id=db_result.incident_id,
            number_plate=db_result.number_plate,
            last_known_junction=db_result.last_known_junction,
            last_known_junction_name=None,  # Not stored separately
            last_seen_time=db_result.last_seen_time,
            last_seen_lat=db_result.last_seen_lat,
            last_seen_lon=db_result.last_seen_lon,
            time_elapsed=db_result.time_elapsed or 0,
            probable_locations=probable_locations,
            search_radius=db_result.search_radius or 0,
            search_center_lat=db_result.search_center_lat,
            search_center_lon=db_result.search_center_lon,
            detection_history=detection_history,
            detection_count=db_result.detection_count or 0,
            overall_confidence=db_result.overall_confidence or 0,
            inference_time_ms=db_result.inference_time_ms or 0,
            generated_at=db_result.generated_at or 0
        )
    
    def get_statistics(self) -> dict:
        """Get incident manager statistics"""
        return {
            'totalIncidents': self.total_incidents,
            'totalResolved': self.total_resolved,
            'activeIncidents': len(self._active_incidents),
            'hasInferenceEngine': self.inference_engine is not None
        }


# ============================================
# Global Instance Management
# ============================================

_incident_manager: Optional[IncidentManager] = None


def init_incident_manager(
    inference_engine=None,
    ws_emitter=None
) -> IncidentManager:
    """Initialize global incident manager"""
    global _incident_manager
    
    _incident_manager = IncidentManager(
        inference_engine=inference_engine,
        ws_emitter=ws_emitter
    )
    
    return _incident_manager


def get_incident_manager() -> Optional[IncidentManager]:
    """Get global incident manager"""
    return _incident_manager


def set_incident_manager(manager: IncidentManager):
    """Set global incident manager"""
    global _incident_manager
    _incident_manager = manager

