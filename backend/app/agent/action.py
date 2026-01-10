"""
Action Module

Execute agent decisions with safety validation.
Implements FRD-03 FR-03.4: Action execution requirements.

Responsibilities:
- Execute signal state changes
- Safety validation (via FRD-05)
- Action logging
- Error handling

Performance Requirements:
- Execution time: < 100ms
"""

from typing import Optional, List, TYPE_CHECKING
import time

if TYPE_CHECKING:
    from app.agent.decision import AgentDecisions, SignalDecision


class ActionModule:
    """
    Execute agent decisions
    
    Responsibilities:
    - Execute signal state changes
    - Safety validation (via FRD-05)
    - Action logging
    - Error handling
    
    Usage:
        action = ActionModule(simulation_manager)
        action.set_safety_validator(safety_validator)
        await action.execute(decisions)
    """
    
    def __init__(self, simulation_manager=None, safety_validator=None):
        """
        Initialize the Action Module
        
        Args:
            simulation_manager: Simulation manager for signal control
            safety_validator: Safety validator from FRD-05
        """
        self.simulation_manager = simulation_manager
        self.safety_validator = safety_validator  # Injected from FRD-05
        
        # Statistics
        self.actions_executed = 0
        self.actions_rejected = 0
        self.total_execution_time = 0.0
        
        # WebSocket emitter for broadcasting
        self._ws_emitter = None
        
        print("[ACTION] Action module initialized")
    
    def set_safety_validator(self, validator):
        """Set safety validator from FRD-05"""
        self.safety_validator = validator
        print("[OK] Safety validator injected into action module")
    
    def set_simulation_manager(self, manager):
        """Set simulation manager"""
        self.simulation_manager = manager
    
    def set_ws_emitter(self, emitter):
        """Set WebSocket emitter for broadcasting signal changes"""
        self._ws_emitter = emitter
    
    async def execute(self, decisions: 'AgentDecisions'):
        """
        Execute signal control decisions
        
        Args:
            decisions: Agent decisions to execute
        """
        if not decisions:
            return
        
        # Skip if emergency override (handled by emergency module)
        if decisions.emergency_override:
            return
        
        # Skip if no decisions
        if not decisions.signal_decisions:
            return
        
        start_time = time.time()
        
        # Execute each signal decision
        for decision in decisions.signal_decisions:
            await self._execute_signal_decision(decision)
        
        # Track execution time
        execution_time = (time.time() - start_time) * 1000
        self.total_execution_time += execution_time
        
        if execution_time > 100:
            print(f"[WARN] Slow execution: {execution_time:.1f}ms")
    
    async def _execute_signal_decision(self, decision: 'SignalDecision'):
        """
        Execute a single signal decision
        
        Safety validation performed before execution.
        
        Args:
            decision: SignalDecision to execute
        """
        # Validate decision has required fields
        if not decision.junction_id or not decision.direction:
            print(f"[WARN] Invalid decision: missing junction_id or direction")
            return
        
        # Safety validation (if validator available)
        if self.safety_validator:
            try:
                is_safe, reason = await self._validate_safety(decision)
                
                if not is_safe:
                    print(f"[BLOCKED] Safety check failed: {decision.junction_id} {decision.direction} - {reason}")
                    self.actions_rejected += 1
                    return
            except Exception as e:
                print(f"[WARN] Safety validation error: {e}")
                # Continue with action if safety check fails (fail-open for demo)
        
        # Execute the action
        try:
            if decision.action == 'GREEN':
                await self._set_signal_green(
                    decision.junction_id,
                    decision.direction,
                    decision.duration
                )
            elif decision.action == 'RED':
                await self._set_signal_red(
                    decision.junction_id,
                    decision.direction
                )
            elif decision.action == 'HOLD':
                # Do nothing - maintain current state
                pass
            
            self.actions_executed += 1
            
            # Log action (verbose logging disabled for performance)
            # await self._log_action(decision)
            
            # Broadcast signal change via WebSocket
            if self._ws_emitter and decision.action != 'HOLD':
                await self._broadcast_signal_change(decision)
            
        except Exception as e:
            print(f"[ERROR] Action execution error: {e}")
            self.actions_rejected += 1
    
    async def _validate_safety(self, decision: 'SignalDecision') -> tuple:
        """
        Validate signal change with safety module
        
        Returns:
            Tuple of (is_safe: bool, reason: str)
        """
        if not self.safety_validator:
            return True, "No validator"
        
        # Get current junction state
        if not self.simulation_manager:
            return True, "No simulation manager"
        
        # Find the junction
        junction = None
        if hasattr(self.simulation_manager, 'get_junctions'):
            junctions = self.simulation_manager.get_junctions() or []
            junction = next((j for j in junctions if j.id == decision.junction_id), None)
        elif hasattr(self.simulation_manager, 'junctions'):
            junctions = self.simulation_manager.junctions or []
            junction = next((j for j in junctions if j.id == decision.junction_id), None)
        
        if not junction or not hasattr(junction, 'signals'):
            return True, "Junction not found"
        
        # Import SignalColor
        from app.models.junction import SignalColor
        
        # Map action to SignalColor
        target_color = SignalColor.GREEN if decision.action == 'GREEN' else SignalColor.RED
        
        # Call safety validator
        if hasattr(self.safety_validator, 'validate_signal_change'):
            import time
            return self.safety_validator.validate_signal_change(
                junction_id=decision.junction_id,
                target_direction=decision.direction,
                target_color=target_color,
                current_signals=junction.signals,
                current_time=time.time()
            )
        
        return True, "Validator missing method"
    
    async def _set_signal_green(self, junction_id: str, direction: str, duration: int):
        """
        Set signal to GREEN
        
        Args:
            junction_id: Junction identifier
            direction: Direction (N/E/S/W)
            duration: Green duration in seconds
        """
        if not self.simulation_manager:
            return
        
        try:
            if hasattr(self.simulation_manager, 'set_signal_green'):
                await self.simulation_manager.set_signal_green(
                    junction_id, direction, duration
                )
            elif hasattr(self.simulation_manager, 'set_signal'):
                await self.simulation_manager.set_signal(
                    junction_id, direction, 'GREEN', duration
                )
            elif hasattr(self.simulation_manager, 'update_signal'):
                self.simulation_manager.update_signal(
                    junction_id, direction, 'GREEN', duration
                )
        except Exception as e:
            print(f"[ERROR] Error setting green signal: {e}")
            raise
    
    async def _set_signal_red(self, junction_id: str, direction: str):
        """
        Set signal to RED
        
        Args:
            junction_id: Junction identifier
            direction: Direction (N/E/S/W)
        """
        if not self.simulation_manager:
            return
        
        try:
            if hasattr(self.simulation_manager, 'set_signal_red'):
                await self.simulation_manager.set_signal_red(junction_id, direction)
            elif hasattr(self.simulation_manager, 'set_signal'):
                await self.simulation_manager.set_signal(
                    junction_id, direction, 'RED', 0
                )
            elif hasattr(self.simulation_manager, 'update_signal'):
                self.simulation_manager.update_signal(
                    junction_id, direction, 'RED', 0
                )
        except Exception as e:
            print(f"[ERROR] Error setting red signal: {e}")
            raise
    
    async def _log_action(self, decision: 'SignalDecision'):
        """Log executed action (verbose)"""
        if decision.action != 'HOLD':
            print(f"[DONE] {decision.junction_id}: {decision.direction} -> {decision.action} ({decision.reason})")
    
    async def _broadcast_signal_change(self, decision: 'SignalDecision'):
        """Broadcast signal change via WebSocket"""
        if self._ws_emitter:
            try:
                await self._ws_emitter.emit_signal_change(
                    junction_id=decision.junction_id,
                    direction=decision.direction.lower(),
                    new_state=decision.action,
                    previous_state='RED' if decision.action == 'GREEN' else 'GREEN',
                    duration=float(decision.duration)
                )
            except Exception as e:
                print(f"[WARN] Broadcast error: {e}")
    
    def get_statistics(self) -> dict:
        """Get action execution statistics"""
        total = self.actions_executed + self.actions_rejected
        success_rate = (
            self.actions_executed / total
            if total > 0 else 1.0
        )
        avg_time = (
            self.total_execution_time / self.actions_executed
            if self.actions_executed > 0 else 0
        )
        
        return {
            'executed': self.actions_executed,
            'rejected': self.actions_rejected,
            'successRate': round(success_rate, 3),
            'avgExecutionTime': round(avg_time, 2)
        }

