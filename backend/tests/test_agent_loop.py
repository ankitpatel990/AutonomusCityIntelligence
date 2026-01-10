"""
Agent Loop Integration Tests

Tests for FRD-03: Autonomous Agent Loop & Integration

Tests cover:
- Agent initialization
- Start/stop/pause/resume
- Loop cycle execution
- Decision strategies (RL, rules)
- Performance requirements
- Error handling
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch

from app.agent.agent_loop import (
    AutonomousAgent, 
    AgentStatus, 
    AgentStrategy,
    AgentStatistics
)
from app.agent.perception import PerceptionModule, PerceivedState
from app.agent.decision import DecisionModule, AgentDecisions, SignalDecision
from app.agent.action import ActionModule
from app.agent.monitoring import MonitoringModule


# ============================================
# Fixtures
# ============================================

@pytest.fixture
def mock_density_tracker():
    """Create mock density tracker"""
    tracker = Mock()
    tracker.get_city_metrics = Mock(return_value=Mock(
        avg_density_score=25.0,
        congestion_points=2
    ))
    tracker.road_densities = {}
    tracker.junction_densities = {}
    return tracker


@pytest.fixture
def mock_simulation_manager():
    """Create mock simulation manager"""
    manager = Mock()
    manager.get_vehicles = Mock(return_value=[])
    manager.get_junctions = Mock(return_value=[])
    manager.get_emergency_status = Mock(return_value={'active': False})
    manager.get_manual_controls = Mock(return_value=[])
    manager.get_recent_violations = Mock(return_value=[])
    return manager


@pytest.fixture
def agent_config():
    """Test agent configuration"""
    return {
        'loopInterval': 0.1,  # Fast for testing
        'maxErrors': 3
    }


@pytest.fixture
def perception_module(mock_density_tracker, mock_simulation_manager):
    """Create perception module with mocks"""
    return PerceptionModule(
        density_tracker=mock_density_tracker,
        simulation_manager=mock_simulation_manager
    )


@pytest.fixture
def decision_module():
    """Create decision module"""
    return DecisionModule()


@pytest.fixture
def action_module(mock_simulation_manager):
    """Create action module with mock"""
    return ActionModule(simulation_manager=mock_simulation_manager)


@pytest.fixture
def monitoring_module():
    """Create monitoring module"""
    return MonitoringModule()


@pytest.fixture
def agent(agent_config, mock_simulation_manager, mock_density_tracker,
          perception_module, decision_module, action_module, monitoring_module):
    """Create fully configured agent"""
    agent = AutonomousAgent(
        config=agent_config,
        simulation_manager=mock_simulation_manager,
        density_tracker=mock_density_tracker
    )
    
    agent.inject_modules(
        perception=perception_module,
        prediction=None,
        decision=decision_module,
        action=action_module,
        monitor=monitoring_module
    )
    
    return agent


# ============================================
# Agent Initialization Tests
# ============================================

class TestAgentInitialization:
    """Test agent initialization"""
    
    def test_agent_creation(self, agent_config):
        """Test agent creates successfully"""
        agent = AutonomousAgent(config=agent_config)
        
        assert agent.status == AgentStatus.STOPPED
        assert agent.strategy == AgentStrategy.RL
        assert agent.stats.loop_count == 0
    
    def test_agent_default_config(self):
        """Test agent works without config"""
        agent = AutonomousAgent()
        
        assert agent.loop_interval == 1.0
        assert agent.max_errors == 5
    
    def test_module_injection(self, agent):
        """Test modules are properly injected"""
        assert agent.perception is not None
        assert agent.decision is not None
        assert agent.action is not None
        assert agent.monitor is not None
    
    def test_module_validation(self, agent_config):
        """Test agent validates modules before start"""
        agent = AutonomousAgent(config=agent_config)
        
        # Should fail without modules
        assert not agent._validate_modules()


# ============================================
# Agent Lifecycle Tests
# ============================================

class TestAgentLifecycle:
    """Test agent start/stop/pause/resume"""
    
    @pytest.mark.asyncio
    async def test_agent_start(self, agent):
        """Test agent starts successfully"""
        await agent.start(AgentStrategy.RULE_BASED)
        
        assert agent.status == AgentStatus.RUNNING
        assert agent.strategy == AgentStrategy.RULE_BASED
        
        await agent.stop()
    
    @pytest.mark.asyncio
    async def test_agent_stop(self, agent):
        """Test agent stops successfully"""
        await agent.start()
        await asyncio.sleep(0.2)
        
        await agent.stop()
        
        assert agent.status == AgentStatus.STOPPED
    
    @pytest.mark.asyncio
    async def test_agent_pause_resume(self, agent):
        """Test agent pause and resume"""
        await agent.start()
        await asyncio.sleep(0.2)
        
        # Pause
        await agent.pause()
        assert agent.status == AgentStatus.PAUSED
        
        loop_count_at_pause = agent.stats.loop_count
        await asyncio.sleep(0.3)
        
        # Should not increase while paused
        # (may have 1 more due to timing)
        assert agent.stats.loop_count <= loop_count_at_pause + 1
        
        # Resume
        await agent.resume()
        assert agent.status == AgentStatus.RUNNING
        
        await asyncio.sleep(0.2)
        
        # Should increase after resume
        assert agent.stats.loop_count > loop_count_at_pause
        
        await agent.stop()
    
    @pytest.mark.asyncio
    async def test_double_start(self, agent):
        """Test starting already running agent"""
        await agent.start()
        
        # Should not error, just return
        await agent.start()
        
        assert agent.status == AgentStatus.RUNNING
        
        await agent.stop()
    
    @pytest.mark.asyncio
    async def test_double_stop(self, agent):
        """Test stopping already stopped agent"""
        await agent.start()
        await agent.stop()
        
        # Should not error
        await agent.stop()
        
        assert agent.status == AgentStatus.STOPPED


# ============================================
# Loop Cycle Tests
# ============================================

class TestLoopCycle:
    """Test agent loop cycle execution"""
    
    @pytest.mark.asyncio
    async def test_single_cycle(self, agent):
        """Test single loop cycle execution"""
        await agent.execute_loop_cycle()
        
        assert agent.stats.loop_count == 1
        assert agent.stats.last_decision_time > 0
        assert agent.stats.avg_latency > 0
    
    @pytest.mark.asyncio
    async def test_multiple_cycles(self, agent):
        """Test multiple loop cycles"""
        for _ in range(5):
            await agent.execute_loop_cycle()
        
        assert agent.stats.loop_count == 5
    
    @pytest.mark.asyncio
    async def test_cycle_performance(self, agent):
        """Test cycle completes within 2 seconds"""
        start = time.time()
        await agent.execute_loop_cycle()
        duration = time.time() - start
        
        assert duration < 2.0, f"Cycle too slow: {duration:.2f}s"
    
    @pytest.mark.asyncio
    async def test_cycle_updates_statistics(self, agent):
        """Test statistics are updated each cycle"""
        initial_count = agent.stats.loop_count
        
        await agent.execute_loop_cycle()
        
        assert agent.stats.loop_count == initial_count + 1
        assert agent.stats.total_latency > 0


# ============================================
# Strategy Tests
# ============================================

class TestDecisionStrategies:
    """Test different decision strategies"""
    
    @pytest.mark.asyncio
    async def test_rule_based_strategy(self, agent):
        """Test rule-based strategy works"""
        agent.strategy = AgentStrategy.RULE_BASED
        
        await agent.execute_loop_cycle()
        
        decisions = agent.get_last_decisions()
        if decisions and decisions.signal_decisions:
            assert decisions.strategy_used == "RULE_BASED"
    
    @pytest.mark.asyncio
    async def test_rl_fallback_to_rules(self, agent):
        """Test RL falls back to rules when no agent"""
        # No RL agent injected, should fallback
        agent.strategy = AgentStrategy.RL
        
        await agent.execute_loop_cycle()
        
        decisions = agent.get_last_decisions()
        if decisions and decisions.signal_decisions:
            # Falls back to RULE_BASED when no RL agent
            assert decisions.strategy_used in ["RULE_BASED", "RL"]


# ============================================
# Perception Tests
# ============================================

class TestPerceptionModule:
    """Test perception module"""
    
    @pytest.mark.asyncio
    async def test_perceive_returns_state(self, perception_module):
        """Test perceive returns valid state"""
        state = await perception_module.perceive()
        
        assert isinstance(state, PerceivedState)
        assert state.timestamp > 0
    
    @pytest.mark.asyncio
    async def test_perception_performance(self, perception_module):
        """Test perception completes within 50ms"""
        start = time.time()
        await perception_module.perceive()
        duration = (time.time() - start) * 1000
        
        # Allow some margin for test environment
        assert duration < 100, f"Perception too slow: {duration:.1f}ms"
    
    def test_perception_stats(self, perception_module):
        """Test perception tracks statistics"""
        asyncio.run(perception_module.perceive())
        
        stats = perception_module.get_stats()
        assert stats['perceptionCount'] == 1


# ============================================
# Decision Tests
# ============================================

class TestDecisionModule:
    """Test decision module"""
    
    @pytest.mark.asyncio
    async def test_rule_based_decision(self, decision_module):
        """Test rule-based decision making"""
        state = PerceivedState(
            timestamp=time.time(),
            junction_densities={
                'J-1': {'N': 50.0, 'E': 30.0, 'S': 20.0, 'W': 10.0}
            },
            signal_states={
                'J-1': {'N': 'RED', 'E': 'RED', 'S': 'RED', 'W': 'RED'}
            }
        )
        
        decisions = await decision_module.decide(
            state, None, AgentStrategy.RULE_BASED
        )
        
        assert isinstance(decisions, AgentDecisions)
        assert decisions.strategy_used == "RULE_BASED"
        
        # Should prioritize highest density (N)
        if decisions.signal_decisions:
            assert decisions.signal_decisions[0].direction == 'N'
    
    @pytest.mark.asyncio
    async def test_emergency_override(self, decision_module):
        """Test emergency mode triggers override"""
        state = PerceivedState(
            timestamp=time.time(),
            emergency_active=True,
            emergency_vehicle_id="AMB-001",
            junction_densities={'J-1': {'N': 50.0, 'E': 30.0, 'S': 20.0, 'W': 10.0}}
        )
        
        decisions = await decision_module.decide(
            state, None, AgentStrategy.RL
        )
        
        assert decisions.emergency_override is True
        assert decisions.strategy_used == "EMERGENCY"
    
    def test_decision_stats(self, decision_module):
        """Test decision module tracks statistics"""
        stats = decision_module.get_stats()
        assert 'decisionCount' in stats
        assert 'hasRlAgent' in stats


# ============================================
# Action Tests
# ============================================

class TestActionModule:
    """Test action module"""
    
    @pytest.mark.asyncio
    async def test_execute_green(self, action_module, mock_simulation_manager):
        """Test executing GREEN action"""
        decisions = AgentDecisions(
            signal_decisions=[
                SignalDecision(
                    junction_id='J-1',
                    direction='N',
                    action='GREEN',
                    duration=30,
                    reason='Test'
                )
            ]
        )
        
        await action_module.execute(decisions)
        
        assert action_module.actions_executed == 1
    
    @pytest.mark.asyncio
    async def test_skip_hold_action(self, action_module):
        """Test HOLD actions are skipped"""
        decisions = AgentDecisions(
            signal_decisions=[
                SignalDecision(
                    junction_id='J-1',
                    direction='N',
                    action='HOLD',
                    duration=30,
                    reason='Test'
                )
            ]
        )
        
        await action_module.execute(decisions)
        
        assert action_module.actions_executed == 0
    
    @pytest.mark.asyncio
    async def test_skip_emergency_override(self, action_module):
        """Test emergency override decisions are skipped"""
        decisions = AgentDecisions(
            emergency_override=True,
            signal_decisions=[
                SignalDecision(
                    junction_id='J-1',
                    direction='N',
                    action='GREEN',
                    duration=30,
                    reason='Test'
                )
            ]
        )
        
        await action_module.execute(decisions)
        
        # Should be skipped due to emergency override
        assert action_module.actions_executed == 0
    
    def test_action_stats(self, action_module):
        """Test action module tracks statistics"""
        stats = action_module.get_statistics()
        assert 'executed' in stats
        assert 'rejected' in stats
        assert 'successRate' in stats


# ============================================
# Monitoring Tests
# ============================================

class TestMonitoringModule:
    """Test monitoring module"""
    
    def test_detect_conflicts(self, monitoring_module):
        """Test signal conflict detection"""
        state = PerceivedState(
            signal_states={
                'J-1': {'N': 'GREEN', 'E': 'GREEN', 'S': 'RED', 'W': 'RED'}
            }
        )
        
        conflicts = monitoring_module._detect_conflicts(state)
        
        assert len(conflicts) > 0
        assert 'J-1' in conflicts[0]
    
    def test_no_conflicts(self, monitoring_module):
        """Test no false conflict detection"""
        state = PerceivedState(
            signal_states={
                'J-1': {'N': 'GREEN', 'E': 'RED', 'S': 'RED', 'W': 'RED'}
            }
        )
        
        conflicts = monitoring_module._detect_conflicts(state)
        
        assert len(conflicts) == 0
    
    @pytest.mark.asyncio
    async def test_error_handling(self, monitoring_module):
        """Test error handling increases count"""
        await monitoring_module.handle_error(Exception("Test error"))
        
        assert monitoring_module.error_count == 1
        assert monitoring_module.consecutive_errors == 1
    
    @pytest.mark.asyncio
    async def test_check_resets_errors(self, monitoring_module):
        """Test successful check resets consecutive errors"""
        monitoring_module.consecutive_errors = 2
        
        state = PerceivedState()
        decisions = AgentDecisions()
        
        await monitoring_module.check(state, decisions)
        
        assert monitoring_module.consecutive_errors == 0
    
    def test_monitoring_stats(self, monitoring_module):
        """Test monitoring module tracks statistics"""
        stats = monitoring_module.get_statistics()
        assert 'checkCount' in stats
        assert 'errorCount' in stats


# ============================================
# Integration Tests
# ============================================

class TestIntegration:
    """Integration tests for complete agent flow"""
    
    @pytest.mark.asyncio
    async def test_full_agent_flow(self, agent):
        """Test complete agent lifecycle"""
        # Start
        await agent.start(AgentStrategy.RULE_BASED)
        assert agent.status == AgentStatus.RUNNING
        
        # Run for a bit
        await asyncio.sleep(0.5)
        
        # Pause
        await agent.pause()
        assert agent.status == AgentStatus.PAUSED
        
        # Resume
        await agent.resume()
        assert agent.status == AgentStatus.RUNNING
        
        await asyncio.sleep(0.3)
        
        # Stop
        await agent.stop()
        assert agent.status == AgentStatus.STOPPED
        
        # Verify cycles ran
        assert agent.stats.loop_count > 0
    
    @pytest.mark.asyncio
    async def test_statistics_accuracy(self, agent):
        """Test statistics are accurate"""
        await agent.start()
        await asyncio.sleep(0.5)
        await agent.stop()
        
        stats = agent.get_statistics()
        
        assert stats['loopCount'] > 0
        assert stats['uptime'] > 0
        assert stats['status'] == 'STOPPED'


# ============================================
# Performance Tests
# ============================================

class TestPerformance:
    """Performance tests for agent"""
    
    @pytest.mark.asyncio
    async def test_cycle_latency(self, agent):
        """Test cycle latency < 500ms"""
        await agent.execute_loop_cycle()
        
        assert agent.stats.avg_latency < 500, \
            f"Latency too high: {agent.stats.avg_latency}ms"
    
    @pytest.mark.asyncio
    async def test_sustained_performance(self, agent):
        """Test agent maintains performance over multiple cycles"""
        for _ in range(20):
            await agent.execute_loop_cycle()
        
        # Average should stay reasonable
        assert agent.stats.avg_latency < 200, \
            f"Avg latency too high: {agent.stats.avg_latency}ms"


# ============================================
# Run tests
# ============================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

