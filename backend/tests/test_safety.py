"""
Safety System Integration Tests

Tests for FRD-05: Safety & Fail-Safe Monitoring Systems.
Comprehensive testing of all safety systems including conflict prevention,
fail-safe triggers, manual overrides, and integration with agent loop.
"""

import pytest
import asyncio
import time
from app.safety.conflict_validator import ConflictValidator
from app.safety.system_modes import SystemModeManager, SystemMode
from app.safety.watchdog import Watchdog
from app.safety.manual_override import ManualOverrideManager
from app.models.junction import SignalColor, SignalState, JunctionSignals, create_default_signals


def test_conflict_validator_creation():
    """Test conflict validator creates"""
    validator = ConflictValidator()
    assert validator is not None
    assert validator.min_red_time == 2
    assert validator.min_green_time == 10


def test_conflict_detection():
    """Test detection of signal conflicts"""
    validator = ConflictValidator()
    
    # Create junction with conflict (two GREEN signals)
    signals = create_test_junction_with_conflict()
    
    is_valid, issues = validator.validate_full_junction(signals)
    
    assert not is_valid
    assert len(issues) > 0
    assert 'Multiple GREEN' in issues[0]


def test_no_conflict():
    """Test valid signal state (no conflict)"""
    validator = ConflictValidator()
    
    signals = create_test_junction_valid()
    
    is_valid, issues = validator.validate_full_junction(signals)
    
    assert is_valid or all('WARNING' in i for i in issues)


def test_green_conflict_prevention():
    """Test prevention of conflicting GREEN signals"""
    validator = ConflictValidator()
    
    # Current: North is GREEN
    signals = create_test_junction_north_green()
    
    # Try to make East GREEN (should fail)
    current_time = time.time()
    is_safe, reason = validator.validate_signal_change(
        junction_id='J-1',
        target_direction='E',
        target_color=SignalColor.GREEN,
        current_signals=signals,
        current_time=current_time
    )
    
    assert not is_safe
    assert 'Conflict' in reason


def test_mode_transitions():
    """Test system mode transitions"""
    manager = SystemModeManager()
    
    # Should start in NORMAL
    assert manager.get_current_mode() == SystemMode.NORMAL
    
    # NORMAL -> EMERGENCY (valid)
    success = manager.transition_to(SystemMode.EMERGENCY, "Test emergency")
    assert success
    assert manager.get_current_mode() == SystemMode.EMERGENCY
    
    # EMERGENCY -> NORMAL (valid)
    success = manager.transition_to(SystemMode.NORMAL, "Emergency cleared")
    assert success
    
    # NORMAL -> FAIL_SAFE (always valid)
    manager.enter_fail_safe("Test fail-safe")
    assert manager.get_current_mode() == SystemMode.FAIL_SAFE
    
    # FAIL_SAFE -> NORMAL (requires manual)
    success = manager.transition_to(SystemMode.NORMAL, "Test")  # Should fail
    assert not success
    
    success = manager.exit_fail_safe("operator-1")  # Should succeed
    assert success


def test_invalid_transitions():
    """Test invalid mode transitions are rejected"""
    manager = SystemModeManager()
    
    # EMERGENCY -> INCIDENT (invalid)
    manager.transition_to(SystemMode.EMERGENCY, "Test")
    success = manager.transition_to(SystemMode.INCIDENT, "Test")
    assert not success


@pytest.mark.asyncio
async def test_watchdog_health_checks():
    """Test watchdog health check execution"""
    mode_manager = SystemModeManager()
    watchdog = Watchdog(
        mode_manager=mode_manager,
        simulation_manager=None,
        agent_loop=None,
        conflict_validator=None
    )
    
    # Should be able to get health status
    status = watchdog.get_health_status()
    assert 'running' in status
    assert 'healthy' in status
    assert 'checks' in status


@pytest.mark.asyncio
async def test_manual_override_signal():
    """Test manual signal override"""
    override_manager = ManualOverrideManager(
        simulation_manager=None,
        agent_loop=None,
        mode_manager=None
    )
    
    # Should be able to create override
    override_id = await override_manager.force_signal_state(
        junction_id='J-1',
        direction='north',
        duration=30,
        operator_id='operator-1',
        reason='Test override'
    )
    
    assert override_id is not None
    assert override_id.startswith('OVR-')
    
    # Check active overrides
    overrides = override_manager.get_active_overrides()
    assert len(overrides) > 0


@pytest.mark.asyncio
async def test_manual_agent_disable():
    """Test manual agent disable"""
    override_manager = ManualOverrideManager(
        simulation_manager=None,
        agent_loop=None,
        mode_manager=None
    )
    
    # Should be able to disable agent
    override_id = await override_manager.disable_autonomous_agent(
        operator_id='operator-1',
        reason='Test disable'
    )
    
    assert override_id is not None
    
    # Should be able to enable agent
    success = await override_manager.enable_autonomous_agent('operator-1')
    assert success


@pytest.mark.asyncio
async def test_emergency_stop():
    """Test emergency stop functionality"""
    override_manager = ManualOverrideManager(
        simulation_manager=None,
        agent_loop=None,
        mode_manager=None
    )
    
    # Should be able to trigger emergency stop
    override_id = await override_manager.emergency_stop(
        operator_id='operator-1',
        reason='Test emergency'
    )
    
    assert override_id is not None


# Helper functions
def create_test_junction_with_conflict() -> JunctionSignals:
    """Create junction with signal conflict"""
    now = time.time()
    
    return JunctionSignals(
        north=SignalState(
            current=SignalColor.GREEN,
            duration=30.0,
            last_change=now,
            time_since_green=0.0
        ),
        east=SignalState(
            current=SignalColor.GREEN,  # Conflict!
            duration=30.0,
            last_change=now,
            time_since_green=0.0
        ),
        south=SignalState(
            current=SignalColor.RED,
            duration=30.0,
            last_change=now,
            time_since_green=30.0
        ),
        west=SignalState(
            current=SignalColor.RED,
            duration=30.0,
            last_change=now,
            time_since_green=30.0
        )
    )


def create_test_junction_valid() -> JunctionSignals:
    """Create junction with valid signals"""
    return create_default_signals('north')


def create_test_junction_north_green() -> JunctionSignals:
    """Create junction with North GREEN"""
    return create_default_signals('north')

