"""
Manual Override System

Implements FRD-05 FR-05.4: Manual override capabilities.
Allows traffic operators to take manual control of signals, bypassing the autonomous agent when needed.
"""

import time
from typing import List, Optional
from dataclasses import dataclass
from enum import Enum


class OverrideType(Enum):
    JUNCTION_SIGNAL = "JUNCTION_SIGNAL"  # Override specific junction signal
    AGENT_DISABLE = "AGENT_DISABLE"      # Disable autonomous agent
    EMERGENCY_STOP = "EMERGENCY_STOP"     # Emergency stop all
    MODE_CHANGE = "MODE_CHANGE"          # Force mode change


@dataclass
class ManualOverride:
    """Manual override record"""
    override_id: str
    type: OverrideType
    operator_id: str
    timestamp: float
    target_id: str  # Junction ID or "SYSTEM"
    parameters: dict
    duration: Optional[float] = None  # None = indefinite
    active: bool = True
    reason: str = ""


class ManualOverrideManager:
    """
    Manage manual traffic control overrides
    
    Allows operators to:
    - Force specific signal states
    - Disable autonomous agent
    - Emergency stop all traffic
    - Override system mode
    
    All actions are logged for audit trail
    """
    
    def __init__(self, 
                 simulation_manager=None,
                 agent_loop=None,
                 mode_manager=None):
        """
        Initialize manual override manager
        
        Args:
            simulation_manager: SimulationManager instance
            agent_loop: AutonomousAgent instance
            mode_manager: SystemModeManager instance
        """
        self.simulation_manager = simulation_manager
        self.agent_loop = agent_loop
        self.mode_manager = mode_manager
        
        # Active overrides
        self.active_overrides: List[ManualOverride] = []
        
        # Override history (for audit)
        self.override_history: List[ManualOverride] = []
        
        # Counter for override IDs
        self.override_counter = 0
        
        print("[SAFETY] Manual Override Manager initialized")
    
    async def force_signal_state(self,
                                 junction_id: str,
                                 direction: str,
                                 duration: int,
                                 operator_id: str,
                                 reason: str = "") -> str:
        """
        Force a specific signal to GREEN
        
        Args:
            junction_id: Junction ID
            direction: Direction (N, E, S, W or north, east, south, west)
            duration: Duration in seconds
            operator_id: Operator ID
            reason: Reason for override
        
        Returns:
            override_id: ID of created override
        """
        override_id = self._generate_override_id()
        
        # Create override record
        override = ManualOverride(
            override_id=override_id,
            type=OverrideType.JUNCTION_SIGNAL,
            operator_id=operator_id,
            timestamp=time.time(),
            target_id=junction_id,
            parameters={
                'direction': direction,
                'duration': duration
            },
            duration=duration,
            reason=reason
        )
        
        # Apply override
        if self.simulation_manager:
            try:
                if hasattr(self.simulation_manager, 'set_signal_green'):
                    await self.simulation_manager.set_signal_green(
                        junction_id=junction_id,
                        direction=direction,
                        duration=duration
                    )
            except Exception as e:
                print(f"[OVERRIDE] Error applying signal override: {e}")
        
        # Record override
        self.active_overrides.append(override)
        self.override_history.append(override)
        
        print(f"[OVERRIDE] Manual override: {junction_id} {direction} GREEN for {duration}s")
        print(f"   Operator: {operator_id}")
        print(f"   Reason: {reason}")
        
        # Log to database
        await self._log_override(override)
        
        return override_id
    
    async def disable_autonomous_agent(self,
                                      operator_id: str,
                                      reason: str = "") -> str:
        """
        Disable autonomous agent (pause autonomous control)
        
        Args:
            operator_id: Operator ID
            reason: Reason for disabling
        
        Returns:
            override_id: ID of override
        """
        override_id = self._generate_override_id()
        
        override = ManualOverride(
            override_id=override_id,
            type=OverrideType.AGENT_DISABLE,
            operator_id=operator_id,
            timestamp=time.time(),
            target_id="SYSTEM",
            parameters={},
            duration=None,  # Indefinite
            reason=reason
        )
        
        # Stop agent
        if self.agent_loop:
            try:
                if hasattr(self.agent_loop, 'pause'):
                    await self.agent_loop.pause()
                elif hasattr(self.agent_loop, 'stop'):
                    await self.agent_loop.stop()
            except Exception as e:
                print(f"[OVERRIDE] Error pausing agent: {e}")
        
        self.active_overrides.append(override)
        self.override_history.append(override)
        
        print(f"[OVERRIDE] Autonomous agent DISABLED")
        print(f"   Operator: {operator_id}")
        print(f"   Reason: {reason}")
        
        await self._log_override(override)
        
        return override_id
    
    async def enable_autonomous_agent(self,
                                     operator_id: str) -> bool:
        """
        Re-enable autonomous agent
        
        Args:
            operator_id: Operator ID
        
        Returns:
            success: Whether agent was re-enabled
        """
        # Find active AGENT_DISABLE override
        for override in self.active_overrides:
            if override.type == OverrideType.AGENT_DISABLE and override.active:
                override.active = False
                
                # Resume agent
                if self.agent_loop:
                    try:
                        if hasattr(self.agent_loop, 'resume'):
                            await self.agent_loop.resume()
                        elif hasattr(self.agent_loop, 'start'):
                            # Restart if resume not available
                            await self.agent_loop.start()
                    except Exception as e:
                        print(f"[OVERRIDE] Error resuming agent: {e}")
                
                print(f"[OVERRIDE] Autonomous agent ENABLED")
                print(f"   Operator: {operator_id}")
                
                return True
        
        print("[OVERRIDE] No active agent disable override")
        return False
    
    async def emergency_stop(self,
                            operator_id: str,
                            reason: str = "Emergency stop") -> str:
        """
        Emergency stop - set all signals to RED
        
        Args:
            operator_id: Operator ID
            reason: Reason for emergency stop
        
        Returns:
            override_id: ID of override
        """
        override_id = self._generate_override_id()
        
        override = ManualOverride(
            override_id=override_id,
            type=OverrideType.EMERGENCY_STOP,
            operator_id=operator_id,
            timestamp=time.time(),
            target_id="SYSTEM",
            parameters={},
            duration=None,
            reason=reason
        )
        
        # Stop agent
        if self.agent_loop:
            try:
                if hasattr(self.agent_loop, 'stop'):
                    await self.agent_loop.stop()
            except Exception as e:
                print(f"[OVERRIDE] Error stopping agent: {e}")
        
        # Set all signals to RED
        if self.simulation_manager:
            try:
                junctions = []
                if hasattr(self.simulation_manager, 'get_junctions'):
                    junctions = self.simulation_manager.get_junctions() or []
                elif hasattr(self.simulation_manager, 'junctions'):
                    junctions = self.simulation_manager.junctions or []
                
                for junction in junctions:
                    for direction in ['north', 'east', 'south', 'west']:
                        if hasattr(self.simulation_manager, 'set_signal_red'):
                            await self.simulation_manager.set_signal_red(
                                junction.id,
                                direction
                            )
            except Exception as e:
                print(f"[OVERRIDE] Error setting signals to RED: {e}")
        
        self.active_overrides.append(override)
        self.override_history.append(override)
        
        print(f"[OVERRIDE] EMERGENCY STOP")
        print(f"   Operator: {operator_id}")
        print(f"   Reason: {reason}")
        
        await self._log_override(override)
        
        return override_id
    
    async def cancel_override(self,
                             override_id: str,
                             operator_id: str) -> bool:
        """
        Cancel an active override
        
        Args:
            override_id: Override ID to cancel
            operator_id: Operator ID
        
        Returns:
            success: Whether override was cancelled
        """
        for override in self.active_overrides:
            if override.override_id == override_id and override.active:
                override.active = False
                
                print(f"[OVERRIDE] Override cancelled: {override_id}")
                print(f"   Operator: {operator_id}")
                
                # Resume normal operation if agent was disabled
                if override.type == OverrideType.AGENT_DISABLE:
                    if self.agent_loop:
                        try:
                            if hasattr(self.agent_loop, 'resume'):
                                await self.agent_loop.resume()
                        except Exception as e:
                            print(f"[OVERRIDE] Error resuming agent: {e}")
                
                return True
        
        return False
    
    def get_active_overrides(self) -> List[dict]:
        """Get all active overrides"""
        return [
            {
                'overrideId': o.override_id,
                'type': o.type.value,
                'operatorId': o.operator_id,
                'timestamp': o.timestamp,
                'targetId': o.target_id,
                'parameters': o.parameters,
                'duration': o.duration,
                'reason': o.reason
            }
            for o in self.active_overrides
            if o.active
        ]
    
    def get_override_history(self, limit: int = 50) -> List[dict]:
        """Get override history for audit"""
        recent = self.override_history[-limit:]
        
        return [
            {
                'overrideId': o.override_id,
                'type': o.type.value,
                'operatorId': o.operator_id,
                'timestamp': o.timestamp,
                'targetId': o.target_id,
                'parameters': o.parameters,
                'active': o.active,
                'reason': o.reason
            }
            for o in recent
        ]
    
    def _generate_override_id(self) -> str:
        """Generate unique override ID"""
        self.override_counter += 1
        return f"OVR-{self.override_counter:06d}"
    
    async def _log_override(self, override: ManualOverride):
        """Log override to database (audit trail)"""
        # TODO: Implement database logging
        pass

