"""
Incident Routes - Post-incident vehicle tracking endpoints (FRD-08)

Endpoints:
- POST /api/incident/report - Report a vehicle incident
- GET /api/incident/{id} - Get incident details
- GET /api/incident/{id}/inference - Get vehicle inference results
- GET /api/incident/{id}/timeline - Get vehicle movement timeline
- GET /api/incidents - List all incidents
- POST /api/incident/{id}/resolve - Mark incident as resolved
- GET /api/incident/statistics - Get system statistics
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import time

from app.database.database import get_db

router = APIRouter(prefix="/api/incident", tags=["incident"])


# ============================================
# Global Component References
# ============================================

_incident_manager = None
_inference_engine = None
_detection_logger = None


def set_incident_components(
    incident_manager=None,
    inference_engine=None,
    detection_logger=None
):
    """Set incident system components"""
    global _incident_manager, _inference_engine, _detection_logger
    _incident_manager = incident_manager
    _inference_engine = inference_engine
    _detection_logger = detection_logger


# ============================================
# Request/Response Models
# ============================================

class IncidentReportRequest(BaseModel):
    """Request to report a vehicle incident"""
    numberPlate: str = Field(
        ...,
        description="Vehicle number plate to track",
        min_length=4,
        max_length=15
    )
    incidentTime: float = Field(
        ...,
        description="Approximate time of incident (Unix timestamp)"
    )
    incidentType: str = Field(
        default="HIT_AND_RUN",
        description="Type: HIT_AND_RUN, THEFT, SUSPICIOUS, ACCIDENT, OTHER"
    )
    location: Optional[str] = Field(
        None,
        description="Known location (junction/road ID)"
    )
    locationName: Optional[str] = Field(
        None,
        description="Human-readable location name"
    )
    lat: Optional[float] = Field(
        None,
        description="GPS latitude"
    )
    lon: Optional[float] = Field(
        None,
        description="GPS longitude"
    )
    description: Optional[str] = Field(
        None,
        description="Additional incident details"
    )


class IncidentReportResponse(BaseModel):
    """Response from incident report"""
    incidentId: str
    status: str
    message: str
    estimatedProcessingTime: float


class ProbableLocationResponse(BaseModel):
    """Probable vehicle location"""
    junctionId: str
    junctionName: Optional[str]
    lat: Optional[float]
    lon: Optional[float]
    confidence: float
    distance: int
    estimatedTravelTime: float


class DetectionHistoryResponse(BaseModel):
    """Detection record in history"""
    junctionId: str
    junctionName: Optional[str]
    timestamp: float
    direction: str
    lat: Optional[float]
    lon: Optional[float]


class InferenceResultResponse(BaseModel):
    """Vehicle location inference result"""
    incidentId: str
    numberPlate: str
    
    lastKnownLocation: Optional[str]
    lastKnownLocationName: Optional[str]
    lastSeenTime: Optional[float]
    lastSeenLat: Optional[float]
    lastSeenLon: Optional[float]
    
    timeElapsed: float
    
    probableLocations: List[ProbableLocationResponse]
    searchRadius: float
    searchCenterLat: Optional[float]
    searchCenterLon: Optional[float]
    
    detectionHistory: List[DetectionHistoryResponse]
    detectionCount: int
    
    confidence: float
    inferenceTimeMs: float
    processedAt: float


class IncidentDetailsResponse(BaseModel):
    """Full incident details"""
    id: str
    numberPlate: str
    incidentType: str
    incidentTime: float
    location: Optional[str]
    locationName: Optional[str]
    lat: Optional[float]
    lon: Optional[float]
    description: Optional[str]
    
    status: str
    reportedAt: float
    processedAt: Optional[float]
    resolvedAt: Optional[float]
    resolutionNotes: Optional[str]
    
    inferenceResult: Optional[InferenceResultResponse]


class IncidentListResponse(BaseModel):
    """Incident list response"""
    total: int
    incidents: List[IncidentDetailsResponse]


# ============================================
# Endpoints
# ============================================

@router.post("/report", response_model=IncidentReportResponse)
async def report_incident(request: IncidentReportRequest):
    """
    Report a vehicle incident
    
    Initiates tracking and inference for the specified vehicle.
    The system will query detection records to trace the vehicle's path.
    
    Response time: < 1 second
    Inference processing: < 5 seconds (async)
    """
    if not _incident_manager:
        raise HTTPException(
            status_code=503,
            detail="Incident system not initialized"
        )
    
    try:
        incident_id = await _incident_manager.create_incident(
            number_plate=request.numberPlate,
            incident_time=request.incidentTime,
            incident_type=request.incidentType,
            location_junction=request.location,
            location_name=request.locationName,
            location_lat=request.lat,
            location_lon=request.lon,
            description=request.description
        )
        
        return IncidentReportResponse(
            incidentId=incident_id,
            status="PROCESSING",
            message="Incident reported. Analyzing detection records...",
            estimatedProcessingTime=5.0
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create incident: {str(e)}"
        )


@router.get("/{incident_id}", response_model=IncidentDetailsResponse)
async def get_incident(incident_id: str):
    """
    Get incident details
    
    Returns full incident information including inference results if available.
    """
    if not _incident_manager:
        raise HTTPException(
            status_code=503,
            detail="Incident system not initialized"
        )
    
    incident = await _incident_manager.get_incident(incident_id)
    
    if not incident:
        raise HTTPException(
            status_code=404,
            detail=f"Incident not found: {incident_id}"
        )
    
    # Convert to response
    inference_result = None
    if incident.inference_result:
        ir = incident.inference_result
        inference_result = InferenceResultResponse(
            incidentId=ir.incident_id,
            numberPlate=ir.number_plate,
            lastKnownLocation=ir.last_known_junction,
            lastKnownLocationName=ir.last_known_junction_name,
            lastSeenTime=ir.last_seen_time,
            lastSeenLat=ir.last_seen_lat,
            lastSeenLon=ir.last_seen_lon,
            timeElapsed=ir.time_elapsed,
            probableLocations=[
                ProbableLocationResponse(
                    junctionId=loc.junction_id,
                    junctionName=loc.junction_name,
                    lat=loc.lat,
                    lon=loc.lon,
                    confidence=loc.confidence,
                    distance=loc.distance_from_last,
                    estimatedTravelTime=loc.estimated_travel_time
                )
                for loc in ir.probable_locations
            ],
            searchRadius=ir.search_radius,
            searchCenterLat=ir.search_center_lat,
            searchCenterLon=ir.search_center_lon,
            detectionHistory=[
                DetectionHistoryResponse(
                    junctionId=det.junction_id,
                    junctionName=det.junction_name,
                    timestamp=det.timestamp,
                    direction=det.direction,
                    lat=det.lat,
                    lon=det.lon
                )
                for det in ir.detection_history
            ],
            detectionCount=ir.detection_count,
            confidence=ir.overall_confidence,
            inferenceTimeMs=ir.inference_time_ms,
            processedAt=ir.generated_at
        )
    
    return IncidentDetailsResponse(
        id=incident.id,
        numberPlate=incident.number_plate,
        incidentType=incident.incident_type.value,
        incidentTime=incident.incident_time,
        location=incident.location_junction,
        locationName=incident.location_name,
        lat=incident.location_lat,
        lon=incident.location_lon,
        description=incident.description,
        status=incident.status.value,
        reportedAt=incident.reported_at,
        processedAt=incident.processed_at,
        resolvedAt=incident.resolved_at,
        resolutionNotes=incident.resolution_notes,
        inferenceResult=inference_result
    )


@router.get("/{incident_id}/inference", response_model=InferenceResultResponse)
async def get_inference_results(incident_id: str):
    """
    Get vehicle inference results
    
    Returns the analyzed location data for the incident vehicle:
    - Last known location from detection records
    - Probable current locations based on movement patterns
    - Detection history (junction crossings)
    - Confidence score
    
    Response time: < 500ms after processing complete
    """
    if not _incident_manager:
        raise HTTPException(
            status_code=503,
            detail="Incident system not initialized"
        )
    
    # Get incident first to check status
    incident = await _incident_manager.get_incident(incident_id)
    
    if not incident:
        raise HTTPException(
            status_code=404,
            detail=f"Incident not found: {incident_id}"
        )
    
    if incident.status.value == "PROCESSING":
        raise HTTPException(
            status_code=202,
            detail="Inference still processing. Try again in a few seconds."
        )
    
    result = await _incident_manager.get_inference_result(incident_id)
    
    if not result:
        raise HTTPException(
            status_code=404,
            detail="No inference result available"
        )
    
    return InferenceResultResponse(
        incidentId=result.incident_id,
        numberPlate=result.number_plate,
        lastKnownLocation=result.last_known_junction,
        lastKnownLocationName=result.last_known_junction_name,
        lastSeenTime=result.last_seen_time,
        lastSeenLat=result.last_seen_lat,
        lastSeenLon=result.last_seen_lon,
        timeElapsed=result.time_elapsed,
        probableLocations=[
            ProbableLocationResponse(
                junctionId=loc.junction_id,
                junctionName=loc.junction_name,
                lat=loc.lat,
                lon=loc.lon,
                confidence=loc.confidence,
                distance=loc.distance_from_last,
                estimatedTravelTime=loc.estimated_travel_time
            )
            for loc in result.probable_locations
        ],
        searchRadius=result.search_radius,
        searchCenterLat=result.search_center_lat,
        searchCenterLon=result.search_center_lon,
        detectionHistory=[
            DetectionHistoryResponse(
                junctionId=det.junction_id,
                junctionName=det.junction_name,
                timestamp=det.timestamp,
                direction=det.direction,
                lat=det.lat,
                lon=det.lon
            )
            for det in result.detection_history
        ],
        detectionCount=result.detection_count,
        confidence=result.overall_confidence,
        inferenceTimeMs=result.inference_time_ms,
        processedAt=result.generated_at
    )


@router.get("/{incident_id}/timeline", response_model=List[DetectionHistoryResponse])
async def get_incident_timeline(incident_id: str):
    """
    Get vehicle movement timeline for incident
    
    Returns chronological list of all detected movements
    for the incident vehicle.
    """
    if not _incident_manager:
        raise HTTPException(
            status_code=503,
            detail="Incident system not initialized"
        )
    
    result = await _incident_manager.get_inference_result(incident_id)
    
    if not result:
        return []
    
    return [
        DetectionHistoryResponse(
            junctionId=det.junction_id,
            junctionName=det.junction_name,
            timestamp=det.timestamp,
            direction=det.direction,
            lat=det.lat,
            lon=det.lon
        )
        for det in result.detection_history
    ]


@router.get("s", response_model=IncidentListResponse)
async def list_incidents(
    status: Optional[str] = Query(None, description="Filter by status (PROCESSING, COMPLETED, RESOLVED)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    """
    List all incidents
    
    Returns paginated list of reported incidents.
    """
    if not _incident_manager:
        raise HTTPException(
            status_code=503,
            detail="Incident system not initialized"
        )
    
    incidents = await _incident_manager.list_incidents(
        status=status,
        limit=limit,
        offset=offset
    )
    
    # Convert to response format
    response_incidents = []
    for incident in incidents:
        response_incidents.append(IncidentDetailsResponse(
            id=incident.id,
            numberPlate=incident.number_plate,
            incidentType=incident.incident_type.value,
            incidentTime=incident.incident_time,
            location=incident.location_junction,
            locationName=incident.location_name,
            lat=incident.location_lat,
            lon=incident.location_lon,
            description=incident.description,
            status=incident.status.value,
            reportedAt=incident.reported_at,
            processedAt=incident.processed_at,
            resolvedAt=incident.resolved_at,
            resolutionNotes=incident.resolution_notes,
            inferenceResult=None  # Don't include full inference in list
        ))
    
    return IncidentListResponse(
        total=len(response_incidents),
        incidents=response_incidents
    )


@router.post("/{incident_id}/resolve")
async def resolve_incident(
    incident_id: str,
    resolution: Optional[str] = Query(None, description="Resolution notes")
):
    """
    Mark incident as resolved
    
    Updates the incident status and adds resolution notes.
    """
    if not _incident_manager:
        raise HTTPException(
            status_code=503,
            detail="Incident system not initialized"
        )
    
    success = await _incident_manager.resolve_incident(
        incident_id=incident_id,
        resolution_notes=resolution
    )
    
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Incident not found: {incident_id}"
        )
    
    return {
        "incidentId": incident_id,
        "status": "RESOLVED",
        "resolution": resolution,
        "resolvedAt": time.time()
    }


@router.get("/statistics", response_model=Dict[str, Any])
async def get_incident_statistics():
    """
    Get incident system statistics
    
    Returns statistics for detection logging, incident management,
    and inference engine.
    """
    stats = {
        "timestamp": time.time(),
        "incidentManager": None,
        "inferenceEngine": None,
        "detectionLogger": None
    }
    
    if _incident_manager:
        stats["incidentManager"] = _incident_manager.get_statistics()
    
    if _inference_engine:
        stats["inferenceEngine"] = _inference_engine.get_statistics()
    
    if _detection_logger:
        stats["detectionLogger"] = _detection_logger.get_statistics()
    
    return stats
