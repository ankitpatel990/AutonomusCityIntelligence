"""
Watchdog & Health Monitor

Implements FRD-05 FR-05.3: Watchdog mechanism.
Continuously monitors system health, detects failures, and triggers fail-safe when needed.
"""

import asyncio
import time
from typing import List, Dict, Callable, Optional
from dataclasses import dataclass

from app.safety.system_modes import SystemMode, SystemModeManager


@dataclass
class HealthCheck:
    """Health check configuration"""
    name: str
    check_function: Callable
    critical: bool  # If True, failure triggers fail-safe
    interval: float  # Seconds between checks
    timeout: float  # Maximum allowed check duration
    last_check: float = 0.0
    consecutive_failures: int = 0
    max_failures: int = 3  # Trigger fail-safe after this many failures


class Watchdog:
    """
    System watchdog - monitors health and triggers fail-safe
    
    Monitors:
    - Agent loop heartbeat (is it running?)
    - Signal conflicts (are signals safe?)
    - Decision latency (is system responsive?)
    - Database connectivity
    - Memory/CPU usage (optional)
    """
    
    def __init__(self, 
                 mode_manager: SystemModeManager,
                 simulation_manager=None,
                 agent_loop=None,
                 conflict_validator=None):
        """
        Initialize watchdog
        
        Args:
            mode_manager: SystemModeManager instance
            simulation_manager: SimulationManager instance
            agent_loop: AutonomousAgent instance
            conflict_validator: ConflictValidator instance
        """
        self.mode_manager = mode_manager
        self.simulation_manager = simulation_manager
        self.agent_loop = agent_loop
        self.conflict_validator = conflict_validator
        
        # Watchdog state
        self.running = False
        self.check_interval = 2.0  # seconds
        
        # Health checks registry
        self.health_checks: List[HealthCheck] = []
        
        # Statistics
        self.total_checks = 0
        self.total_failures = 0
        
        # Register standard health checks
        self._register_standard_checks()
        
        print("[SAFETY] Watchdog initialized")
        print(f"   Registered {len(self.health_checks)} health checks")
    
    def _register_standard_checks(self):
        """Register standard health checks"""
        
        # Check 1: Agent loop heartbeat
        self.health_checks.append(HealthCheck(
            name="agent_heartbeat",
            check_function=self._check_agent_heartbeat,
            critical=True,
            interval=5.0,
            timeout=1.0,
            max_failures=2
        ))
        
        # Check 2: Signal conflicts
        self.health_checks.append(HealthCheck(
            name="signal_conflicts",
            check_function=self._check_signal_conflicts,
            critical=True,
            interval=1.0,
            timeout=0.5,
            max_failures=1  # Immediate fail-safe on conflict
        ))
        
        # Check 3: Decision latency
        self.health_checks.append(HealthCheck(
            name="decision_latency",
            check_function=self._check_decision_latency,
            critical=False,
            interval=10.0,
            timeout=1.0,
            max_failures=5
        ))
        
        # Check 4: System mode validity
        self.health_checks.append(HealthCheck(
            name="mode_validity",
            check_function=self._check_mode_validity,
            critical=False,
            interval=5.0,
            timeout=0.5,
            max_failures=3
        ))
    
    async def start(self):
        """Start watchdog monitoring"""
        if self.running:
            print("[WATCHDOG] Watchdog already running")
            return
        
        self.running = True
        print("[WATCHDOG] Watchdog started")
        
        # Start monitoring loop
        asyncio.create_task(self._monitoring_loop())
    
    async def stop(self):
        """Stop watchdog monitoring"""
        self.running = False
        print("[WATCHDOG] Watchdog stopped")
    
    async def _monitoring_loop(self):
        """Main watchdog monitoring loop"""
        while self.running:
            try:
                # Run all health checks
                await self._run_health_checks()
                
                # Wait for next check interval
                await asyncio.sleep(self.check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[WATCHDOG] Watchdog error: {e}")
                await asyncio.sleep(1)
    
    async def _run_health_checks(self):
        """Run all registered health checks"""
        current_time = time.time()
        
        for check in self.health_checks:
            # Check if it's time to run this check
            if current_time - check.last_check < check.interval:
                continue
            
            # Run the check
            try:
                check_start = time.time()
                
                # Run with timeout
                passed = await asyncio.wait_for(
                    check.check_function(),
                    timeout=check.timeout
                )
                
                check_duration = time.time() - check_start
                
                # Update check record
                check.last_check = current_time
                self.total_checks += 1
                
                if passed:
                    # Check passed - reset failure counter
                    if check.consecutive_failures > 0:
                        print(f"[WATCHDOG] {check.name}: Recovered")
                    check.consecutive_failures = 0
                else:
                    # Check failed
                    check.consecutive_failures += 1
                    self.total_failures += 1
                    
                    print(f"[WATCHDOG] {check.name}: FAILED "
                          f"({check.consecutive_failures}/{check.max_failures})")
                    
                    # Trigger fail-safe if critical and max failures reached
                    if check.critical and check.consecutive_failures >= check.max_failures:
                        await self._trigger_fail_safe(
                            f"Critical health check failed: {check.name}"
                        )
                
            except asyncio.TimeoutError:
                check.consecutive_failures += 1
                print(f"[WATCHDOG] {check.name}: TIMEOUT")
                
                if check.critical and check.consecutive_failures >= check.max_failures:
                    await self._trigger_fail_safe(
                        f"Health check timeout: {check.name}"
                    )
            
            except Exception as e:
                check.consecutive_failures += 1
                print(f"[WATCHDOG] {check.name}: ERROR - {e}")
    
    # Health check implementations
    
    async def _check_agent_heartbeat(self) -> bool:
        """Check if agent loop is alive and running"""
        if not self.agent_loop:
            return True  # No agent loop is OK if not initialized
        
        # Check if agent is running
        if hasattr(self.agent_loop, 'status'):
            if self.agent_loop.status.value != "RUNNING":
                return True  # Not running is OK if stopped intentionally
        
        # Check time since last decision
        if hasattr(self.agent_loop, 'stats'):
            if hasattr(self.agent_loop.stats, 'last_decision_time'):
                time_since_decision = time.time() - self.agent_loop.stats.last_decision_time
                
                # Should have made a decision in last 10 seconds
                if time_since_decision > 10.0:
                    print(f"[WATCHDOG] Agent stalled: {time_since_decision:.1f}s since last decision")
                    return False
        
        return True
    
    async def _check_signal_conflicts(self) -> bool:
        """Check for signal conflicts at all junctions"""
        if not self.conflict_validator or not self.simulation_manager:
            return True  # No validator or simulation manager is OK
        
        try:
            # Get junctions
            junctions = []
            if hasattr(self.simulation_manager, 'get_junctions'):
                junctions = self.simulation_manager.get_junctions() or []
            elif hasattr(self.simulation_manager, 'junctions'):
                junctions = self.simulation_manager.junctions or []
            
            # Validate signals at each junction
            for junction in junctions:
                if hasattr(junction, 'signals'):
                    is_valid, issues = self.conflict_validator.validate_full_junction(junction.signals)
                    
                    if not is_valid:
                        print(f"[WATCHDOG] Signal conflict at {junction.id}: {issues}")
                        return False
        except Exception as e:
            print(f"[WATCHDOG] Error checking conflicts: {e}")
            return False
        
        return True
    
    async def _check_decision_latency(self) -> bool:
        """Check if decision making is within acceptable latency"""
        if not self.agent_loop:
            return True
        
        if hasattr(self.agent_loop, 'stats'):
            if hasattr(self.agent_loop.stats, 'avg_latency'):
                avg_latency = self.agent_loop.stats.avg_latency
                
                # Average latency should be < 2000ms
                if avg_latency > 2000:
                    print(f"[WATCHDOG] High decision latency: {avg_latency:.1f}ms")
                    return False
        
        return True
    
    async def _check_mode_validity(self) -> bool:
        """Check if system mode is valid"""
        # Check if stuck in EMERGENCY mode too long
        if self.mode_manager.get_current_mode() == SystemMode.EMERGENCY:
            duration = self.mode_manager.get_mode_duration()
            if duration > 300:  # 5 minutes
                print(f"[WATCHDOG] Stuck in EMERGENCY mode for {duration:.0f}s")
                return False
        
        return True
    
    async def _trigger_fail_safe(self, reason: str):
        """
        Trigger fail-safe mode
        
        Args:
            reason: Reason for fail-safe trigger
        """
        print(f"[FAIL-SAFE] TRIGGERING FAIL-SAFE: {reason}")
        
        # Transition to fail-safe mode
        self.mode_manager.enter_fail_safe(reason)
        
        # Stop agent loop
        if self.agent_loop and hasattr(self.agent_loop, 'stop'):
            try:
                await self.agent_loop.stop()
            except Exception as e:
                print(f"[FAIL-SAFE] Error stopping agent: {e}")
        
        # Set all signals to safe default state (all RED with one GREEN)
        await self._set_safe_signal_state()
    
    async def _set_safe_signal_state(self):
        """Set all signals to safe default state"""
        if not self.simulation_manager:
            return
        
        try:
            junctions = []
            if hasattr(self.simulation_manager, 'get_junctions'):
                junctions = self.simulation_manager.get_junctions() or []
            elif hasattr(self.simulation_manager, 'junctions'):
                junctions = self.simulation_manager.junctions or []
            
            for junction in junctions:
                # Set all to RED except North (safe default)
                if hasattr(self.simulation_manager, 'set_signal_green'):
                    await self.simulation_manager.set_signal_green(
                        junction.id,
                        'north',
                        duration=9999  # Very long duration
                    )
        except Exception as e:
            print(f"[FAIL-SAFE] Error setting safe state: {e}")
        
        print("[FAIL-SAFE] All signals set to safe state")
    
    def get_health_status(self) -> dict:
        """Get overall system health status"""
        checks_status = []
        
        for check in self.health_checks:
            checks_status.append({
                'name': check.name,
                'critical': check.critical,
                'consecutiveFailures': check.consecutive_failures,
                'maxFailures': check.max_failures,
                'healthy': check.consecutive_failures == 0
            })
        
        all_healthy = all(c['healthy'] for c in checks_status)
        
        return {
            'running': self.running,
            'healthy': all_healthy,
            'totalChecks': self.total_checks,
            'totalFailures': self.total_failures,
            'checks': checks_status
        }

