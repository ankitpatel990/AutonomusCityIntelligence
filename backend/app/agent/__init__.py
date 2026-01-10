"""
Autonomous Agent Loop and Decision Making

This module implements FRD-03: Autonomous Agent Loop & Integration.

Components:
- AutonomousAgent: Main agent orchestrating the system
- PerceptionModule: State reading (FRD-03.2)
- DecisionModule: Multi-strategy decisions (FRD-03.3)
- ActionModule: Signal control execution (FRD-03.4)
- MonitoringModule: Health checks (FRD-03.5)

The agent executes a continuous loop:
1. PERCEIVE - Read current state from density tracker, simulation
2. PREDICT - Run congestion prediction (optional, FRD-06)
3. DECIDE - Determine signal actions using RL/rules/manual
4. ACT - Execute actions with safety validation (FRD-05)
5. MONITOR - Check health and trigger fail-safe if needed

Usage:
    from app.agent import get_agent, init_agent, AgentStrategy
    
    # Initialize agent
    agent = init_agent(config, simulation_manager, density_tracker)
    
    # Inject modules
    agent.inject_modules(perception, prediction, decision, action, monitor)
    
    # Start agent loop
    await agent.start(AgentStrategy.RL)
    
    # Later...
    await agent.stop()
"""

# Core agent loop and enums
from app.agent.agent_loop import (
    AutonomousAgent,
    AgentStatus,
    AgentStrategy,
    AgentStatistics,
    get_agent,
    init_agent,
    set_agent,
    cleanup_old_logs
)

# Perception module
from app.agent.perception import (
    PerceptionModule,
    PerceivedState
)

# Decision module
from app.agent.decision import (
    DecisionModule,
    SignalDecision,
    AgentDecisions,
    RuleBasedEngine
)

# Action module
from app.agent.action import (
    ActionModule
)

# Monitoring module
from app.agent.monitoring import (
    MonitoringModule,
    HealthChecker
)


__all__ = [
    # Core classes
    'AutonomousAgent',
    'AgentStatus',
    'AgentStrategy',
    'AgentStatistics',
    
    # Modules
    'PerceptionModule',
    'PerceivedState',
    'DecisionModule',
    'SignalDecision',
    'AgentDecisions',
    'RuleBasedEngine',
    'ActionModule',
    'MonitoringModule',
    'HealthChecker',
    
    # Factory functions
    'get_agent',
    'init_agent',
    'set_agent',
    'cleanup_old_logs'
]
