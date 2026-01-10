"""
Reinforcement Learning Module

PPO agent and training for traffic signal optimization.
Implements FRD-04: RL-Powered Signal Orchestration.

Components:
- TrafficSignalEnv: OpenAI Gym environment for traffic control
- PPO Agent: Proximal Policy Optimization using Stable-Baselines3
- RLInferenceService: Fast model inference for real-time decisions
- RewardCalculator: Configurable reward function
- TrainingMonitor: TensorBoard and metrics logging

Usage:
    # Training
    from app.rl.training import train_rl_agent
    agent = train_rl_agent(density_tracker, total_timesteps=100000)
    
    # Inference
    from app.rl.inference import get_inference_service
    service = get_inference_service()
    actions, _ = service.predict(observation)
"""

from app.rl.traffic_env import TrafficSignalEnv, TrafficSignalEnvWrapper
from app.rl.rewards import RewardCalculator, RewardWeights, RewardBreakdown
from app.rl.inference import (
    RLInferenceService,
    get_inference_service,
    set_inference_service,
    init_inference_service
)
from app.rl.training import (
    train_rl_agent,
    continue_training,
    evaluate_agent,
    compare_strategies
)
from app.rl.monitoring import TrainingMonitor

# Conditional imports for SB3 components
try:
    from app.rl.ppo_config import (
        PPO_CONFIG,
        TRAINING_CONFIG,
        create_ppo_agent,
        create_callbacks,
        get_device,
        ProgressCallback
    )
    from app.rl.monitoring import DetailedLoggingCallback, EarlyStoppingCallback
    SB3_AVAILABLE = True
except ImportError:
    SB3_AVAILABLE = False


__all__ = [
    # Environment
    'TrafficSignalEnv',
    'TrafficSignalEnvWrapper',
    
    # Rewards
    'RewardCalculator',
    'RewardWeights',
    'RewardBreakdown',
    
    # Inference
    'RLInferenceService',
    'get_inference_service',
    'set_inference_service',
    'init_inference_service',
    
    # Training
    'train_rl_agent',
    'continue_training',
    'evaluate_agent',
    'compare_strategies',
    
    # Monitoring
    'TrainingMonitor',
    
    # Config (if SB3 available)
    'PPO_CONFIG',
    'TRAINING_CONFIG',
    'create_ppo_agent',
    'create_callbacks',
    'get_device',
    
    # Callbacks
    'ProgressCallback',
    'DetailedLoggingCallback',
    'EarlyStoppingCallback',
    
    # Status
    'SB3_AVAILABLE',
]
