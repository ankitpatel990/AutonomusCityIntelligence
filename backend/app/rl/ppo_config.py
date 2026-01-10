"""
PPO Agent Configuration

Configure PPO agent using Stable-Baselines3 with hyperparameters 
tuned for traffic signal control.
Implements FRD-04 FR-04.2: PPO agent configuration.

PPO Hyperparameters tuned for:
- Multi-agent coordination (9 junctions)
- Real-time decision making
- Stable learning with exploration
"""

import os
import torch
from typing import Optional, Dict, Any, List

try:
    from stable_baselines3 import PPO
    from stable_baselines3.common.callbacks import CheckpointCallback, EvalCallback, BaseCallback
    from stable_baselines3.common.vec_env import DummyVecEnv, SubprocVecEnv
    from stable_baselines3.common.monitor import Monitor
    SB3_AVAILABLE = True
except ImportError:
    SB3_AVAILABLE = False
    print("[WARN] stable-baselines3 not installed. RL training unavailable.")


# ============================================
# PPO Hyperparameters
# ============================================

PPO_CONFIG = {
    # Learning rate
    'learning_rate': 3e-4,  # Standard for PPO
    
    # Training batch size
    'n_steps': 2048,  # Number of steps per update
    'batch_size': 64,  # Minibatch size
    
    # Epochs
    'n_epochs': 10,  # Number of epochs per update
    
    # Discount factor
    'gamma': 0.99,  # Future reward discount
    
    # GAE parameter
    'gae_lambda': 0.95,  # Generalized Advantage Estimation
    
    # Clipping
    'clip_range': 0.2,  # PPO clipping parameter
    
    # Value function coefficient
    'vf_coef': 0.5,
    
    # Entropy coefficient (exploration)
    'ent_coef': 0.01,  # Encourage exploration
    
    # Max gradient norm
    'max_grad_norm': 0.5,
    
    # Network architecture
    'policy_kwargs': {
        'net_arch': dict(pi=[256, 128], vf=[256, 128]),  # Policy and value networks
        'activation_fn': torch.nn.ReLU
    },
    
    # Misc
    'verbose': 1,
    'tensorboard_log': './logs/tensorboard/',
    'device': 'auto'  # Use GPU if available
}


# ============================================
# Training Configuration
# ============================================

TRAINING_CONFIG = {
    # Total timesteps to train
    'total_timesteps': 1_000_000,  # 1M steps (~1-2 hours)
    
    # For quick testing
    'quick_train_timesteps': 10_000,  # 10k steps (~5 minutes)
    
    # Evaluation frequency
    'eval_freq': 10_000,  # Evaluate every 10k steps
    'n_eval_episodes': 5,  # Episodes per evaluation
    
    # Checkpointing
    'checkpoint_freq': 50_000,  # Save every 50k steps
    'checkpoint_dir': './models/checkpoints/',
    
    # Best model saving
    'save_best_model': True,
    'best_model_dir': './models/best/',
    
    # Final model
    'final_model_path': './models/ppo_traffic_final.zip',
    
    # Early stopping
    'early_stopping_patience': 5,  # Stop if no improvement for 5 evals
    'early_stopping_threshold': 0.01  # Minimum improvement threshold
}


def create_ppo_agent(env, config: dict = None) -> Optional['PPO']:
    """
    Create PPO agent with configuration
    
    Args:
        env: TrafficSignalEnv instance (or gym env)
        config: Custom configuration (overrides defaults)
    
    Returns:
        PPO agent instance or None if SB3 not available
    """
    if not SB3_AVAILABLE:
        print("[ERROR] stable-baselines3 not available")
        return None
    
    # Merge configurations
    agent_config = {**PPO_CONFIG}
    if config:
        # Handle nested policy_kwargs separately
        if 'policy_kwargs' in config:
            agent_config['policy_kwargs'].update(config.pop('policy_kwargs'))
        agent_config.update(config)
    
    # Ensure directories exist
    os.makedirs(agent_config.get('tensorboard_log', './logs/tensorboard/'), exist_ok=True)
    
    # Create PPO agent
    agent = PPO(
        policy='MlpPolicy',  # Multi-layer perceptron policy
        env=env,
        learning_rate=agent_config['learning_rate'],
        n_steps=agent_config['n_steps'],
        batch_size=agent_config['batch_size'],
        n_epochs=agent_config['n_epochs'],
        gamma=agent_config['gamma'],
        gae_lambda=agent_config['gae_lambda'],
        clip_range=agent_config['clip_range'],
        vf_coef=agent_config['vf_coef'],
        ent_coef=agent_config['ent_coef'],
        max_grad_norm=agent_config['max_grad_norm'],
        policy_kwargs=agent_config['policy_kwargs'],
        verbose=agent_config['verbose'],
        tensorboard_log=agent_config['tensorboard_log'],
        device=agent_config['device']
    )
    
    print("[OK] PPO Agent created")
    print(f"   Learning rate: {agent_config['learning_rate']}")
    print(f"   Network: {agent_config['policy_kwargs']['net_arch']}")
    print(f"   Device: {agent.device}")
    
    return agent


def create_callbacks(config: dict = None, eval_env = None) -> List['BaseCallback']:
    """
    Create training callbacks
    
    Args:
        config: Training configuration
        eval_env: Optional evaluation environment
    
    Returns:
        List of callbacks
    """
    if not SB3_AVAILABLE:
        return []
    
    train_config = {**TRAINING_CONFIG}
    if config:
        train_config.update(config)
    
    callbacks = []
    
    # Ensure directories exist
    os.makedirs(train_config['checkpoint_dir'], exist_ok=True)
    os.makedirs(train_config['best_model_dir'], exist_ok=True)
    
    # Checkpoint callback - save model periodically
    checkpoint_callback = CheckpointCallback(
        save_freq=train_config['checkpoint_freq'],
        save_path=train_config['checkpoint_dir'],
        name_prefix='ppo_traffic'
    )
    callbacks.append(checkpoint_callback)
    
    # Evaluation callback - evaluate and save best model
    if eval_env is not None:
        eval_callback = EvalCallback(
            eval_env,
            best_model_save_path=train_config['best_model_dir'],
            log_path='./logs/eval/',
            eval_freq=train_config['eval_freq'],
            n_eval_episodes=train_config['n_eval_episodes'],
            deterministic=True
        )
        callbacks.append(eval_callback)
    
    return callbacks


def get_device() -> str:
    """
    Get available device for training
    
    Returns:
        'cuda' if GPU available, else 'cpu'
    """
    if torch.cuda.is_available():
        device_name = torch.cuda.get_device_name(0)
        print(f"[GPU] GPU available: {device_name}")
        return 'cuda'
    else:
        print("[CPU] Using CPU for training")
        return 'cpu'


def create_vectorized_env(env_fn, n_envs: int = 1, use_subprocess: bool = False):
    """
    Create vectorized environment for parallel training
    
    Args:
        env_fn: Function that creates environment
        n_envs: Number of parallel environments
        use_subprocess: Use subprocess for true parallelism
    
    Returns:
        Vectorized environment
    """
    if not SB3_AVAILABLE:
        return None
    
    if use_subprocess and n_envs > 1:
        return SubprocVecEnv([env_fn for _ in range(n_envs)])
    else:
        return DummyVecEnv([env_fn for _ in range(n_envs)])


class ProgressCallback(BaseCallback if SB3_AVAILABLE else object):
    """
    Custom callback for training progress
    
    Logs detailed progress during training
    """
    
    def __init__(self, log_interval: int = 1000, verbose: int = 0):
        if SB3_AVAILABLE:
            super().__init__(verbose)
        self.log_interval = log_interval
        self.episode_rewards = []
        self.episode_lengths = []
    
    def _on_step(self) -> bool:
        """Called after each step"""
        if self.n_calls % self.log_interval == 0:
            # Get recent rewards
            if len(self.episode_rewards) > 0:
                recent_reward = sum(self.episode_rewards[-10:]) / min(10, len(self.episode_rewards))
                print(f"[STEP] Step {self.n_calls}: Avg Reward = {recent_reward:.2f}")
        
        # Log episode end
        if len(self.locals.get('dones', [])) > 0 and any(self.locals['dones']):
            if 'infos' in self.locals:
                for info in self.locals['infos']:
                    if 'episode' in info:
                        self.episode_rewards.append(info['episode']['r'])
                        self.episode_lengths.append(info['episode']['l'])
        
        return True
    
    def _on_training_end(self) -> None:
        """Called at end of training"""
        if len(self.episode_rewards) > 0:
            print(f"[OK] Training complete!")
            print(f"   Total episodes: {len(self.episode_rewards)}")
            print(f"   Avg reward: {sum(self.episode_rewards) / len(self.episode_rewards):.2f}")
            print(f"   Max reward: {max(self.episode_rewards):.2f}")

