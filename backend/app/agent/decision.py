"""
Decision Module

Make traffic control decisions using multiple strategies.
Implements FRD-03 FR-03.3: Decision making engine.
Integrates with FRD-04 RL-Powered Signal Orchestration.

Strategies:
1. RL (Primary) - Reinforcement Learning agent (FRD-04)
2. RULE_BASED (Fallback) - Simple density-based rules
3. MANUAL - Apply manual overrides
4. EMERGENCY - Emergency corridor priority

Decision hierarchy:
1. Emergency override (highest priority)
2. Manual controls
3. RL agent (primary)
4. Rule-based (fallback)

Performance Requirements:
- RL decisions: < 100ms
- Rule-based: < 50ms

RL Integration (FRD-04):
- Uses RLInferenceService for fast model inference
- Converts PerceivedState to 63-dim observation
- Maps 9-action output to signal decisions
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time
import numpy as np

from app.agent.agent_loop import AgentStrategy
from app.agent.perception import PerceivedState


@dataclass
class SignalDecision:
    """Decision for a single junction"""
    junction_id: str
    direction: str  # 'N', 'E', 'S', 'W'
    action: str  # 'GREEN', 'RED', 'HOLD'
    duration: int  # seconds
    reason: str  # Explanation for logging
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'junctionId': self.junction_id,
            'direction': self.direction,
            'action': self.action,
            'duration': self.duration,
            'reason': self.reason
        }


@dataclass
class AgentDecisions:
    """Collection of decisions for this cycle"""
    timestamp: float = field(default_factory=time.time)
    strategy_used: str = "RULE_BASED"
    signal_decisions: List[SignalDecision] = field(default_factory=list)
    emergency_override: bool = False
    latency: float = 0.0
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'timestamp': self.timestamp,
            'strategyUsed': self.strategy_used,
            'signalDecisions': [d.to_dict() for d in self.signal_decisions],
            'emergencyOverride': self.emergency_override,
            'latency': self.latency
        }


class DecisionModule:
    """
    Make traffic control decisions
    
    Strategy hierarchy:
    1. Emergency override (highest priority)
    2. Manual controls
    3. RL agent (primary)
    4. Rule-based (fallback)
    
    Usage:
        decision = DecisionModule()
        decision.inject_rl_agent(trained_model)
        decisions = await decision.decide(state, predictions, strategy)
    """
    
    def __init__(self, density_tracker=None):
        """
        Initialize the Decision Module
        
        Args:
            density_tracker: Optional DensityTracker for waiting time data
        """
        self.rl_agent = None  # Injected from FRD-04 (PPO model)
        self.rl_service = None  # Optional: RLInferenceService
        self.rule_engine = RuleBasedEngine()
        self.density_tracker = density_tracker  # For waiting time tracking
        
        # Configuration
        self.min_green_time = 10  # seconds
        self.max_green_time = 60  # seconds
        self.default_green_time = 30  # seconds
        
        # Performance tracking
        self._decision_count = 0
        self._total_latency = 0.0
        self._rl_decisions = 0
        self._rule_decisions = 0
        self._rl_fallback_count = 0  # Times fell back from RL to rules
        
        print("[DECISION] Decision module initialized")
    
    def inject_density_tracker(self, density_tracker):
        """Inject density tracker for waiting time data"""
        self.density_tracker = density_tracker
        print("[OK] Density tracker injected into decision module")
    
    def inject_rl_agent(self, rl_agent):
        """
        Inject trained RL agent
        
        Args:
            rl_agent: Trained PPO/DQN agent from stable-baselines3
        """
        self.rl_agent = rl_agent
        print("[OK] RL agent injected into decision module")
    
    def inject_rl_service(self, rl_service):
        """
        Inject RL inference service (alternative to raw agent)
        
        Args:
            rl_service: RLInferenceService instance
        """
        self.rl_service = rl_service
        if rl_service and rl_service.is_ready():
            self.rl_agent = rl_service.model
            print("[OK] RL inference service injected")
        else:
            print("[WARN] RL service not ready")
    
    async def decide(self, 
                     state: PerceivedState, 
                     predictions: Optional[dict],
                     strategy: AgentStrategy) -> AgentDecisions:
        """
        Make decisions based on state and predictions
        
        Decision hierarchy:
        1. Emergency mode → Emergency logic
        2. Manual overrides → Apply manual controls
        3. RL strategy → RL agent decisions
        4. Rule-based strategy → Rule-based decisions
        
        Args:
            state: Current perceived state
            predictions: Optional congestion predictions
            strategy: Decision strategy to use
            
        Returns:
            AgentDecisions object with all signal decisions
        """
        start_time = time.time()
        
        # Check for emergency mode (highest priority)
        if state.emergency_active:
            decisions = await self._emergency_mode_decisions(state)
            decisions.emergency_override = True
            decisions.latency = (time.time() - start_time) * 1000
            return decisions
        
        # Check for manual overrides
        if state.manual_controls:
            decisions = await self._apply_manual_controls(state)
            decisions.strategy_used = "MANUAL"
            decisions.latency = (time.time() - start_time) * 1000
            return decisions
        
        # Normal operation - use selected strategy
        if strategy == AgentStrategy.RL and self.rl_agent:
            decisions = await self._rl_based_decisions(state, predictions)
            self._rl_decisions += 1
        else:
            decisions = await self._rule_based_decisions(state, predictions)
            self._rule_decisions += 1
        
        # Calculate latency
        latency = (time.time() - start_time) * 1000  # ms
        decisions.latency = latency
        
        # Update stats
        self._decision_count += 1
        self._total_latency += latency
        
        # Performance warning
        max_latency = 100 if strategy == AgentStrategy.RL else 50
        if latency > max_latency:
            print(f"[WARN] Slow decision: {latency:.1f}ms (strategy: {strategy.value})")
        
        return decisions
    
    async def _rl_based_decisions(self, 
                                   state: PerceivedState,
                                   predictions: Optional[dict]) -> AgentDecisions:
        """
        Use RL agent for decisions (PRIMARY STRATEGY)
        
        This is where the trained PPO agent makes autonomous decisions.
        Converts state to observation format and maps actions to signals.
        """
        if not self.rl_agent:
            # Fallback to rules if no RL agent
            self._rl_fallback_count += 1
            return await self._rule_based_decisions(state, predictions)
        
        try:
            # Convert state to RL observation format (63-dim for 9 junctions × 7 features)
            observation = self._state_to_observation(state)
            
            # Get RL agent prediction
            actions, _ = self.rl_agent.predict(observation, deterministic=True)
            
            # Convert actions to signal decisions
            signal_decisions = self._actions_to_decisions(actions, state)
            
            return AgentDecisions(
                timestamp=time.time(),
                strategy_used="RL",
                signal_decisions=signal_decisions,
                emergency_override=False,
                latency=0.0  # Set by caller
            )
            
        except Exception as e:
            print(f"[WARN] RL decision error: {e}, falling back to rules")
            self._rl_fallback_count += 1
            return await self._rule_based_decisions(state, predictions)
    
    async def _rule_based_decisions(self, 
                                     state: PerceivedState,
                                     predictions: Optional[dict]) -> AgentDecisions:
        """
        Use rule-based logic (FALLBACK STRATEGY)
        
        Simple density-based rules:
        - Prioritize direction with highest density
        - Ensure fairness (no starvation)
        - Respect minimum/maximum timings
        """
        signal_decisions = []
        
        for junction_id, densities in state.junction_densities.items():
            decision = self.rule_engine.make_decision(
                junction_id=junction_id,
                densities=densities,
                current_signals=state.signal_states.get(junction_id, {}),
                predictions=predictions
            )
            signal_decisions.append(decision)
        
        return AgentDecisions(
            timestamp=time.time(),
            strategy_used="RULE_BASED",
            signal_decisions=signal_decisions,
            emergency_override=False,
            latency=0.0
        )
    
    async def _emergency_mode_decisions(self, 
                                        state: PerceivedState) -> AgentDecisions:
        """
        Emergency mode: delegate to emergency corridor manager (FRD-07)
        
        In emergency mode, signals along the corridor are set to GREEN
        for the emergency vehicle direction. Agent loop acknowledges 
        and passes through - actual control is by emergency module.
        """
        signal_decisions = []
        
        # If we have corridor info, generate green wave decisions
        if state.emergency_corridor:
            for junction_id in state.emergency_corridor:
                # Emergency vehicle gets priority - set green in corridor direction
                decision = SignalDecision(
                    junction_id=junction_id,
                    direction='N',  # Will be overridden by emergency manager
                    action='GREEN',
                    duration=self.default_green_time,
                    reason=f"Emergency corridor for {state.emergency_vehicle_id}"
                )
                signal_decisions.append(decision)
        
        return AgentDecisions(
            timestamp=time.time(),
            strategy_used="EMERGENCY",
            signal_decisions=signal_decisions,  # May be empty - handled by emergency module
            emergency_override=True,
            latency=0.0
        )
    
    async def _apply_manual_controls(self, state: PerceivedState) -> AgentDecisions:
        """Apply manual traffic control overrides"""
        signal_decisions = []
        
        for control in state.manual_controls:
            control_type = control.get('type', '')
            action = control.get('action', '')
            
            if control_type == 'JUNCTION' and action == 'FORCE_GREEN':
                params = control.get('parameters', {})
                decision = SignalDecision(
                    junction_id=control.get('targetId', ''),
                    direction=params.get('direction', 'N'),
                    action='GREEN',
                    duration=params.get('duration', self.default_green_time),
                    reason="Manual override by traffic controller"
                )
                signal_decisions.append(decision)
            
            elif control_type == 'JUNCTION' and action == 'FORCE_RED':
                params = control.get('parameters', {})
                decision = SignalDecision(
                    junction_id=control.get('targetId', ''),
                    direction=params.get('direction', 'N'),
                    action='RED',
                    duration=params.get('duration', self.default_green_time),
                    reason="Manual override by traffic controller"
                )
                signal_decisions.append(decision)
        
        return AgentDecisions(
            timestamp=time.time(),
            strategy_used="MANUAL",
            signal_decisions=signal_decisions,
            emergency_override=False,
            latency=0.0
        )
    
    def _state_to_observation(self, state: PerceivedState) -> np.ndarray:
        """
        Convert perceived state to RL observation format
        
        RL Observation Space: 63 dimensions (9 junctions × 7 features)
        Features per junction:
        - density_N, density_E, density_S, density_W (4 values)
        - avg_wait_time (1 value)
        - current_signal (1 value, encoded 0-3)
        - vehicle_count (1 value)
        
        Returns:
            np.ndarray of shape (63,) with float32 values
        """
        observation = []
        
        # Sort junctions for consistent order
        sorted_junctions = sorted(state.junction_densities.keys())
        
        # Pad or truncate to 9 junctions
        target_junctions = 9
        
        for i in range(target_junctions):
            if i < len(sorted_junctions):
                junction_id = sorted_junctions[i]
                densities = state.junction_densities[junction_id]
                
                # Density for each direction (4 values, normalized 0-1)
                observation.append(min(densities.get('N', 0.0) / 100.0, 1.0))
                observation.append(min(densities.get('E', 0.0) / 100.0, 1.0))
                observation.append(min(densities.get('S', 0.0) / 100.0, 1.0))
                observation.append(min(densities.get('W', 0.0) / 100.0, 1.0))
                
                # Average waiting time (from density tracker, normalized 0-1, max 100 seconds)
                avg_wait_time = self._get_waiting_time(junction_id)
                observation.append(min(avg_wait_time / 100.0, 1.0))
                
                # Current signal state (encoded 0-3)
                signal_states = state.signal_states.get(junction_id, {})
                green_dirs = [d for d, s in signal_states.items() if s == 'GREEN']
                signal_encoding = {'N': 0, 'E': 1, 'S': 2, 'W': 3}
                current_signal = signal_encoding.get(green_dirs[0], 0) / 3.0 if green_dirs else 0.0
                observation.append(current_signal)
                
                # Vehicle count at junction (normalized)
                vehicle_count = sum(densities.values()) / 4.0
                observation.append(min(vehicle_count / 50.0, 1.0))
            else:
                # Pad with zeros for missing junctions
                observation.extend([0.0] * 7)
        
        return np.array(observation, dtype=np.float32)
    
    def _get_waiting_time(self, junction_id: str) -> float:
        """
        Get average waiting time for a junction
        
        Retrieves waiting time from density tracker if available.
        Falls back to 0.0 if not available.
        
        Args:
            junction_id: Junction identifier
            
        Returns:
            Average waiting time in seconds (0-100 range)
        """
        if not self.density_tracker:
            return 0.0
        
        try:
            # Get junction density data from tracker
            junction_data = self.density_tracker.get_junction_density(junction_id)
            if junction_data and hasattr(junction_data, 'avg_waiting_time'):
                return junction_data.avg_waiting_time
        except Exception as e:
            # Silently fail and return 0.0
            pass
        
        return 0.0
    
    def _actions_to_decisions(self, actions: np.ndarray, 
                               state: PerceivedState) -> List[SignalDecision]:
        """
        Convert RL actions to signal decisions
        
        Actions are indices (0-3) mapping to directions (N, E, S, W)
        indicating which direction should get green light.
        """
        decisions = []
        direction_map = {0: 'N', 1: 'E', 2: 'S', 3: 'W'}
        
        sorted_junctions = sorted(state.junction_densities.keys())
        
        # Handle both single action (int) and array of actions
        if np.isscalar(actions):
            actions = [actions]
        elif len(actions.shape) == 0:
            actions = [int(actions)]
        
        for i, junction_id in enumerate(sorted_junctions):
            if i >= len(actions):
                break
            
            action_idx = int(actions[i]) if i < len(actions) else 0
            direction = direction_map.get(action_idx % 4, 'N')
            
            # Check if already green in this direction
            current_state = state.signal_states.get(junction_id, {})
            if current_state.get(direction) == 'GREEN':
                action_type = 'HOLD'
            else:
                action_type = 'GREEN'
            
            decision = SignalDecision(
                junction_id=junction_id,
                direction=direction,
                action=action_type,
                duration=self.default_green_time,
                reason=f"RL policy (action={action_idx})"
            )
            decisions.append(decision)
        
        return decisions
    
    def get_stats(self) -> dict:
        """Get decision module statistics"""
        avg_latency = (
            self._total_latency / self._decision_count 
            if self._decision_count > 0 else 0
        )
        
        # Get RL service stats if available
        rl_stats = {}
        if self.rl_service:
            rl_stats = self.rl_service.get_statistics()
        
        return {
            'decisionCount': self._decision_count,
            'avgLatency': round(avg_latency, 2),
            'rlDecisions': self._rl_decisions,
            'ruleDecisions': self._rule_decisions,
            'rlFallbackCount': self._rl_fallback_count,
            'hasRlAgent': self.rl_agent is not None,
            'rlServiceStats': rl_stats
        }
    
    def is_rl_available(self) -> bool:
        """Check if RL agent is available for decisions"""
        return self.rl_agent is not None


class RuleBasedEngine:
    """
    Simple rule-based decision engine (fallback)
    
    Rules:
    1. Green goes to highest density direction
    2. Minimum green time prevents rapid switching
    3. Maximum green time prevents starvation
    4. Consider predictions if available
    """
    
    def __init__(self):
        """Initialize rule engine"""
        self.min_green_time = 10
        self.max_green_time = 60
        self.default_duration = 30
        
        # Track green duration per junction
        self._green_start_times: Dict[str, float] = {}
        self._current_green_dirs: Dict[str, str] = {}
    
    def make_decision(self,
                     junction_id: str,
                     densities: Dict[str, float],
                     current_signals: Dict[str, str],
                     predictions: Optional[dict] = None) -> SignalDecision:
        """
        Make rule-based decision for a junction
        
        Args:
            junction_id: Junction identifier
            densities: Density per direction {'N': 0.5, 'E': 0.3, ...}
            current_signals: Current signal states {'N': 'RED', ...}
            predictions: Optional congestion predictions
            
        Returns:
            SignalDecision for this junction
        """
        # Find current green direction
        current_green = None
        for direction, state in current_signals.items():
            if state == 'GREEN':
                current_green = direction
                break
        
        # Find direction with highest density
        if densities:
            max_direction = max(densities.items(), key=lambda x: x[1])[0]
            max_density = densities[max_direction]
        else:
            max_direction = 'N'
            max_density = 0.0
        
        # Check if we need to switch
        now = time.time()
        green_start = self._green_start_times.get(junction_id, now)
        green_duration = now - green_start
        
        # Decision logic
        if current_green and current_green == max_direction:
            # Already green in correct direction - hold if not exceeded max
            if green_duration < self.max_green_time:
                return SignalDecision(
                    junction_id=junction_id,
                    direction=current_green,
                    action='HOLD',
                    duration=self.default_duration,
                    reason=f"Rule: Hold highest density ({max_density:.1f})"
                )
        
        # Check minimum green time
        if current_green and green_duration < self.min_green_time:
            return SignalDecision(
                junction_id=junction_id,
                direction=current_green,
                action='HOLD',
                duration=self.default_duration,
                reason=f"Rule: Min green time not reached ({green_duration:.0f}s)"
            )
        
        # Switch to highest density direction
        self._green_start_times[junction_id] = now
        self._current_green_dirs[junction_id] = max_direction
        
        return SignalDecision(
            junction_id=junction_id,
            direction=max_direction,
            action='GREEN',
            duration=self.default_duration,
            reason=f"Rule: Switch to highest density ({max_density:.1f})"
        )

