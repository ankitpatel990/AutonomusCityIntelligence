"""
Green Corridor Manager - Emergency Signal Control

Implements FRD-07 FR-07.3: Corridor activation for emergency vehicles.
Creates a "green wave" by setting signals to GREEN ahead of emergency vehicle.
"""

import asyncio
import time
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field

from app.safety import SystemMode, SystemModeManager


@dataclass
class ActiveCorridor:
    """
    Active green corridor state
    
    Tracks the current corridor configuration.
    """
    session_id: str
    junction_path: List[str]  # Complete path
    road_path: List[str]  # Road segments in path
    current_junction_index: int = 0
    activated_at: float = field(default_factory=time.time)
    lookahead_junctions: int = 5  # How many junctions ahead to clear
    signal_overrides: Dict[str, str] = field(default_factory=dict)  # junction -> green_direction
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response"""
        return {
            'sessionId': self.session_id,
            'junctionPath': self.junction_path,
            'roadPath': self.road_path,
            'currentJunctionIndex': self.current_junction_index,
            'junctionCount': len(self.junction_path),
            'activatedAt': self.activated_at,
            'signalOverrides': self.signal_overrides,
            'lookahead': self.lookahead_junctions
        }


class GreenCorridorManager:
    """
    Manage emergency green corridor
    
    Responsibilities:
    - Calculate corridor path
    - Activate signals along path (GREEN in travel direction)
    - Track vehicle progress
    - Deactivate corridor when complete
    - Integrate with system mode manager
    
    Usage:
        manager = GreenCorridorManager(mode_manager, tracker, pathfinder)
        await manager.activate_corridor(session_id)
        # Vehicle moves...
        await manager.update_corridor_progress(session, current_junction)
        await manager.deactivate_corridor()
    """
    
    def __init__(
        self,
        mode_manager: Optional[SystemModeManager] = None,
        emergency_tracker=None,
        pathfinder=None,
        map_loader=None,
        ws_emitter=None
    ):
        """
        Initialize corridor manager
        
        Args:
            mode_manager: SystemModeManager for EMERGENCY mode control
            emergency_tracker: EmergencyTracker for session management
            pathfinder: EmergencyPathfinder for route calculation
            map_loader: MapLoaderService for junction data
            ws_emitter: WebSocket emitter for real-time updates
        """
        self.mode_manager = mode_manager
        self.emergency_tracker = emergency_tracker
        self.pathfinder = pathfinder
        self.map_loader = map_loader
        self.ws_emitter = ws_emitter
        
        # Active corridor state
        self.active_corridor: Optional[ActiveCorridor] = None
        
        # Monitoring task
        self._monitoring_task: Optional[asyncio.Task] = None
        
        # Configuration
        self.lookahead_junctions = 5
        self.signal_hold_duration = 120  # seconds
        self.update_interval = 1.0  # seconds
        
        # Statistics
        self.corridors_activated = 0
        self.corridors_completed = 0
        
        print("✅ Green Corridor Manager initialized")
    
    def set_dependencies(
        self,
        mode_manager=None,
        emergency_tracker=None,
        pathfinder=None,
        map_loader=None,
        ws_emitter=None
    ):
        """Set dependencies after initialization"""
        if mode_manager:
            self.mode_manager = mode_manager
        if emergency_tracker:
            self.emergency_tracker = emergency_tracker
        if pathfinder:
            self.pathfinder = pathfinder
        if map_loader:
            self.map_loader = map_loader
        if ws_emitter:
            self.ws_emitter = ws_emitter
    
    async def activate_corridor(self, session_id: str) -> bool:
        """
        Activate green corridor for emergency session
        
        Args:
            session_id: Emergency session ID
        
        Returns:
            True if corridor activated successfully
        """
        if not self.emergency_tracker:
            print("❌ Emergency tracker not available")
            return False
        
        # Get emergency session
        session = self.emergency_tracker.get_session(session_id)
        
        if not session:
            print(f"❌ Emergency session not found: {session_id}")
            return False
        
        print(f"🟢 Activating green corridor: {session_id}")
        
        # Get spawn and destination junctions
        start_junction = session.vehicle.current_junction_id
        end_junction = session.vehicle.destination_junction_id
        
        if not start_junction or not end_junction:
            # Try to find nearest junctions from positions
            start_junction = self._find_nearest_junction(session.vehicle.current_position)
            end_junction = self._find_nearest_junction(session.vehicle.destination)
        
        # Calculate path using pathfinder
        junction_path = None
        if self.pathfinder:
            junction_path = self.pathfinder.find_path(start_junction, end_junction)
        
        if not junction_path:
            print(f"❌ No path found for corridor: {start_junction} -> {end_junction}")
            # Use simple direct path as fallback
            junction_path = [start_junction, end_junction]
        
        # Get road segments
        road_path = []
        if self.pathfinder:
            road_path = self.pathfinder.get_road_segments_in_path(junction_path)
            distance = self.pathfinder.get_path_distance(junction_path)
            estimated_time = self.pathfinder.estimate_travel_time(junction_path, speed_kmh=60)
        else:
            distance = 0
            estimated_time = len(junction_path) * 10  # 10 seconds per junction fallback
        
        # Update session with route
        self.emergency_tracker.update_session_route(
            session_id,
            junction_path,
            distance,
            estimated_time
        )
        
        # Create corridor state
        self.active_corridor = ActiveCorridor(
            session_id=session_id,
            junction_path=junction_path,
            road_path=road_path,
            current_junction_index=0,
            activated_at=time.time(),
            lookahead_junctions=self.lookahead_junctions
        )
        
        # Change system mode to EMERGENCY
        if self.mode_manager:
            self.mode_manager.transition_to(
                SystemMode.EMERGENCY,
                f"Emergency corridor activated: {session_id}"
            )
        
        # Activate signals along corridor
        await self._activate_corridor_signals()
        
        # Update session with affected junctions
        self.emergency_tracker.update_corridor_junctions(
            session_id,
            list(self.active_corridor.signal_overrides.keys())
        )
        
        # Emit WebSocket event
        if self.ws_emitter:
            await self.ws_emitter.emit_emergency_activated({
                'vehicle_id': session.vehicle.vehicle_id,
                'session_id': session_id,
                'corridor_path': junction_path,
                'estimated_time': estimated_time,
                'destination': end_junction,
                'road_path': road_path
            })
        
        # Start monitoring task
        self._monitoring_task = asyncio.create_task(self._monitor_corridor())
        
        self.corridors_activated += 1
        print(f"   Corridor active with {len(junction_path)} junctions")
        
        return True
    
    async def _activate_corridor_signals(self):
        """
        Activate signals along corridor path
        
        Sets junctions in lookahead range to GREEN in travel direction.
        """
        if not self.active_corridor:
            return
        
        junction_path = self.active_corridor.junction_path
        current_idx = self.active_corridor.current_junction_index
        lookahead = self.active_corridor.lookahead_junctions
        
        # Get junctions to clear
        end_idx = min(current_idx + lookahead, len(junction_path))
        junctions_to_clear = junction_path[current_idx:end_idx]
        
        print(f"🚦 Activating {len(junctions_to_clear)} junctions in corridor")
        
        # For each junction, determine travel direction and set GREEN
        new_overrides = {}
        
        for i, junction_id in enumerate(junctions_to_clear):
            # Determine direction based on next junction in path
            absolute_idx = current_idx + i
            
            if absolute_idx < len(junction_path) - 1:
                next_junction_id = junction_path[absolute_idx + 1]
                direction = self._calculate_direction(junction_id, next_junction_id)
            else:
                # Last junction - keep current direction or default
                direction = self.active_corridor.signal_overrides.get(junction_id, 'north')
            
            # Set signal to GREEN in travel direction
            await self._set_junction_green(
                junction_id=junction_id,
                direction=direction,
                lead_time=10 + i * 5  # Staggered timing
            )
            
            new_overrides[junction_id] = direction
            print(f"   {junction_id}: {direction} → GREEN")
        
        self.active_corridor.signal_overrides = new_overrides
    
    async def _set_junction_green(
        self,
        junction_id: str,
        direction: str,
        lead_time: int = 10
    ):
        """
        Set signal GREEN for corridor at a junction
        
        Args:
            junction_id: Junction ID
            direction: Direction to make green ('north', 'east', 'south', 'west')
            lead_time: Seconds before ambulance arrives
        """
        # Update junction in map loader if available
        if self.map_loader:
            junction = self._get_junction(junction_id)
            if junction:
                # Update junction mode to EMERGENCY
                junction.mode = 'EMERGENCY'
                
                # Set signals
                if junction.signals:
                    from app.models.junction import SignalColor
                    
                    # Set travel direction to GREEN
                    duration = self.signal_hold_duration
                    now = time.time()
                    
                    # Update all signals
                    for dir_name in ['north', 'east', 'south', 'west']:
                        signal = getattr(junction.signals, dir_name)
                        if dir_name == direction:
                            signal.current = SignalColor.GREEN
                            signal.duration = duration
                        else:
                            signal.current = SignalColor.RED
                            signal.duration = duration
                        signal.last_change = now
        
        # Emit signal change via WebSocket
        if self.ws_emitter:
            await self.ws_emitter.emit_signal_change(
                junction_id=junction_id,
                direction=direction,
                new_state='GREEN',
                previous_state='RED',
                duration=self.signal_hold_duration
            )
    
    async def _monitor_corridor(self):
        """
        Monitor emergency vehicle progress through corridor
        
        Background task that updates signals as vehicle moves.
        """
        print("📡 Corridor monitoring started")
        
        while self.active_corridor:
            try:
                # Get session
                session_id = self.active_corridor.session_id
                session = self.emergency_tracker.get_session(session_id)
                
                if not session:
                    print("❌ Session lost, deactivating corridor")
                    await self.deactivate_corridor()
                    break
                
                # Check if emergency completed or cancelled
                from app.emergency.emergency_tracker import EmergencyStatus
                if session.status != EmergencyStatus.ACTIVE:
                    await self.deactivate_corridor()
                    break
                
                # Get progress
                progress = self.emergency_tracker.get_progress(session_id)
                current_junction = progress.get('currentJunction')
                
                # Update corridor progress if moved
                if current_junction:
                    await self._update_corridor_progress(session, current_junction)
                
                # Emit progress via WebSocket
                if self.ws_emitter:
                    await self.ws_emitter.emit_emergency_progress(
                        vehicle_id=session.vehicle.vehicle_id,
                        current_junction=current_junction or '',
                        progress=progress.get('progress', 0),
                        eta=progress.get('eta', 0)
                    )
                
                # Wait before next update
                await asyncio.sleep(self.update_interval)
                
            except asyncio.CancelledError:
                print("📡 Corridor monitoring cancelled")
                break
            except Exception as e:
                print(f"❌ Corridor monitoring error: {e}")
                await asyncio.sleep(self.update_interval)
        
        print("📡 Corridor monitoring stopped")
    
    async def _update_corridor_progress(self, session, current_junction: str):
        """
        Update corridor based on vehicle progress
        
        Advances signal clearing as vehicle moves.
        """
        if not self.active_corridor:
            return
        
        junction_path = self.active_corridor.junction_path
        
        # Find current position in path
        if current_junction in junction_path:
            new_idx = junction_path.index(current_junction)
            
            if new_idx > self.active_corridor.current_junction_index:
                # Vehicle has advanced - update corridor
                self.active_corridor.current_junction_index = new_idx
                
                # Activate signals for new lookahead range
                await self._activate_corridor_signals()
                
                print(f"📍 Corridor progress: {new_idx + 1}/{len(junction_path)}")
    
    async def deactivate_corridor(self):
        """
        Deactivate green corridor
        
        Returns signals to normal autonomous control.
        """
        if not self.active_corridor:
            return
        
        session_id = self.active_corridor.session_id
        print(f"🔴 Deactivating green corridor: {session_id}")
        
        # Stop monitoring task
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            self._monitoring_task = None
        
        # Reset junction modes
        if self.map_loader:
            for junction_id in self.active_corridor.signal_overrides.keys():
                junction = self._get_junction(junction_id)
                if junction:
                    junction.mode = 'NORMAL'
        
        # Emit WebSocket event
        if self.ws_emitter:
            session = self.emergency_tracker.get_session(session_id)
            vehicle_id = session.vehicle.vehicle_id if session else 'unknown'
            await self.ws_emitter.emit_emergency_deactivated(
                vehicle_id=vehicle_id,
                reason='corridor_deactivated'
            )
        
        # Return system mode to NORMAL
        if self.mode_manager:
            current_mode = self.mode_manager.get_current_mode()
            if current_mode == SystemMode.EMERGENCY:
                self.mode_manager.transition_to(
                    SystemMode.NORMAL,
                    f"Emergency corridor deactivated: {session_id}"
                )
        
        # Clear active corridor
        self.active_corridor = None
        self.corridors_completed += 1
        
        print("   Corridor deactivated, signals returning to autonomous control")
    
    def _calculate_direction(self, from_junction: str, to_junction: str) -> str:
        """
        Calculate travel direction between junctions
        
        Args:
            from_junction: Current junction ID
            to_junction: Next junction ID
        
        Returns:
            Direction string ('north', 'east', 'south', 'west')
        """
        from_pos = self._get_junction_position(from_junction)
        to_pos = self._get_junction_position(to_junction)
        
        if not from_pos or not to_pos:
            return 'north'  # Default
        
        dx = to_pos[0] - from_pos[0]
        dy = to_pos[1] - from_pos[1]
        
        # Determine primary direction
        # Note: Canvas Y increases downward, so +dy is south
        if abs(dx) > abs(dy):
            return 'east' if dx > 0 else 'west'
        else:
            return 'south' if dy > 0 else 'north'
    
    def _find_nearest_junction(self, position: tuple) -> Optional[str]:
        """Find nearest junction to position"""
        if not self.map_loader:
            # Return first junction from mock list
            return 'J-0'
        
        junctions = self.map_loader.junctions
        
        min_distance = float('inf')
        nearest_junction = None
        
        for junction in junctions:
            distance = (
                (junction.x - position[0]) ** 2 +
                (junction.y - position[1]) ** 2
            ) ** 0.5
            
            if distance < min_distance:
                min_distance = distance
                nearest_junction = junction.id
        
        return nearest_junction
    
    def _get_junction(self, junction_id: str):
        """Get junction object from map loader"""
        if not self.map_loader:
            return None
        
        for junction in self.map_loader.junctions:
            if junction.id == junction_id:
                return junction
        
        return None
    
    def _get_junction_position(self, junction_id: str) -> Optional[tuple]:
        """Get junction position"""
        # Try pathfinder first (has cached positions)
        if self.pathfinder and junction_id in self.pathfinder.junction_positions:
            return self.pathfinder.junction_positions[junction_id]
        
        # Try map loader
        junction = self._get_junction(junction_id)
        if junction:
            return (junction.x, junction.y)
        
        return None
    
    def is_corridor_active(self) -> bool:
        """Check if corridor is currently active"""
        return self.active_corridor is not None
    
    def get_corridor_status(self) -> Optional[Dict[str, Any]]:
        """Get current corridor status"""
        if not self.active_corridor:
            return None
        
        return self.active_corridor.to_dict()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get corridor manager statistics"""
        return {
            'corridorsActivated': self.corridors_activated,
            'corridorsCompleted': self.corridors_completed,
            'corridorActive': self.is_corridor_active(),
            'currentSession': self.active_corridor.session_id if self.active_corridor else None
        }


# Global corridor manager instance
_corridor_manager: Optional[GreenCorridorManager] = None


def get_corridor_manager() -> Optional[GreenCorridorManager]:
    """Get global corridor manager instance"""
    return _corridor_manager


def init_corridor_manager(
    mode_manager=None,
    emergency_tracker=None,
    pathfinder=None,
    map_loader=None,
    ws_emitter=None
) -> GreenCorridorManager:
    """Initialize global corridor manager"""
    global _corridor_manager
    _corridor_manager = GreenCorridorManager(
        mode_manager=mode_manager,
        emergency_tracker=emergency_tracker,
        pathfinder=pathfinder,
        map_loader=map_loader,
        ws_emitter=ws_emitter
    )
    return _corridor_manager


