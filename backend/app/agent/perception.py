"""
Perception Module

Reads complete system state for the agent loop.
Implements FRD-03 FR-03.2: State perception requirements.

This module provides:
- Vehicle state reading
- Density data from FRD-02 DensityTracker
- Signal states from junctions
- Emergency status
- Manual controls
- Recent violations

Performance Requirements:
- Perception time: < 50ms
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Set
import time


@dataclass
class PerceivedState:
    """
    Complete system state at a point in time
    
    This is the observation used by the agent for decision making.
    Combines data from density tracker, simulation, and other modules.
    """
    
    # Timestamp
    timestamp: float = field(default_factory=time.time)
    
    # Vehicles
    total_vehicles: int = 0
    vehicles_by_type: Dict[str, int] = field(default_factory=dict)
    
    # Density data (from FRD-02)
    road_densities: Dict[str, float] = field(default_factory=dict)
    junction_densities: Dict[str, Dict[str, float]] = field(default_factory=dict)
    city_avg_density: float = 0.0
    congestion_points: int = 0
    
    # Signal states
    signal_states: Dict[str, Dict[str, str]] = field(default_factory=dict)
    
    # Emergency status (FRD-07)
    emergency_active: bool = False
    emergency_vehicle_id: Optional[str] = None
    emergency_corridor: List[str] = field(default_factory=list)
    
    # Manual controls (traffic police overrides)
    manual_controls: List[dict] = field(default_factory=list)
    
    # Violations (FRD-09)
    recent_violations: List[dict] = field(default_factory=list)
    
    # Additional metrics
    simulation_time: float = 0.0
    is_paused: bool = False
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API/logging"""
        return {
            'timestamp': self.timestamp,
            'totalVehicles': self.total_vehicles,
            'vehiclesByType': self.vehicles_by_type,
            'roadDensities': self.road_densities,
            'junctionDensities': self.junction_densities,
            'cityAvgDensity': self.city_avg_density,
            'congestionPoints': self.congestion_points,
            'signalStates': self.signal_states,
            'emergencyActive': self.emergency_active,
            'emergencyVehicleId': self.emergency_vehicle_id,
            'manualControlsCount': len(self.manual_controls),
            'recentViolationsCount': len(self.recent_violations)
        }


class PerceptionModule:
    """
    Perceive current system state
    
    Reads data from:
    - Density Tracker (FRD-02)
    - Simulation Manager
    - Signal states
    - Emergency status
    - Manual controls
    
    Performance target: < 50ms perception time
    
    Usage:
        perception = PerceptionModule(density_tracker, simulation_manager)
        state = await perception.perceive()
    """
    
    def __init__(self, density_tracker=None, simulation_manager=None):
        """
        Initialize the Perception Module
        
        Args:
            density_tracker: DensityTracker instance from FRD-02
            simulation_manager: SimulationManager instance
        """
        self.density_tracker = density_tracker
        self.simulation_manager = simulation_manager
        
        # Lazy references to other modules
        self._emergency_manager = None
        self._violation_tracker = None
        
        # Performance tracking
        self._last_perception_time = 0.0
        self._perception_count = 0
        self._total_perception_time = 0.0
        
        print("[PERCEPTION] Perception module initialized")
    
    def set_emergency_manager(self, emergency_manager):
        """Set emergency manager for emergency status"""
        self._emergency_manager = emergency_manager
    
    def set_violation_tracker(self, violation_tracker):
        """Set violation tracker for recent violations"""
        self._violation_tracker = violation_tracker
    
    async def perceive(self) -> PerceivedState:
        """
        Perceive complete system state
        
        Returns:
            PerceivedState object with all current data
        """
        start_time = time.time()
        
        # Initialize state with defaults
        state = PerceivedState(timestamp=time.time())
        
        # Get vehicle data
        state.total_vehicles, state.vehicles_by_type = self._get_vehicle_data()
        
        # Get density data from FRD-02 tracker
        self._get_density_data(state)
        
        # Get signal states
        state.signal_states = self._get_signal_states()
        
        # Get emergency status
        self._get_emergency_status(state)
        
        # Get manual controls
        state.manual_controls = self._get_manual_controls()
        
        # Get recent violations
        state.recent_violations = self._get_recent_violations()
        
        # Get simulation info
        self._get_simulation_info(state)
        
        # Performance check
        perception_time = (time.time() - start_time) * 1000
        self._last_perception_time = perception_time
        self._perception_count += 1
        self._total_perception_time += perception_time
        
        if perception_time > 50:
            print(f"[WARN] Slow perception: {perception_time:.1f}ms")
        
        return state
    
    def _get_vehicle_data(self) -> tuple:
        """Get vehicle counts and types"""
        total = 0
        by_type = {'car': 0, 'bike': 0, 'ambulance': 0, 'truck': 0}
        
        if self.simulation_manager:
            try:
                # Try to get vehicles from simulation manager
                if hasattr(self.simulation_manager, 'get_vehicles'):
                    vehicles = self.simulation_manager.get_vehicles()
                    total = len(vehicles) if vehicles else 0
                    
                    for v in (vehicles or []):
                        v_type = v.type if hasattr(v, 'type') else v.get('type', 'car')
                        by_type[v_type] = by_type.get(v_type, 0) + 1
                        
                elif hasattr(self.simulation_manager, 'vehicles'):
                    vehicles = self.simulation_manager.vehicles
                    total = len(vehicles) if vehicles else 0
                    
                    for v in (vehicles or []):
                        v_type = v.type if hasattr(v, 'type') else v.get('type', 'car')
                        by_type[v_type] = by_type.get(v_type, 0) + 1
            except Exception as e:
                print(f"[WARN] Error getting vehicles: {e}")
        
        return total, by_type
    
    def _get_density_data(self, state: PerceivedState):
        """Get density data from FRD-02 tracker"""
        if not self.density_tracker:
            return
        
        try:
            # Get city metrics
            if hasattr(self.density_tracker, 'get_city_metrics'):
                metrics = self.density_tracker.get_city_metrics()
                state.city_avg_density = metrics.avg_density_score if hasattr(metrics, 'avg_density_score') else 0.0
                state.congestion_points = metrics.congestion_points if hasattr(metrics, 'congestion_points') else 0
            
            # Get road densities
            if hasattr(self.density_tracker, 'road_densities'):
                for road_id, data in self.density_tracker.road_densities.items():
                    if hasattr(data, 'density_score'):
                        state.road_densities[road_id] = data.density_score
                    elif isinstance(data, dict):
                        state.road_densities[road_id] = data.get('density_score', 0.0)
            
            # Get junction densities
            if hasattr(self.density_tracker, 'junction_densities'):
                for jid, data in self.density_tracker.junction_densities.items():
                    if hasattr(data, 'density_north'):
                        state.junction_densities[jid] = {
                            'N': data.density_north,
                            'E': data.density_east,
                            'S': data.density_south,
                            'W': data.density_west
                        }
                    elif isinstance(data, dict):
                        state.junction_densities[jid] = {
                            'N': data.get('density_north', 0),
                            'E': data.get('density_east', 0),
                            'S': data.get('density_south', 0),
                            'W': data.get('density_west', 0)
                        }
        except Exception as e:
            print(f"[WARN] Error getting density data: {e}")
    
    def _get_signal_states(self) -> Dict[str, Dict[str, str]]:
        """Extract signal states from junctions"""
        states = {}
        
        if not self.simulation_manager:
            return states
        
        try:
            junctions = None
            if hasattr(self.simulation_manager, 'get_junctions'):
                junctions = self.simulation_manager.get_junctions()
            elif hasattr(self.simulation_manager, 'junctions'):
                junctions = self.simulation_manager.junctions
            
            if junctions:
                for junction in junctions:
                    jid = junction.id if hasattr(junction, 'id') else junction.get('id')
                    if not jid:
                        continue
                    
                    # Extract signal states
                    signals = {}
                    if hasattr(junction, 'signals'):
                        sig = junction.signals
                        if hasattr(sig, 'north'):
                            signals['N'] = sig.north.current.value if hasattr(sig.north, 'current') else 'RED'
                            signals['E'] = sig.east.current.value if hasattr(sig.east, 'current') else 'RED'
                            signals['S'] = sig.south.current.value if hasattr(sig.south, 'current') else 'RED'
                            signals['W'] = sig.west.current.value if hasattr(sig.west, 'current') else 'RED'
                        elif isinstance(sig, dict):
                            signals['N'] = sig.get('north', {}).get('current', 'RED')
                            signals['E'] = sig.get('east', {}).get('current', 'RED')
                            signals['S'] = sig.get('south', {}).get('current', 'RED')
                            signals['W'] = sig.get('west', {}).get('current', 'RED')
                    elif isinstance(junction, dict):
                        sig = junction.get('signals', {})
                        signals['N'] = sig.get('north', {}).get('current', 'RED')
                        signals['E'] = sig.get('east', {}).get('current', 'RED')
                        signals['S'] = sig.get('south', {}).get('current', 'RED')
                        signals['W'] = sig.get('west', {}).get('current', 'RED')
                    
                    states[jid] = signals
                    
        except Exception as e:
            print(f"[WARN] Error getting signal states: {e}")
        
        return states
    
    def _get_emergency_status(self, state: PerceivedState):
        """Get emergency mode status"""
        state.emergency_active = False
        state.emergency_vehicle_id = None
        state.emergency_corridor = []
        
        # Check emergency manager
        if self._emergency_manager:
            try:
                if hasattr(self._emergency_manager, 'is_active'):
                    state.emergency_active = self._emergency_manager.is_active()
                if hasattr(self._emergency_manager, 'get_active_vehicle'):
                    state.emergency_vehicle_id = self._emergency_manager.get_active_vehicle()
                if hasattr(self._emergency_manager, 'get_corridor'):
                    state.emergency_corridor = self._emergency_manager.get_corridor()
            except Exception as e:
                print(f"[WARN] Error getting emergency status: {e}")
        
        # Fallback: check simulation manager
        if self.simulation_manager and not state.emergency_active:
            try:
                if hasattr(self.simulation_manager, 'get_emergency_status'):
                    status = self.simulation_manager.get_emergency_status()
                    if status:
                        state.emergency_active = status.get('active', False)
                        state.emergency_vehicle_id = status.get('vehicleId')
            except Exception as e:
                print(f"[WARN] Error getting emergency from sim: {e}")
    
    def _get_manual_controls(self) -> List[dict]:
        """Get active manual traffic controls"""
        controls = []
        
        if self.simulation_manager:
            try:
                if hasattr(self.simulation_manager, 'get_manual_controls'):
                    controls = self.simulation_manager.get_manual_controls() or []
                elif hasattr(self.simulation_manager, 'manual_controls'):
                    controls = self.simulation_manager.manual_controls or []
            except Exception as e:
                print(f"[WARN] Error getting manual controls: {e}")
        
        return controls
    
    def _get_recent_violations(self) -> List[dict]:
        """Get recent traffic violations"""
        violations = []
        
        if self._violation_tracker:
            try:
                if hasattr(self._violation_tracker, 'get_recent'):
                    violations = self._violation_tracker.get_recent(limit=10)
            except Exception as e:
                print(f"[WARN] Error getting violations: {e}")
        
        # Fallback: check simulation manager
        if self.simulation_manager and not violations:
            try:
                if hasattr(self.simulation_manager, 'get_recent_violations'):
                    violations = self.simulation_manager.get_recent_violations() or []
            except Exception as e:
                pass
        
        return violations
    
    def _get_simulation_info(self, state: PerceivedState):
        """Get simulation metadata"""
        if self.simulation_manager:
            try:
                if hasattr(self.simulation_manager, 'simulation_time'):
                    state.simulation_time = self.simulation_manager.simulation_time
                if hasattr(self.simulation_manager, 'is_paused'):
                    state.is_paused = self.simulation_manager.is_paused
            except Exception as e:
                pass
    
    def get_stats(self) -> dict:
        """Get perception performance statistics"""
        avg_time = (
            self._total_perception_time / self._perception_count 
            if self._perception_count > 0 else 0
        )
        
        return {
            'lastPerceptionTime': round(self._last_perception_time, 2),
            'avgPerceptionTime': round(avg_time, 2),
            'perceptionCount': self._perception_count
        }

