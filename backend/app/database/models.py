"""
SQLAlchemy ORM Models

This module defines all database tables for the Traffic Intelligence System.
Includes models for:
- Detection records (vehicle tracking)
- Vehicle owners (mock data)
- Violations and challans
- Agent logs
- System events
- Map and API cache
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, Index
from sqlalchemy.sql import func
from .database import Base


class DetectionRecord(Base):
    """
    Vehicle detection at junctions (FRD-08)
    
    Records each time a vehicle passes through a junction.
    Used for post-incident route reconstruction.
    """
    __tablename__ = "detection_records"
    
    id = Column(String, primary_key=True)
    vehicle_id = Column(String, nullable=False)
    number_plate = Column(String, nullable=False, index=True)
    junction_id = Column(String, nullable=False, index=True)
    
    timestamp = Column(Float, nullable=False, index=True)
    direction = Column(String, nullable=False)  # N, E, S, W
    incoming_road = Column(String)
    outgoing_road = Column(String)
    
    speed = Column(Float)
    position_x = Column(Float)
    position_y = Column(Float)
    vehicle_type = Column(String)
    violation_detected = Column(Boolean, default=False)
    
    created_at = Column(DateTime, server_default=func.now())
    
    __table_args__ = (
        Index('idx_detection_plate_time', 'number_plate', 'timestamp'),
        Index('idx_detection_junction_time', 'junction_id', 'timestamp'),
    )


class VehicleOwner(Base):
    """
    Mock vehicle owner data (FRD-09)
    
    Simulates a vehicle registration database for challan system.
    """
    __tablename__ = "vehicle_owners"
    
    number_plate = Column(String, primary_key=True)
    owner_name = Column(String, nullable=False)
    contact = Column(String, nullable=False)
    email = Column(String)
    address = Column(Text)
    wallet_balance = Column(Float, default=1000.0)
    total_challans = Column(Integer, default=0)
    total_fines_paid = Column(Float, default=0.0)
    registration_date = Column(DateTime, server_default=func.now())


class Violation(Base):
    """
    Traffic violations (FRD-09)
    
    Records detected traffic violations before challan generation.
    """
    __tablename__ = "violations"
    
    id = Column(String, primary_key=True)
    vehicle_id = Column(String, nullable=False)
    number_plate = Column(String, nullable=False, index=True)
    
    violation_type = Column(String, nullable=False)  # RED_LIGHT, SPEEDING, etc.
    severity = Column(String, nullable=False)  # LOW, MEDIUM, HIGH
    
    location = Column(String, nullable=False)
    junction_id = Column(String)
    road_id = Column(String)
    position_x = Column(Float)
    position_y = Column(Float)
    
    timestamp = Column(Float, nullable=False, index=True)
    
    evidence_speed = Column(Float)
    evidence_speed_limit = Column(Float)
    evidence_signal_state = Column(String)
    evidence_snapshot = Column(Text)  # JSON
    
    processed = Column(Boolean, default=False, index=True)
    challan_id = Column(String, ForeignKey('challans.challan_id'))
    
    created_at = Column(DateTime, server_default=func.now())


class Challan(Base):
    """
    Digital challans (FRD-09)
    
    Generated from violations, tracks payment status.
    """
    __tablename__ = "challans"
    
    challan_id = Column(String, primary_key=True)
    violation_id = Column(String, ForeignKey('violations.id'), nullable=False)
    
    number_plate = Column(String, ForeignKey('vehicle_owners.number_plate'), nullable=False, index=True)
    owner_name = Column(String, nullable=False)
    
    violation_type = Column(String, nullable=False)
    violation_description = Column(Text)
    fine_amount = Column(Float, nullable=False)
    
    location = Column(String, nullable=False)
    violation_timestamp = Column(Float, nullable=False)
    
    status = Column(String, default='ISSUED', index=True)  # ISSUED, PAID, PENDING, CANCELLED
    payment_timestamp = Column(Float)
    transaction_id = Column(String)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())


class ChallanTransaction(Base):
    """
    Challan payment transactions (FRD-09)
    
    Records payment attempts and wallet deductions.
    """
    __tablename__ = "challan_transactions"
    
    transaction_id = Column(String, primary_key=True)
    challan_id = Column(String, ForeignKey('challans.challan_id'), nullable=False, index=True)
    number_plate = Column(String, nullable=False, index=True)
    
    amount = Column(Float, nullable=False)
    previous_balance = Column(Float, nullable=False)
    new_balance = Column(Float, nullable=False)
    
    timestamp = Column(Float, nullable=False)
    status = Column(String, default='SUCCESS')  # SUCCESS, FAILED, PENDING
    failure_reason = Column(Text)
    
    created_at = Column(DateTime, server_default=func.now())


class AgentLog(Base):
    """
    Agent decision logs (FRD-03)
    
    Records each decision cycle of the autonomous agent.
    """
    __tablename__ = "agent_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(Float, nullable=False, index=True)
    
    mode = Column(String, nullable=False)  # NORMAL, EMERGENCY, FAIL_SAFE
    strategy = Column(String, nullable=False)  # RL, RULE_BASED
    
    decision_latency = Column(Float)  # ms
    decisions_json = Column(Text)  # JSON array of signal decisions
    
    state_summary_json = Column(Text)  # JSON summary of perceived state
    
    created_at = Column(DateTime, server_default=func.now())
    
    __table_args__ = (
        Index('idx_agent_log_time', 'timestamp'),
    )


class SystemEvent(Base):
    """
    System events log (FRD-05)
    
    Records important system events: mode changes, errors, alerts.
    """
    __tablename__ = "system_events"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(Float, nullable=False, index=True)
    
    event_type = Column(String, nullable=False, index=True)  # MODE_CHANGE, ERROR, ALERT, etc.
    severity = Column(String, nullable=False)  # INFO, WARNING, ERROR, CRITICAL
    
    message = Column(Text)
    metadata_json = Column(Text)  # Additional JSON data
    
    created_at = Column(DateTime, server_default=func.now())


class MapCache(Base):
    """
    Cache for loaded OSM map data (FRD-01 v2.0)
    
    Stores downloaded OpenStreetMap data to avoid repeated API calls.
    """
    __tablename__ = "map_cache"
    
    area_id = Column(String, primary_key=True)
    area_name = Column(String, nullable=False, index=True)
    
    bounds_json = Column(Text, nullable=False)  # JSON: {north, south, east, west}
    map_data_json = Column(Text, nullable=False)  # JSON: {junctions, roads}
    
    junction_count = Column(Integer, nullable=False)
    road_count = Column(Integer, nullable=False)
    
    cached_at = Column(DateTime, server_default=func.now())
    last_accessed = Column(DateTime, onupdate=func.now())


class APICache(Base):
    """
    Cache for TomTom/Google API responses (FRD-01 v2.0)
    
    Caches live traffic API responses to reduce API calls.
    """
    __tablename__ = "api_cache"
    
    cache_key = Column(String, primary_key=True)  # Format: "tomtom_road_{road_id}"
    response_data = Column(Text, nullable=False)  # JSON: LiveTrafficData
    
    expires_at = Column(Float, nullable=False, index=True)  # Unix timestamp
    created_at = Column(DateTime, server_default=func.now())


class TrafficHistory(Base):
    """
    Historical traffic data for analysis (FRD-01 v2.0)
    
    Stores historical traffic data for trend analysis and prediction.
    """
    __tablename__ = "traffic_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    road_id = Column(String, nullable=False, index=True)
    
    congestion_level = Column(String, nullable=False)  # LOW/MEDIUM/HIGH/JAM
    current_speed = Column(Float)
    vehicle_count = Column(Integer)
    density_score = Column(Float)
    
    timestamp = Column(Float, nullable=False, index=True)
    source = Column(String, nullable=False)  # API/SIMULATION/MANUAL
    
    created_at = Column(DateTime, server_default=func.now())
    
    __table_args__ = (
        Index('idx_traffic_road_time', 'road_id', 'timestamp'),
    )


# ============================================
# Post-Incident Tracking Models (FRD-08)
# ============================================

class Incident(Base):
    """
    Traffic incident records (FRD-08)
    
    Records reported incidents for vehicle tracking and inference.
    """
    __tablename__ = "incidents"
    
    id = Column(String, primary_key=True)
    number_plate = Column(String, nullable=False, index=True)
    
    incident_type = Column(String, nullable=False)  # HIT_AND_RUN, THEFT, SUSPICIOUS, OTHER
    incident_time = Column(Float, nullable=False)  # When incident occurred
    
    location_junction = Column(String)  # Junction ID if known
    location_road = Column(String)  # Road ID if known
    location_name = Column(String)  # Human-readable address
    location_lat = Column(Float)  # GPS latitude
    location_lon = Column(Float)  # GPS longitude
    
    description = Column(Text)
    
    status = Column(String, default='PROCESSING', index=True)  # PROCESSING, COMPLETED, RESOLVED
    reported_at = Column(Float, nullable=False)  # When reported
    processed_at = Column(Float)  # When inference completed
    resolved_at = Column(Float)  # When resolved
    resolution_notes = Column(Text)
    
    inference_result_id = Column(String, ForeignKey('inference_results.id'))
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    __table_args__ = (
        Index('idx_incident_plate_time', 'number_plate', 'incident_time'),
    )


class InferenceResult(Base):
    """
    Vehicle location inference results (FRD-08)
    
    Stores the analysis results from post-incident tracking.
    """
    __tablename__ = "inference_results"
    
    id = Column(String, primary_key=True)
    incident_id = Column(String, nullable=False, index=True)
    number_plate = Column(String, nullable=False, index=True)
    
    # Last known location
    last_known_junction = Column(String)
    last_known_road = Column(String)
    last_seen_time = Column(Float)
    last_seen_lat = Column(Float)
    last_seen_lon = Column(Float)
    
    # Time elapsed since last detection
    time_elapsed = Column(Float)  # seconds
    
    # Probable locations (JSON array)
    probable_locations_json = Column(Text)  # JSON: [{"junction_id", "confidence", "distance", "lat", "lon"}]
    
    # Search area
    search_radius = Column(Float)  # km
    search_center_lat = Column(Float)
    search_center_lon = Column(Float)
    
    # Detection history (JSON array)
    detection_history_json = Column(Text)  # JSON: [{"junction_id", "timestamp", "direction"}]
    detection_count = Column(Integer, default=0)
    
    # Confidence and metrics
    overall_confidence = Column(Float)  # 0-100
    inference_time_ms = Column(Float)  # Time to compute
    
    generated_at = Column(Float, nullable=False)
    
    created_at = Column(DateTime, server_default=func.now())
    
    __table_args__ = (
        Index('idx_inference_incident', 'incident_id'),
    )
