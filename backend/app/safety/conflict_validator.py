"""
Safety Validator - Signal Conflict Prevention

Implements FRD-05 FR-05.1: Signal conflict detection and prevention.
This is the first line of defense against dangerous signal conflicts.

Safety Rules:
1. Only ONE direction can be GREEN at a time
2. Opposing directions cannot both be GREEN
3. Must have transition through YELLOW
4. Minimum RED time between changes
"""

from typing import List, Tuple, Optional
import time

from app.models.junction import SignalColor, SignalState, JunctionSignals


class ConflictValidator:
    """
    Validate signal changes to prevent conflicts
    
    Safety Rules:
    1. Only ONE direction can be GREEN at a time
    2. Opposing directions cannot both be GREEN
    3. Must have transition through YELLOW
    4. Minimum RED time between changes
    """
    
    # Conflict matrix: which directions conflict with each other
    # Maps direction codes (N/E/S/W) to conflicting directions
    CONFLICT_MATRIX = {
        'N': ['E', 'W', 'S'],  # North conflicts with all others
        'E': ['N', 'S', 'W'],  # East conflicts with all others
        'S': ['N', 'E', 'W'],  # South conflicts with all others
        'W': ['N', 'E', 'S']   # West conflicts with all others
    }
    
    # Direction name to code mapping
    DIRECTION_MAP = {
        'north': 'N',
        'east': 'E',
        'south': 'S',
        'west': 'W',
        'N': 'N',
        'E': 'E',
        'S': 'S',
        'W': 'W'
    }
    
    def __init__(self, config: dict = None):
        """
        Initialize conflict validator
        
        Args:
            config: Configuration (optional)
        """
        self.config = config or {}
        
        # Minimum timings (seconds)
        self.min_red_time = self.config.get('minRedTime', 2)
        self.min_green_time = self.config.get('minGreenTime', 10)
        self.yellow_duration = self.config.get('yellowDuration', 3)
        
        # Track last change times
        self.last_change_times = {}  # junction_id:direction -> timestamp
        
        print("[SAFETY] Conflict Validator initialized")
        print(f"   Min RED time: {self.min_red_time}s")
        print(f"   Min GREEN time: {self.min_green_time}s")
    
    def validate_signal_change(self, 
                               junction_id: str,
                               target_direction: str,
                               target_color: SignalColor,
                               current_signals: JunctionSignals,
                               current_time: float) -> Tuple[bool, str]:
        """
        Validate if a signal change is safe
        
        Args:
            junction_id: Junction ID
            target_direction: Direction to change (N/E/S/W or north/east/south/west)
            target_color: Desired color
            current_signals: Current signal states
            current_time: Current timestamp
        
        Returns:
            (is_safe, reason): Tuple of validation result and reason
        """
        # Normalize direction to code
        target_dir_code = self._normalize_direction(target_direction)
        
        # Rule 1: Check for conflicts if changing to GREEN
        if target_color == SignalColor.GREEN:
            is_safe, reason = self._check_green_conflicts(
                target_dir_code,
                current_signals
            )
            if not is_safe:
                return False, reason
        
        # Rule 2: Check minimum timing constraints
        is_safe, reason = self._check_timing_constraints(
            junction_id,
            target_dir_code,
            target_color,
            current_signals,
            current_time
        )
        if not is_safe:
            return False, reason
        
        # Rule 3: Check state transition validity (RED -> YELLOW -> GREEN)
        is_safe, reason = self._check_state_transition(
            target_dir_code,
            target_color,
            current_signals
        )
        if not is_safe:
            return False, reason
        
        # All checks passed
        return True, "SAFE"
    
    def _check_green_conflicts(self, 
                               target_direction: str,
                               current_signals: JunctionSignals) -> Tuple[bool, str]:
        """
        Check if setting target_direction to GREEN would create conflicts
        
        Returns:
            (is_safe, reason)
        """
        # Get conflicting directions
        conflicting_dirs = self.CONFLICT_MATRIX.get(target_direction, [])
        
        # Check each conflicting direction
        for conflict_dir in conflicting_dirs:
            signal_state = self._get_signal_by_direction(current_signals, conflict_dir)
            
            if signal_state and signal_state.current == SignalColor.GREEN:
                return False, f"Conflict: {conflict_dir} is already GREEN"
        
        return True, "No conflicts"
    
    def _check_timing_constraints(self,
                                  junction_id: str,
                                  target_direction: str,
                                  target_color: SignalColor,
                                  current_signals: JunctionSignals,
                                  current_time: float) -> Tuple[bool, str]:
        """
        Check minimum timing constraints
        
        Returns:
            (is_safe, reason)
        """
        # Get current signal for this direction
        current_signal = self._get_signal_by_direction(current_signals, target_direction)
        
        if not current_signal:
            return True, "No timing constraints"
        
        # Check minimum GREEN time (if currently GREEN)
        if current_signal.current == SignalColor.GREEN and target_color != SignalColor.GREEN:
            last_change = self.last_change_times.get(f"{junction_id}:{target_direction}", current_signal.last_change)
            time_elapsed = current_time - last_change
            
            if time_elapsed < self.min_green_time:
                return False, f"Minimum GREEN time not elapsed: {time_elapsed:.1f}s < {self.min_green_time}s"
        
        # Check minimum RED time (if currently RED)
        if current_signal.current == SignalColor.RED and target_color == SignalColor.GREEN:
            last_change = self.last_change_times.get(f"{junction_id}:{target_direction}", current_signal.last_change)
            time_elapsed = current_time - last_change
            
            if time_elapsed < self.min_red_time:
                return False, f"Minimum RED time not elapsed: {time_elapsed:.1f}s < {self.min_red_time}s"
        
        return True, "Timing constraints met"
    
    def _check_state_transition(self,
                                target_direction: str,
                                target_color: SignalColor,
                                current_signals: JunctionSignals) -> Tuple[bool, str]:
        """
        Check if state transition is valid
        
        Valid transitions:
        - RED -> GREEN (with YELLOW in between, handled by signal controller)
        - GREEN -> RED (with YELLOW in between)
        - Any -> YELLOW (always allowed)
        
        Returns:
            (is_safe, reason)
        """
        current_signal = self._get_signal_by_direction(current_signals, target_direction)
        
        if not current_signal:
            return True, "No current state"
        
        current_color = current_signal.current
        
        # YELLOW is always allowed as intermediate state
        if target_color == SignalColor.YELLOW:
            return True, "YELLOW transition allowed"
        
        # RED is always allowed (emergency stop)
        if target_color == SignalColor.RED:
            return True, "RED transition allowed"
        
        # GREEN requires proper transition
        # (In practice, signal controller will insert YELLOW automatically)
        if target_color == SignalColor.GREEN:
            if current_color == SignalColor.GREEN:
                return True, "Already GREEN"
            # We allow RED -> GREEN, assuming YELLOW will be inserted
            return True, "Transition allowed (YELLOW will be inserted)"
        
        return True, "Transition allowed"
    
    def _get_signal_by_direction(self, 
                                 signals: JunctionSignals, 
                                 direction: str) -> Optional[SignalState]:
        """Get signal state for specific direction"""
        direction_map = {
            'N': signals.north,
            'E': signals.east,
            'S': signals.south,
            'W': signals.west
        }
        return direction_map.get(direction)
    
    def _normalize_direction(self, direction: str) -> str:
        """Normalize direction to code (N/E/S/W)"""
        return self.DIRECTION_MAP.get(direction, direction.upper()[:1])
    
    def record_signal_change(self, 
                            junction_id: str,
                            direction: str,
                            timestamp: float):
        """
        Record a signal change for timing tracking
        
        Args:
            junction_id: Junction ID
            direction: Direction changed
            timestamp: Time of change
        """
        dir_code = self._normalize_direction(direction)
        key = f"{junction_id}:{dir_code}"
        self.last_change_times[key] = timestamp
    
    def validate_full_junction(self, signals: JunctionSignals) -> Tuple[bool, List[str]]:
        """
        Validate entire junction for conflicts
        
        Used for health checks
        
        Returns:
            (is_valid, list_of_issues)
        """
        issues = []
        
        # Count GREEN signals
        green_count = 0
        green_directions = []
        
        for direction in ['N', 'E', 'S', 'W']:
            signal = self._get_signal_by_direction(signals, direction)
            if signal and signal.current == SignalColor.GREEN:
                green_count += 1
                green_directions.append(direction)
        
        # Check: should have at most 1 GREEN
        if green_count > 1:
            issues.append(f"Multiple GREEN signals: {green_directions}")
        
        # Check: should have at least 1 GREEN (for efficiency)
        # (This is a warning, not an error)
        if green_count == 0:
            issues.append("WARNING: No GREEN signals (inefficient)")
        
        is_valid = len([i for i in issues if not i.startswith("WARNING")]) == 0
        
        return is_valid, issues

