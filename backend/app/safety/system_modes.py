"""
System Modes & State Machine

Implements FRD-05 FR-05.2: System mode management.
Manages transitions between NORMAL, EMERGENCY, INCIDENT, and FAIL_SAFE modes.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional, Callable
import time


class SystemMode(Enum):
    """System operational modes"""
    NORMAL = "NORMAL"           # Normal autonomous operation
    EMERGENCY = "EMERGENCY"     # Emergency vehicle corridor active
    INCIDENT = "INCIDENT"       # Traffic incident management
    FAIL_SAFE = "FAIL_SAFE"     # Safety failure - all signals to safe state


@dataclass
class SystemState:
    """Current system state"""
    mode: SystemMode
    entered_at: float
    reason: str
    previous_mode: Optional[SystemMode] = None


class SystemModeManager:
    """
    Manage system operational modes
    
    Mode descriptions:
    - NORMAL: Standard autonomous traffic control
    - EMERGENCY: Priority for emergency vehicle corridor
    - INCIDENT: Post-incident investigation mode
    - FAIL_SAFE: Safety critical failure - all signals default to safe state
    
    Transition rules:
    - NORMAL -> EMERGENCY: Emergency vehicle detected
    - EMERGENCY -> NORMAL: Emergency cleared
    - ANY -> FAIL_SAFE: Safety violation detected
    - FAIL_SAFE -> NORMAL: Manual reset only
    - NORMAL -> INCIDENT: Incident investigation triggered
    - INCIDENT -> NORMAL: Investigation complete
    """
    
    def __init__(self):
        """Initialize system mode manager"""
        self.current_state = SystemState(
            mode=SystemMode.NORMAL,
            entered_at=time.time(),
            reason="System initialized"
        )
        
        # Mode transition history
        self.transition_history = []
        
        # Mode-specific callbacks
        self.mode_enter_callbacks = {}  # mode -> callback
        self.mode_exit_callbacks = {}
        
        print("[SAFETY] System Mode Manager initialized")
        print(f"   Current mode: {self.current_state.mode.value}")
    
    def get_current_mode(self) -> SystemMode:
        """Get current system mode"""
        return self.current_state.mode
    
    def transition_to(self, 
                     new_mode: SystemMode, 
                     reason: str,
                     forced: bool = False) -> bool:
        """
        Transition to a new mode
        
        Args:
            new_mode: Target mode
            reason: Reason for transition
            forced: Force transition (skip validation)
        
        Returns:
            success: Whether transition was successful
        """
        current_mode = self.current_state.mode
        
        # Check if already in target mode
        if current_mode == new_mode:
            print(f"[MODE] Already in {new_mode.value} mode")
            return True
        
        # Validate transition (unless forced)
        if not forced and not self._is_valid_transition(current_mode, new_mode):
            print(f"[MODE] Invalid transition: {current_mode.value} -> {new_mode.value}")
            return False
        
        # Execute transition
        print(f"[MODE] Transition: {current_mode.value} -> {new_mode.value}")
        print(f"   Reason: {reason}")
        
        # Call exit callback for current mode
        if current_mode in self.mode_exit_callbacks:
            try:
                self.mode_exit_callbacks[current_mode]()
            except Exception as e:
                print(f"[MODE] Exit callback error: {e}")
        
        # Update state
        old_state = self.current_state
        self.current_state = SystemState(
            mode=new_mode,
            entered_at=time.time(),
            reason=reason,
            previous_mode=current_mode
        )
        
        # Record transition
        self.transition_history.append({
            'from': current_mode.value,
            'to': new_mode.value,
            'timestamp': time.time(),
            'reason': reason
        })
        
        # Call enter callback for new mode
        if new_mode in self.mode_enter_callbacks:
            try:
                self.mode_enter_callbacks[new_mode]()
            except Exception as e:
                print(f"[MODE] Enter callback error: {e}")
        
        return True
    
    def enter_fail_safe(self, reason: str):
        """
        Enter FAIL_SAFE mode (critical safety failure)
        
        This can be called from ANY mode and ALWAYS succeeds
        """
        print(f"[FAIL-SAFE] ENTERING FAIL-SAFE MODE: {reason}")
        self.transition_to(SystemMode.FAIL_SAFE, reason, forced=True)
    
    def exit_fail_safe(self, operator_id: str) -> bool:
        """
        Exit FAIL_SAFE mode (manual operator action required)
        
        Args:
            operator_id: ID of operator authorizing exit
        
        Returns:
            success: Whether exit was successful
        """
        if self.current_state.mode != SystemMode.FAIL_SAFE:
            print("[FAIL-SAFE] Not in FAIL_SAFE mode")
            return False
        
        print(f"[FAIL-SAFE] Exiting FAIL_SAFE mode (authorized by: {operator_id})")
        return self.transition_to(
            SystemMode.NORMAL,
            f"Manual reset by operator: {operator_id}",
            forced=True
        )
    
    def _is_valid_transition(self, 
                            from_mode: SystemMode, 
                            to_mode: SystemMode) -> bool:
        """
        Check if mode transition is valid
        
        Transition rules:
        - NORMAL <-> EMERGENCY (bidirectional)
        - NORMAL <-> INCIDENT (bidirectional)
        - ANY -> FAIL_SAFE (always allowed)
        - FAIL_SAFE -> NORMAL (manual only, via exit_fail_safe())
        """
        # FAIL_SAFE can be entered from any mode
        if to_mode == SystemMode.FAIL_SAFE:
            return True
        
        # Exiting FAIL_SAFE requires manual intervention
        if from_mode == SystemMode.FAIL_SAFE:
            return False  # Must use exit_fail_safe()
        
        # Define valid transitions
        valid_transitions = {
            SystemMode.NORMAL: [SystemMode.EMERGENCY, SystemMode.INCIDENT],
            SystemMode.EMERGENCY: [SystemMode.NORMAL],
            SystemMode.INCIDENT: [SystemMode.NORMAL]
        }
        
        allowed = valid_transitions.get(from_mode, [])
        return to_mode in allowed
    
    def register_mode_callback(self, 
                              mode: SystemMode, 
                              callback: Callable,
                              on_enter: bool = True):
        """
        Register callback for mode transitions
        
        Args:
            mode: Mode to register callback for
            callback: Function to call
            on_enter: If True, call on mode enter; else on mode exit
        """
        if on_enter:
            self.mode_enter_callbacks[mode] = callback
        else:
            self.mode_exit_callbacks[mode] = callback
    
    def get_mode_duration(self) -> float:
        """Get time spent in current mode (seconds)"""
        return time.time() - self.current_state.entered_at
    
    def get_state_info(self) -> dict:
        """Get current state information"""
        return {
            'mode': self.current_state.mode.value,
            'enteredAt': self.current_state.entered_at,
            'duration': self.get_mode_duration(),
            'reason': self.current_state.reason,
            'previousMode': (
                self.current_state.previous_mode.value 
                if self.current_state.previous_mode else None
            )
        }
    
    def get_transition_history(self, limit: int = 10) -> list:
        """Get recent mode transitions"""
        return self.transition_history[-limit:]

