"""
Monitoring Module

Monitor agent loop health and trigger fail-safe when needed.
Implements FRD-03 FR-03.5: Health monitoring requirements.

Checks:
- Decision latency
- Signal conflicts
- Loop frequency/stalls
- Error rates

Integration:
- FRD-05 (Safety & Fail-Safe) for fail-safe activation

Performance Requirements:
- Monitoring overhead: < 20ms
"""

from typing import List, Dict, Any, Optional, TYPE_CHECKING
import time

if TYPE_CHECKING:
    from app.agent.perception import PerceivedState
    from app.agent.decision import AgentDecisions


class MonitoringModule:
    """
    Monitor agent loop health
    
    Checks:
    - Decision latency thresholds
    - Signal conflicts (multiple greens)
    - Loop frequency/stalls
    - Error rates
    
    Triggers fail-safe mode when issues detected.
    
    Usage:
        monitor = MonitoringModule()
        monitor.set_failsafe_handler(failsafe_handler)
        await monitor.check(state, decisions)
    """
    
    def __init__(self):
        """Initialize the Monitoring Module"""
        # Error tracking
        self.error_count = 0
        self.max_errors = 5
        self.consecutive_errors = 0
        
        # Timing tracking
        self.last_check_time = time.time()
        self.check_count = 0
        
        # Thresholds
        self.max_decision_latency = 2000  # 2 seconds (ms)
        self.max_loop_interval = 5.0  # seconds
        self.conflict_tolerance = 0  # No conflicts allowed
        
        # Fail-safe handler (FRD-05)
        self._failsafe_handler = None
        
        # WebSocket emitter for alerts
        self._ws_emitter = None
        
        # Alert history (prevent spam)
        self._recent_alerts: Dict[str, float] = {}
        self._alert_cooldown = 10.0  # seconds
        
        # Statistics
        self._warnings_issued = 0
        self._failsafe_triggers = 0
        
        print("[MONITOR] Monitoring module initialized")
    
    def set_failsafe_handler(self, handler):
        """Set fail-safe handler from FRD-05"""
        self._failsafe_handler = handler
        print("[OK] Fail-safe handler injected into monitoring module")
    
    def set_ws_emitter(self, emitter):
        """Set WebSocket emitter for alerts"""
        self._ws_emitter = emitter
    
    async def check(self, state: 'PerceivedState', decisions: 'AgentDecisions'):
        """
        Check system health
        
        Performs all health checks and triggers appropriate responses.
        
        Args:
            state: Current system state
            decisions: Decisions that were made
        """
        start_time = time.time()
        
        try:
            # Check decision latency
            if decisions and decisions.latency > self.max_decision_latency:
                await self._warn(
                    "HIGH_LATENCY",
                    "Decision latency too high",
                    f"{decisions.latency:.1f}ms exceeds {self.max_decision_latency}ms threshold"
                )
            
            # Check for signal conflicts
            if state:
                conflicts = self._detect_conflicts(state)
                if conflicts:
                    await self._trigger_failsafe(
                        "SIGNAL_CONFLICT",
                        "Signal conflicts detected",
                        conflicts
                    )
            
            # Check agent loop frequency (stall detection)
            time_since_last = time.time() - self.last_check_time
            if time_since_last > self.max_loop_interval and self.check_count > 0:
                await self._warn(
                    "LOOP_STALL",
                    "Agent loop stalled",
                    f"{time_since_last:.1f}s since last check exceeds {self.max_loop_interval}s"
                )
            
            # Update timing
            self.last_check_time = time.time()
            self.check_count += 1
            
            # Reset consecutive errors on successful check
            self.consecutive_errors = 0
            
        except Exception as e:
            print(f"[WARN] Monitoring check error: {e}")
        
        # Performance check
        check_time = (time.time() - start_time) * 1000
        if check_time > 20:
            print(f"[WARN] Slow monitoring: {check_time:.1f}ms")
    
    async def handle_error(self, error: Exception):
        """
        Handle agent loop errors
        
        Args:
            error: Exception that occurred
        """
        self.error_count += 1
        self.consecutive_errors += 1
        
        print(f"[WARN] Agent error #{self.error_count}: {error}")
        
        # Check for critical error threshold
        if self.consecutive_errors >= self.max_errors:
            await self._trigger_failsafe(
                "ERROR_THRESHOLD",
                "Too many consecutive errors",
                f"{self.consecutive_errors} errors in a row"
            )
    
    def _detect_conflicts(self, state: 'PerceivedState') -> List[str]:
        """
        Detect signal conflicts
        
        A conflict is when multiple signals are GREEN at the same junction.
        This is a critical safety issue.
        
        Args:
            state: Current perceived state
            
        Returns:
            List of conflict descriptions
        """
        conflicts = []
        
        if not state or not state.signal_states:
            return conflicts
        
        for junction_id, signals in state.signal_states.items():
            if not signals:
                continue
            
            # Count green signals
            green_count = sum(1 for s in signals.values() if s == 'GREEN')
            
            # More than one green is a conflict
            if green_count > 1:
                green_dirs = [d for d, s in signals.items() if s == 'GREEN']
                conflicts.append(
                    f"{junction_id}: {green_count} greens ({', '.join(green_dirs)})"
                )
        
        return conflicts
    
    async def _warn(self, alert_type: str, message: str, details: str):
        """
        Issue warning
        
        Args:
            alert_type: Type of alert
            message: Warning message
            details: Additional details
        """
        # Check cooldown
        now = time.time()
        last_alert = self._recent_alerts.get(alert_type, 0)
        if now - last_alert < self._alert_cooldown:
            return  # Skip - too recent
        
        self._recent_alerts[alert_type] = now
        self._warnings_issued += 1
        
        print(f"[WARNING] {message}: {details}")
        
        # Broadcast via WebSocket
        if self._ws_emitter:
            try:
                await self._ws_emitter.emit_system_state_update({
                    'alert': {
                        'type': alert_type,
                        'message': message,
                        'details': details,
                        'severity': 'WARNING'
                    }
                })
            except Exception as e:
                print(f"[WARN] Alert broadcast error: {e}")
    
    async def _trigger_failsafe(self, reason_type: str, reason: str, details: Any):
        """
        Trigger fail-safe mode
        
        Delegates to FRD-05 Safety module for actual fail-safe activation.
        
        Args:
            reason_type: Type of failure
            reason: Human-readable reason
            details: Additional details
        """
        self._failsafe_triggers += 1
        
        print(f"[FAILSAFE] Triggered: {reason}")
        print(f"   Details: {details}")
        
        # Call FRD-05 fail-safe handler if available
        if self._failsafe_handler:
            try:
                if hasattr(self._failsafe_handler, 'activate'):
                    await self._failsafe_handler.activate(reason, details)
                elif hasattr(self._failsafe_handler, 'trigger'):
                    await self._failsafe_handler.trigger(reason, details)
            except Exception as e:
                print(f"[ERROR] Fail-safe handler error: {e}")
        
        # Broadcast via WebSocket
        if self._ws_emitter:
            try:
                # Get affected junctions
                affected_junctions = []
                if isinstance(details, list):
                    affected_junctions = [d.split(':')[0] for d in details if ':' in d]
                
                await self._ws_emitter.emit_failsafe_triggered(
                    reason=reason,
                    affected_junctions=affected_junctions,
                    previous_mode="NORMAL"
                )
            except Exception as e:
                print(f"[WARN] Failsafe broadcast error: {e}")
    
    def get_statistics(self) -> dict:
        """Get monitoring statistics"""
        return {
            'checkCount': self.check_count,
            'errorCount': self.error_count,
            'consecutiveErrors': self.consecutive_errors,
            'warningsIssued': self._warnings_issued,
            'failsafeTriggers': self._failsafe_triggers,
            'lastCheckTime': self.last_check_time
        }
    
    def reset_error_count(self):
        """Reset error counters"""
        self.error_count = 0
        self.consecutive_errors = 0


class HealthChecker:
    """
    Additional health checks for the system
    
    Can be used for periodic deep health checks.
    """
    
    def __init__(self):
        """Initialize health checker"""
        self._last_deep_check = 0
        self._deep_check_interval = 60.0  # seconds
    
    async def deep_check(self, state: 'PerceivedState') -> Dict[str, Any]:
        """
        Perform deep health check
        
        Returns comprehensive health status.
        """
        now = time.time()
        
        # Throttle deep checks
        if now - self._last_deep_check < self._deep_check_interval:
            return {'skipped': True}
        
        self._last_deep_check = now
        
        health = {
            'timestamp': now,
            'overall': 'HEALTHY',
            'checks': []
        }
        
        # Check vehicle count reasonable
        if state:
            if state.total_vehicles > 1000:
                health['checks'].append({
                    'name': 'vehicle_count',
                    'status': 'WARNING',
                    'message': f'High vehicle count: {state.total_vehicles}'
                })
            else:
                health['checks'].append({
                    'name': 'vehicle_count',
                    'status': 'OK',
                    'message': f'Vehicle count: {state.total_vehicles}'
                })
            
            # Check congestion
            if state.congestion_points > 5:
                health['checks'].append({
                    'name': 'congestion',
                    'status': 'WARNING',
                    'message': f'High congestion: {state.congestion_points} points'
                })
            else:
                health['checks'].append({
                    'name': 'congestion',
                    'status': 'OK',
                    'message': f'Congestion points: {state.congestion_points}'
                })
        
        # Determine overall status
        statuses = [c['status'] for c in health['checks']]
        if 'ERROR' in statuses:
            health['overall'] = 'UNHEALTHY'
        elif 'WARNING' in statuses:
            health['overall'] = 'DEGRADED'
        
        return health

