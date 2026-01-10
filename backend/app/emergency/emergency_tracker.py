"""
Emergency Vehicle Tracker

Implements FRD-07 FR-07.1: Emergency vehicle detection and tracking.
Manages emergency sessions, vehicle position updates, and lifecycle.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum
import time
import uuid


class EmergencyType(Enum):
    """Types of emergency vehicles"""
    AMBULANCE = "AMBULANCE"
    FIRE_TRUCK = "FIRE_TRUCK"
    POLICE = "POLICE"


class EmergencyStatus(Enum):
    """Emergency session status"""
    INACTIVE = "INACTIVE"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


@dataclass
class EmergencyVehicle:
    """
    Emergency vehicle data
    
    Tracks position, route, and status of emergency vehicle.
    """
    vehicle_id: str
    type: EmergencyType
    current_position: tuple  # (x, y) canvas coordinates
    current_junction_id: Optional[str]
    destination: tuple  # (x, y) canvas coordinates
    destination_junction_id: str
    speed: float
    heading: float  # degrees
    number_plate: str = ""
    lat: Optional[float] = None
    lon: Optional[float] = None
    destination_lat: Optional[float] = None
    destination_lon: Optional[float] = None


@dataclass
class EmergencySession:
    """
    Active emergency corridor session
    
    Manages the complete lifecycle of an emergency from activation
    to completion or cancellation.
    """
    session_id: str
    vehicle: EmergencyVehicle
    status: EmergencyStatus
    activated_at: float
    completed_at: Optional[float] = None
    calculated_route: List[str] = field(default_factory=list)  # List of junction IDs
    affected_junctions: List[str] = field(default_factory=list)  # Junctions in corridor
    total_distance: float = 0.0
    estimated_time: float = 0.0
    actual_travel_time: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary for API response"""
        return {
            'sessionId': self.session_id,
            'vehicleId': self.vehicle.vehicle_id,
            'vehicleType': self.vehicle.type.value,
            'numberPlate': self.vehicle.number_plate,
            'status': self.status.value,
            'activatedAt': self.activated_at,
            'completedAt': self.completed_at,
            'currentPosition': {
                'x': self.vehicle.current_position[0],
                'y': self.vehicle.current_position[1]
            },
            'destination': {
                'x': self.vehicle.destination[0],
                'y': self.vehicle.destination[1]
            },
            'destinationJunction': self.vehicle.destination_junction_id,
            'calculatedRoute': self.calculated_route,
            'affectedJunctions': self.affected_junctions,
            'totalDistance': self.total_distance,
            'estimatedTime': self.estimated_time,
            'speed': self.vehicle.speed
        }


class EmergencyTracker:
    """
    Track emergency vehicles and manage emergency sessions
    
    Responsibilities:
    - Detect and register emergency vehicles
    - Track vehicle positions in real-time
    - Manage emergency session lifecycle
    - Provide vehicle data to corridor system
    
    Usage:
        tracker = EmergencyTracker()
        session_id = tracker.activate_emergency(
            vehicle_id="EMV-001",
            spawn_junction="J-0",
            destination_junction="J-8",
            emergency_type=EmergencyType.AMBULANCE
        )
    """
    
    def __init__(self, map_loader=None, ws_emitter=None):
        """
        Initialize emergency tracker
        
        Args:
            map_loader: MapLoaderService instance for junction data
            ws_emitter: WebSocket emitter for real-time updates
        """
        self.map_loader = map_loader
        self.ws_emitter = ws_emitter
        
        # Active emergency sessions
        self.active_sessions: List[EmergencySession] = []
        
        # Session history
        self.session_history: List[EmergencySession] = []
        
        # Session counter for IDs
        self.session_counter = 0
        
        # Statistics
        self.total_emergencies = 0
        self.completed_emergencies = 0
        self.cancelled_emergencies = 0
        self.total_time_saved = 0.0
        
        print("✅ Emergency Tracker initialized")
    
    def set_map_loader(self, map_loader):
        """Set map loader service after initialization"""
        self.map_loader = map_loader
    
    def set_ws_emitter(self, ws_emitter):
        """Set WebSocket emitter for real-time updates"""
        self.ws_emitter = ws_emitter
    
    def activate_emergency(
        self,
        spawn_junction: str,
        destination_junction: str,
        emergency_type: EmergencyType = EmergencyType.AMBULANCE,
        vehicle_id: Optional[str] = None,
        number_plate: Optional[str] = None
    ) -> str:
        """
        Activate emergency corridor for a vehicle
        
        Args:
            spawn_junction: Junction ID where emergency vehicle spawns
            destination_junction: Target junction ID (hospital, etc.)
            emergency_type: Type of emergency vehicle
            vehicle_id: Optional vehicle ID (auto-generated if not provided)
            number_plate: Optional vehicle number plate
        
        Returns:
            session_id: ID of created emergency session
        
        Raises:
            ValueError: If junctions are invalid or emergency already active
        """
        # Check if emergency already active (limit to one for hackathon)
        if self.is_emergency_active():
            raise ValueError("Emergency already active. Complete or cancel current emergency first.")
        
        # Get junction positions
        spawn_pos, spawn_lat, spawn_lon = self._get_junction_position(spawn_junction)
        dest_pos, dest_lat, dest_lon = self._get_junction_position(destination_junction)
        
        if not spawn_pos:
            raise ValueError(f"Spawn junction not found: {spawn_junction}")
        if not dest_pos:
            raise ValueError(f"Destination junction not found: {destination_junction}")
        
        # Generate IDs
        if not vehicle_id:
            vehicle_id = f"EMV-{uuid.uuid4().hex[:8].upper()}"
        
        if not number_plate:
            type_prefix = {
                EmergencyType.AMBULANCE: "AMB",
                EmergencyType.FIRE_TRUCK: "FIRE",
                EmergencyType.POLICE: "POL"
            }
            number_plate = f"GJ18{type_prefix[emergency_type]}{self.session_counter:03d}"
        
        # Create emergency vehicle data
        emergency_vehicle = EmergencyVehicle(
            vehicle_id=vehicle_id,
            type=emergency_type,
            current_position=spawn_pos,
            current_junction_id=spawn_junction,
            destination=dest_pos,
            destination_junction_id=destination_junction,
            speed=0.0,
            heading=0.0,
            number_plate=number_plate,
            lat=spawn_lat,
            lon=spawn_lon,
            destination_lat=dest_lat,
            destination_lon=dest_lon
        )
        
        # Create session
        self.session_counter += 1
        session_id = f"EMG-{self.session_counter:05d}"
        
        session = EmergencySession(
            session_id=session_id,
            vehicle=emergency_vehicle,
            status=EmergencyStatus.ACTIVE,
            activated_at=time.time(),
            calculated_route=[spawn_junction, destination_junction],  # Will be updated by pathfinder
            affected_junctions=[]  # Will be updated by corridor manager
        )
        
        self.active_sessions.append(session)
        self.total_emergencies += 1
        
        print(f"🚨 Emergency activated: {session_id}")
        print(f"   Vehicle: {vehicle_id} ({emergency_type.value})")
        print(f"   Number Plate: {number_plate}")
        print(f"   Route: {spawn_junction} → {destination_junction}")
        
        return session_id
    
    def update_session_route(self, session_id: str, route: List[str], distance: float = 0.0, estimated_time: float = 0.0):
        """
        Update session with calculated route
        
        Called by pathfinder after calculating optimal route.
        
        Args:
            session_id: Emergency session ID
            route: List of junction IDs in route
            distance: Total route distance in meters
            estimated_time: Estimated travel time in seconds
        """
        session = self._get_session(session_id)
        if not session:
            return
        
        session.calculated_route = route
        session.total_distance = distance
        session.estimated_time = estimated_time
        
        print(f"📍 Route calculated for {session_id}: {len(route)} junctions, {distance:.0f}m, ~{estimated_time:.0f}s")
    
    def update_corridor_junctions(self, session_id: str, junctions: List[str]):
        """
        Update session with affected corridor junctions
        
        Args:
            session_id: Emergency session ID
            junctions: List of junction IDs in active corridor
        """
        session = self._get_session(session_id)
        if not session:
            return
        
        session.affected_junctions = junctions
    
    def update_vehicle_position(
        self,
        session_id: str,
        position: tuple,
        speed: float = 0.0,
        heading: float = 0.0,
        current_junction: Optional[str] = None
    ):
        """
        Update emergency vehicle position
        
        Called periodically to track vehicle progress.
        
        Args:
            session_id: Emergency session ID
            position: New position (x, y)
            speed: Current speed
            heading: Current heading in degrees
            current_junction: Current or nearest junction ID
        """
        session = self._get_session(session_id)
        
        if not session or session.status != EmergencyStatus.ACTIVE:
            return
        
        # Update vehicle data
        session.vehicle.current_position = position
        session.vehicle.speed = speed
        session.vehicle.heading = heading
        
        if current_junction:
            session.vehicle.current_junction_id = current_junction
        
        # Check if reached destination
        if self._has_reached_destination(session):
            self.complete_emergency(session_id)
    
    def complete_emergency(self, session_id: str):
        """
        Complete emergency session
        
        Called when vehicle reaches destination.
        
        Args:
            session_id: Emergency session ID
        """
        session = self._get_session(session_id)
        
        if not session:
            return
        
        session.status = EmergencyStatus.COMPLETED
        session.completed_at = time.time()
        session.actual_travel_time = session.completed_at - session.activated_at
        
        # Calculate time saved (compared to estimated normal time)
        if session.estimated_time > 0:
            normal_time = session.estimated_time * 1.5  # Assume 50% slower without corridor
            time_saved = normal_time - session.actual_travel_time
            self.total_time_saved += max(0, time_saved)
        
        print(f"✅ Emergency completed: {session_id}")
        print(f"   Duration: {session.actual_travel_time:.1f}s")
        
        self.completed_emergencies += 1
        
        # Move to history
        self.session_history.append(session)
        self.active_sessions = [s for s in self.active_sessions if s.session_id != session_id]
    
    def cancel_emergency(self, session_id: str, reason: str = "Manual cancellation"):
        """
        Cancel emergency session
        
        Args:
            session_id: Emergency session ID
            reason: Reason for cancellation
        """
        session = self._get_session(session_id)
        
        if not session:
            return
        
        session.status = EmergencyStatus.CANCELLED
        session.completed_at = time.time()
        
        print(f"❌ Emergency cancelled: {session_id} - {reason}")
        
        self.cancelled_emergencies += 1
        
        # Move to history
        self.session_history.append(session)
        self.active_sessions = [s for s in self.active_sessions if s.session_id != session_id]
    
    def get_active_emergency(self) -> Optional[EmergencySession]:
        """
        Get currently active emergency session
        
        Returns:
            EmergencySession or None
        """
        if not self.active_sessions:
            return None
        
        # Return first active session (assume one at a time for hackathon)
        return self.active_sessions[0]
    
    def get_session(self, session_id: str) -> Optional[EmergencySession]:
        """Get session by ID (public interface)"""
        return self._get_session(session_id)
    
    def is_emergency_active(self) -> bool:
        """Check if any emergency is currently active"""
        return len(self.active_sessions) > 0
    
    def get_progress(self, session_id: str) -> Dict[str, Any]:
        """
        Get emergency progress information
        
        Returns:
            Progress data with percentage, ETA, etc.
        """
        session = self._get_session(session_id)
        
        if not session:
            return {'progress': 0, 'found': False}
        
        # Calculate progress based on position along route
        route = session.calculated_route
        current_junction = session.vehicle.current_junction_id
        
        if not route or len(route) < 2:
            return {
                'progress': 0,
                'currentJunction': current_junction,
                'totalJunctions': 0,
                'eta': session.estimated_time
            }
        
        # Find current position in route
        try:
            current_idx = route.index(current_junction) if current_junction in route else 0
        except ValueError:
            current_idx = 0
        
        progress = (current_idx / (len(route) - 1)) * 100 if len(route) > 1 else 0
        
        # Estimate remaining time
        elapsed = time.time() - session.activated_at
        if progress > 0:
            total_estimated = elapsed / (progress / 100)
            eta = max(0, total_estimated - elapsed)
        else:
            eta = session.estimated_time
        
        return {
            'progress': round(progress, 1),
            'currentJunction': current_junction,
            'currentJunctionIndex': current_idx,
            'totalJunctions': len(route),
            'remainingJunctions': len(route) - current_idx - 1,
            'elapsed': elapsed,
            'eta': eta,
            'estimatedArrival': time.time() + eta
        }
    
    def _get_session(self, session_id: str) -> Optional[EmergencySession]:
        """Get session by ID (internal)"""
        # Check active sessions
        for session in self.active_sessions:
            if session.session_id == session_id:
                return session
        
        # Check history
        for session in self.session_history:
            if session.session_id == session_id:
                return session
        
        return None
    
    def _get_junction_position(self, junction_id: str) -> tuple:
        """
        Get junction position from map loader
        
        Returns:
            (position tuple, lat, lon) or (None, None, None)
        """
        if not self.map_loader:
            # Fallback for testing - use mock positions
            mock_positions = {
                'J-0': ((100, 100), 23.17, 72.68),
                'J-1': ((400, 100), 23.17, 72.69),
                'J-2': ((700, 100), 23.17, 72.70),
                'J-3': ((100, 400), 23.18, 72.68),
                'J-4': ((400, 400), 23.18, 72.69),
                'J-5': ((700, 400), 23.18, 72.70),
                'J-6': ((100, 700), 23.19, 72.68),
                'J-7': ((400, 700), 23.19, 72.69),
                'J-8': ((700, 700), 23.19, 72.70),
            }
            return mock_positions.get(junction_id, (None, None, None))
        
        # Use map loader to find junction
        junctions = self.map_loader.junctions
        for junction in junctions:
            if junction.id == junction_id:
                return ((junction.x, junction.y), junction.lat, junction.lon)
        
        return (None, None, None)
    
    def _has_reached_destination(self, session: EmergencySession) -> bool:
        """Check if vehicle has reached destination"""
        vehicle_pos = session.vehicle.current_position
        dest_pos = session.vehicle.destination
        
        # Simple distance check (within 30 units)
        distance = (
            (vehicle_pos[0] - dest_pos[0]) ** 2 +
            (vehicle_pos[1] - dest_pos[1]) ** 2
        ) ** 0.5
        
        return distance < 30
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get emergency system statistics"""
        return {
            'totalEmergencies': self.total_emergencies,
            'completedEmergencies': self.completed_emergencies,
            'cancelledEmergencies': self.cancelled_emergencies,
            'activeEmergencies': len(self.active_sessions),
            'currentSession': (
                self.active_sessions[0].session_id 
                if self.active_sessions else None
            ),
            'totalTimeSaved': round(self.total_time_saved, 1),
            'successRate': (
                round((self.completed_emergencies / self.total_emergencies) * 100, 1)
                if self.total_emergencies > 0 else 0
            )
        }
    
    def get_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get emergency event history"""
        history = sorted(
            self.session_history,
            key=lambda s: s.completed_at or 0,
            reverse=True
        )[:limit]
        
        return [s.to_dict() for s in history]


# Global tracker instance
_emergency_tracker: Optional[EmergencyTracker] = None


def get_emergency_tracker() -> Optional[EmergencyTracker]:
    """Get global emergency tracker instance"""
    return _emergency_tracker


def init_emergency_tracker(map_loader=None, ws_emitter=None) -> EmergencyTracker:
    """Initialize global emergency tracker"""
    global _emergency_tracker
    _emergency_tracker = EmergencyTracker(map_loader=map_loader, ws_emitter=ws_emitter)
    return _emergency_tracker


