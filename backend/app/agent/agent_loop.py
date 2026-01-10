"""
Autonomous Agent Loop

Core agent loop that orchestrates the entire system.
Implements FRD-03 Autonomous Agent Loop & Integration requirements.

The agent executes a continuous loop:
1. PERCEIVE - Read current state from density tracker, simulation
2. PREDICT - Run congestion prediction (optional)
3. DECIDE - Determine signal actions using RL/rules/manual
4. ACT - Execute actions with safety validation
5. MONITOR - Check health and safety

Performance Requirements (FRD-03):
- Loop cycle: < 2 seconds
- Execution time: < 500ms
- Decision latency: < 100ms (RL), < 50ms (rules)
"""

import asyncio
import time
import json
from enum import Enum
from typing import Optional, Any, TYPE_CHECKING
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from app.agent.perception import PerceptionModule, PerceivedState
    from app.agent.decision import DecisionModule, AgentDecisions
    from app.agent.action import ActionModule
    from app.agent.monitoring import MonitoringModule


class AgentStatus(str, Enum):
    """Agent operational status"""
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"


class AgentStrategy(str, Enum):
    """Decision-making strategy"""
    RL = "RL"
    RULE_BASED = "RULE_BASED"
    MANUAL = "MANUAL"


@dataclass
class AgentStatistics:
    """Agent performance statistics"""
    loop_count: int = 0
    total_latency: float = 0.0
    last_decision_time: float = 0.0
    errors_count: int = 0
    avg_latency: float = 0.0
    decisions_made: int = 0
    start_time: float = field(default_factory=time.time)
    
    def reset(self):
        """Reset statistics"""
        self.loop_count = 0
        self.total_latency = 0.0
        self.last_decision_time = 0.0
        self.errors_count = 0
        self.avg_latency = 0.0
        self.decisions_made = 0
        self.start_time = time.time()


class AutonomousAgent:
    """
    Central autonomous agent that orchestrates the entire system
    
    Executes continuous loop:
    1. PERCEIVE - Read current state
    2. PREDICT - Run congestion prediction (optional)
    3. DECIDE - Determine signal actions
    4. ACT - Execute actions
    5. MONITOR - Check health and safety
    
    Usage:
        agent = AutonomousAgent(config, simulation_manager, density_tracker)
        agent.inject_modules(perception, prediction, decision, action, monitor)
        await agent.start(AgentStrategy.RL)
        
        # Later...
        await agent.stop()
    """
    
    def __init__(self, config: dict = None, simulation_manager=None, density_tracker=None):
        """
        Initialize the Autonomous Agent
        
        Args:
            config: System configuration dictionary
            simulation_manager: Simulation manager instance (optional)
            density_tracker: Density tracker instance (optional)
        """
        self.config = config or {}
        self.simulation_manager = simulation_manager
        self.density_tracker = density_tracker
        
        # State
        self.status = AgentStatus.STOPPED
        self.strategy = AgentStrategy.RL
        
        # Sub-modules (to be injected)
        self.perception: Optional['PerceptionModule'] = None
        self.prediction = None  # Optional: FRD-06
        self.decision: Optional['DecisionModule'] = None
        self.action: Optional['ActionModule'] = None
        self.monitor: Optional['MonitoringModule'] = None
        
        # Statistics
        self.stats = AgentStatistics()
        
        # Configuration
        self.loop_interval = config.get('loopInterval', 1.0) if config else 1.0  # seconds
        self.max_errors = config.get('maxErrors', 5) if config else 5
        
        # Control
        self._task: Optional[asyncio.Task] = None
        self._pause_event = asyncio.Event()
        self._pause_event.set()  # Start unpaused
        
        # WebSocket emitter (for broadcasting updates)
        self._ws_emitter = None
        
        # Last cycle data (for API access)
        self._last_state: Optional['PerceivedState'] = None
        self._last_decisions: Optional['AgentDecisions'] = None
        
        print("[AGENT] Autonomous Agent initialized")
    
    def inject_modules(self, perception=None, prediction=None, decision=None, action=None, monitor=None):
        """
        Inject sub-modules (dependency injection pattern)
        
        Args:
            perception: PerceptionModule instance
            prediction: PredictionModule instance (optional, FRD-06)
            decision: DecisionModule instance
            action: ActionModule instance
            monitor: MonitoringModule instance
        """
        if perception:
            self.perception = perception
        if prediction:
            self.prediction = prediction
        if decision:
            self.decision = decision
        if action:
            self.action = action
        if monitor:
            self.monitor = monitor
        
        print("[OK] Agent modules injected")
    
    def set_ws_emitter(self, emitter):
        """Set WebSocket emitter for broadcasting updates"""
        self._ws_emitter = emitter
    
    async def start(self, strategy: AgentStrategy = AgentStrategy.RL):
        """
        Start the autonomous agent loop
        
        Args:
            strategy: Decision strategy (RL/RULE_BASED/MANUAL)
        """
        if self.status == AgentStatus.RUNNING:
            print("[WARN] Agent already running")
            return
        
        # Validate modules are injected
        if not self._validate_modules():
            raise RuntimeError("Agent modules not properly configured")
        
        self.status = AgentStatus.RUNNING
        self.strategy = strategy
        self.stats.reset()
        self._pause_event.set()
        
        print(f"[START] Agent started with strategy: {strategy.value}")
        
        # Broadcast status
        await self._broadcast_status_update()
        
        # Start main loop as async task
        self._task = asyncio.create_task(self._main_loop())
    
    def _validate_modules(self) -> bool:
        """Validate all required modules are injected"""
        if not self.perception:
            print("[ERROR] Perception module not injected")
            return False
        if not self.decision:
            print("[ERROR] Decision module not injected")
            return False
        if not self.action:
            print("[ERROR] Action module not injected")
            return False
        if not self.monitor:
            print("[ERROR] Monitor module not injected")
            return False
        return True
    
    async def _main_loop(self):
        """
        Main agent loop - runs continuously
        
        Executes Perceive → Predict → Decide → Act → Monitor cycle
        """
        print("[LOOP] Agent main loop started")
        
        while self.status in (AgentStatus.RUNNING, AgentStatus.PAUSED):
            try:
                # Wait if paused
                await self._pause_event.wait()
                
                # Check if still running after pause
                if self.status != AgentStatus.RUNNING:
                    break
                
                # Execute one cycle
                await self.execute_loop_cycle()
                
                # Wait for next cycle
                await asyncio.sleep(self.loop_interval)
                
            except asyncio.CancelledError:
                print("[STOP] Agent loop cancelled")
                break
            except Exception as e:
                print(f"[ERROR] Agent loop error: {e}")
                self.stats.errors_count += 1
                
                # Handle error through monitor
                if self.monitor:
                    await self.monitor.handle_error(e)
                
                # Error recovery
                if self.stats.errors_count >= self.max_errors:
                    print("[CRITICAL] Too many errors, stopping agent")
                    await self.stop()
                    break
                
                # Continue on transient errors
                await asyncio.sleep(1)
        
        print("[LOOP] Agent main loop exited")
    
    async def execute_loop_cycle(self):
        """
        Execute one complete agent loop cycle
        
        Steps:
        1. PERCEIVE - Read current state
        2. PREDICT - Run congestion prediction
        3. DECIDE - Determine actions
        4. ACT - Execute actions
        5. MONITOR - Check health
        
        Performance tracked and logged
        """
        start_time = time.time()
        
        try:
            # 1. PERCEIVE: Read current state
            state = await self.perception.perceive()
            self._last_state = state
            
            # 2. PREDICT: Run congestion prediction (optional)
            predictions = None
            if self.prediction:
                predictions = await self.prediction.predict(state)
            
            # 3. DECIDE: Determine actions
            decisions = await self.decision.decide(state, predictions, self.strategy)
            self._last_decisions = decisions
            
            # 4. ACT: Execute actions
            await self.action.execute(decisions)
            
            # 5. MONITOR: Check health and safety
            await self.monitor.check(state, decisions)
            
            # Update statistics
            latency = (time.time() - start_time) * 1000  # ms
            self.stats.loop_count += 1
            self.stats.total_latency += latency
            self.stats.last_decision_time = time.time()
            self.stats.avg_latency = self.stats.total_latency / self.stats.loop_count
            self.stats.decisions_made += len(decisions.signal_decisions) if decisions else 0
            
            # Log cycle to database (async, non-blocking)
            await self._log_cycle(state, decisions, latency)
            
            # Broadcast decision (via WebSocket)
            await self._broadcast_decision(decisions, latency)
            
            # Debug output (every 10 cycles)
            if self.stats.loop_count % 10 == 0:
                print(f"[CYCLE] Cycle {self.stats.loop_count}: {latency:.1f}ms "
                      f"(avg: {self.stats.avg_latency:.1f}ms)")
            
        except Exception as e:
            print(f"[ERROR] Cycle execution error: {e}")
            raise
    
    async def stop(self):
        """Stop the agent loop"""
        if self.status == AgentStatus.STOPPED:
            return
        
        print("[STOP] Stopping agent...")
        self.status = AgentStatus.STOPPED
        self._pause_event.set()  # Unblock if paused
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        
        # Broadcast status
        await self._broadcast_status_update()
        
        print("[OK] Agent stopped")
    
    async def pause(self):
        """Pause the agent loop"""
        if self.status != AgentStatus.RUNNING:
            return
        
        self.status = AgentStatus.PAUSED
        self._pause_event.clear()
        
        # Broadcast status
        await self._broadcast_status_update()
        
        print("[PAUSE] Agent paused")
    
    async def resume(self):
        """Resume the agent loop"""
        if self.status != AgentStatus.PAUSED:
            return
        
        self.status = AgentStatus.RUNNING
        self._pause_event.set()
        
        # Broadcast status
        await self._broadcast_status_update()
        
        print("[RESUME] Agent resumed")
    
    def get_statistics(self) -> dict:
        """Get agent performance statistics"""
        uptime = time.time() - self.stats.start_time if self.stats.loop_count > 0 else 0
        
        return {
            "status": self.status.value,
            "strategy": self.strategy.value,
            "loopCount": self.stats.loop_count,
            "avgLatency": round(self.stats.avg_latency, 2),
            "lastDecisionTime": self.stats.last_decision_time,
            "errorsCount": self.stats.errors_count,
            "decisionsCount": self.stats.decisions_made,
            "uptime": round(uptime, 2)
        }
    
    def get_last_state(self) -> Optional['PerceivedState']:
        """Get last perceived state"""
        return self._last_state
    
    def get_last_decisions(self) -> Optional['AgentDecisions']:
        """Get last decisions made"""
        return self._last_decisions
    
    async def _log_cycle(self, state: 'PerceivedState', decisions: 'AgentDecisions', latency: float):
        """
        Log agent loop cycle to database
        
        Runs asynchronously to not block agent loop
        """
        try:
            # Run in background thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            loop.run_in_executor(
                None,
                self._write_log_to_db,
                state,
                decisions,
                latency
            )
        except Exception as e:
            print(f"[WARN] Logging error: {e}")
            # Don't let logging errors crash the agent
    
    def _write_log_to_db(self, state: 'PerceivedState', decisions: 'AgentDecisions', latency: float):
        """Write log entry to database (runs in thread pool)"""
        try:
            from app.database.database import SessionLocal
            from app.database.models import AgentLog
            
            db = SessionLocal()
            
            try:
                # Create log entry
                log = AgentLog(
                    timestamp=state.timestamp if state else time.time(),
                    mode=self._get_system_mode(state),
                    strategy=decisions.strategy_used if decisions else self.strategy.value,
                    decision_latency=latency,
                    decisions_json=json.dumps([
                        {
                            'junction': d.junction_id,
                            'direction': d.direction,
                            'action': d.action,
                            'duration': d.duration,
                            'reason': d.reason
                        }
                        for d in (decisions.signal_decisions if decisions else [])
                    ]),
                    state_summary_json=json.dumps({
                        'totalVehicles': state.total_vehicles if state else 0,
                        'vehiclesByType': state.vehicles_by_type if state else {},
                        'avgDensity': state.city_avg_density if state else 0,
                        'congestionPoints': state.congestion_points if state else 0,
                        'emergencyActive': state.emergency_active if state else False
                    })
                )
                
                db.add(log)
                db.commit()
                
            except Exception as e:
                print(f"[ERROR] Database logging error: {e}")
                db.rollback()
            finally:
                db.close()
                
        except Exception as e:
            print(f"[ERROR] Log write error: {e}")
    
    def _get_system_mode(self, state: Optional['PerceivedState']) -> str:
        """Determine system mode from state"""
        if not state:
            return "NORMAL"
        if state.emergency_active:
            return "EMERGENCY"
        elif state.manual_controls:
            return "MANUAL"
        else:
            return "NORMAL"
    
    async def _broadcast_status_update(self):
        """Broadcast agent status via WebSocket"""
        if self._ws_emitter:
            try:
                stats = self.get_statistics()
                await self._ws_emitter.emit_agent_status_update(
                    status=stats['status'],
                    strategy=stats['strategy'],
                    uptime=stats['uptime'],
                    decisions=stats['decisionsCount'],
                    avg_latency=stats['avgLatency']
                )
            except Exception as e:
                print(f"[WARN] WebSocket broadcast error: {e}")
    
    async def _broadcast_decision(self, decisions: 'AgentDecisions', latency: float):
        """Broadcast agent decision via WebSocket"""
        if self._ws_emitter and decisions:
            try:
                await self._ws_emitter.emit_agent_decision({
                    'timestamp': decisions.timestamp,
                    'decisions': [
                        {
                            'junction': d.junction_id,
                            'direction': d.direction,
                            'action': d.action,
                            'duration': d.duration,
                            'reason': d.reason
                        }
                        for d in decisions.signal_decisions
                    ],
                    'latency': latency,
                    'strategy': decisions.strategy_used,
                    'mode': 'EMERGENCY' if decisions.emergency_override else 'NORMAL'
                })
            except Exception as e:
                print(f"[WARN] Decision broadcast error: {e}")


# Global agent instance
_agent: Optional[AutonomousAgent] = None


def get_agent() -> Optional[AutonomousAgent]:
    """Get the global agent instance"""
    return _agent


def init_agent(config: dict = None, simulation_manager=None, density_tracker=None) -> AutonomousAgent:
    """Initialize the global agent instance"""
    global _agent
    _agent = AutonomousAgent(config, simulation_manager, density_tracker)
    return _agent


def set_agent(agent: AutonomousAgent):
    """Set the global agent instance"""
    global _agent
    _agent = agent


async def cleanup_old_logs(retention_days: int = 7):
    """
    Clean up old agent logs
    
    Should be run periodically (e.g., daily)
    
    Args:
        retention_days: Number of days to retain logs
    """
    try:
        from app.database.database import SessionLocal
        from app.database.models import AgentLog
        
        db = SessionLocal()
        
        try:
            cutoff_time = time.time() - (retention_days * 24 * 3600)
            
            deleted = db.query(AgentLog)\
                .filter(AgentLog.timestamp < cutoff_time)\
                .delete()
            
            db.commit()
            
            print(f"[CLEANUP] Cleaned up {deleted} old agent logs")
            
        except Exception as e:
            print(f"[ERROR] Log cleanup error: {e}")
            db.rollback()
        finally:
            db.close()
            
    except Exception as e:
        print(f"[ERROR] Cleanup error: {e}")

