"""
Training Monitoring Module

Comprehensive training monitoring with TensorBoard, custom metrics logging,
and real-time training progress tracking.
Implements FRD-04 FR-04.7: Training monitoring.

Features:
- TensorBoard integration
- Episode metrics logging
- Reward component breakdown
- Training statistics
"""

import os
import time
import numpy as np
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

try:
    from torch.utils.tensorboard import SummaryWriter
    TENSORBOARD_AVAILABLE = True
except ImportError:
    TENSORBOARD_AVAILABLE = False
    print("[WARN] TensorBoard not available")

try:
    from stable_baselines3.common.callbacks import BaseCallback
    SB3_AVAILABLE = True
except ImportError:
    SB3_AVAILABLE = False


@dataclass
class EpisodeMetrics:
    """Metrics for a single episode"""
    episode_number: int
    total_reward: float
    episode_length: int
    avg_density: float = 0.0
    total_vehicles: int = 0
    congestion_points: int = 0
    duration_seconds: float = 0.0
    timestamp: float = field(default_factory=time.time)


class TrainingMonitor:
    """
    Monitor RL training progress
    
    Logs metrics to TensorBoard and console for real-time
    monitoring of training progress.
    
    Usage:
        monitor = TrainingMonitor('./logs/tensorboard/')
        monitor.log_episode(reward, length, info)
        monitor.log_step(reward, action, obs)
        summary = monitor.get_summary()
    """
    
    def __init__(self, log_dir: str = './logs/tensorboard/'):
        """
        Initialize training monitor
        
        Args:
            log_dir: TensorBoard log directory
        """
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        
        # TensorBoard writer
        self.writer = None
        if TENSORBOARD_AVAILABLE:
            self.writer = SummaryWriter(log_dir=log_dir)
            print(f"[MONITOR] Training monitor initialized")
            print(f"   TensorBoard: {log_dir}")
            print(f"   Run: tensorboard --logdir {log_dir}")
        else:
            print("[WARN] TensorBoard not available, logging to console only")
        
        # Episode tracking
        self.episode_count = 0
        self.step_count = 0
        
        # Metrics history
        self.episode_rewards: List[float] = []
        self.episode_lengths: List[int] = []
        self.avg_densities: List[float] = []
        self.episode_metrics: List[EpisodeMetrics] = []
        
        # Running statistics
        self.running_reward = 0.0
        self.best_episode_reward = float('-inf')
        self.worst_episode_reward = float('inf')
        
        # Training start time
        self.start_time = time.time()
    
    def log_episode(self, 
                    episode_reward: float,
                    episode_length: int,
                    info: dict = None):
        """
        Log completed episode
        
        Args:
            episode_reward: Total episode reward
            episode_length: Number of steps
            info: Additional episode information
        """
        info = info or {}
        self.episode_count += 1
        self.step_count += episode_length
        
        # Track history
        self.episode_rewards.append(episode_reward)
        self.episode_lengths.append(episode_length)
        
        # Update running statistics
        self.running_reward = 0.99 * self.running_reward + 0.01 * episode_reward
        self.best_episode_reward = max(self.best_episode_reward, episode_reward)
        self.worst_episode_reward = min(self.worst_episode_reward, episode_reward)
        
        # Create episode metrics
        metrics = EpisodeMetrics(
            episode_number=self.episode_count,
            total_reward=episode_reward,
            episode_length=episode_length,
            avg_density=info.get('avg_density', 0.0),
            total_vehicles=info.get('total_vehicles', 0),
            congestion_points=info.get('congestion_points', 0),
            duration_seconds=info.get('episode_duration', 0.0)
        )
        self.episode_metrics.append(metrics)
        
        # Log to TensorBoard
        if self.writer:
            self.writer.add_scalar('Episode/Reward', episode_reward, self.episode_count)
            self.writer.add_scalar('Episode/Length', episode_length, self.episode_count)
            self.writer.add_scalar('Episode/RunningReward', self.running_reward, self.episode_count)
            
            if 'avg_density' in info:
                self.writer.add_scalar('Metrics/AvgDensity', info['avg_density'], self.episode_count)
                self.avg_densities.append(info['avg_density'])
            
            if 'total_vehicles' in info:
                self.writer.add_scalar('Metrics/TotalVehicles', info['total_vehicles'], self.episode_count)
            
            if 'congestion_points' in info:
                self.writer.add_scalar('Metrics/CongestionPoints', info['congestion_points'], self.episode_count)
        
        # Console output (every 10 episodes)
        if self.episode_count % 10 == 0:
            avg_reward = np.mean(self.episode_rewards[-10:])
            avg_length = np.mean(self.episode_lengths[-10:])
            
            print(f"[EPISODE] Episode {self.episode_count}: "
                  f"Reward={episode_reward:.1f} (avg={avg_reward:.1f}), "
                  f"Length={episode_length} (avg={avg_length:.0f})")
    
    def log_step(self, 
                 reward: float,
                 action: np.ndarray,
                 observation: np.ndarray):
        """
        Log individual step
        
        Args:
            reward: Step reward
            action: Action taken
            observation: State observation
        """
        if self.writer:
            # Log reward
            self.writer.add_scalar('Step/Reward', reward, self.step_count)
            
            # Log action distribution (for MultiDiscrete)
            if hasattr(action, '__len__'):
                action_counts = np.bincount(action.flatten().astype(int), minlength=4)
                for i, count in enumerate(action_counts):
                    self.writer.add_scalar(f'Action/Direction_{i}', count, self.step_count)
    
    def log_reward_breakdown(self, 
                            breakdown: dict,
                            step: int = None):
        """
        Log detailed reward breakdown
        
        Args:
            breakdown: Dict of reward components
            step: Current step (defaults to self.step_count)
        """
        if step is None:
            step = self.step_count
        
        if self.writer:
            for component, value in breakdown.items():
                self.writer.add_scalar(f'Reward/{component}', value, step)
    
    def log_training_metrics(self, 
                            loss: float,
                            policy_loss: float = None,
                            value_loss: float = None,
                            entropy_loss: float = None,
                            step: int = None):
        """
        Log PPO training metrics
        
        Args:
            loss: Total loss
            policy_loss: Policy loss
            value_loss: Value function loss
            entropy_loss: Entropy loss
            step: Training step
        """
        if step is None:
            step = self.step_count
        
        if self.writer:
            self.writer.add_scalar('Training/Loss', loss, step)
            if policy_loss is not None:
                self.writer.add_scalar('Training/PolicyLoss', policy_loss, step)
            if value_loss is not None:
                self.writer.add_scalar('Training/ValueLoss', value_loss, step)
            if entropy_loss is not None:
                self.writer.add_scalar('Training/EntropyLoss', entropy_loss, step)
    
    def log_custom_scalar(self, tag: str, value: float, step: int = None):
        """Log custom scalar value"""
        if step is None:
            step = self.step_count
        
        if self.writer:
            self.writer.add_scalar(tag, value, step)
    
    def get_summary(self) -> dict:
        """Get training summary statistics"""
        if not self.episode_rewards:
            return {
                'episodeCount': 0,
                'totalSteps': 0,
                'avgReward': 0.0,
                'maxReward': 0.0,
                'minReward': 0.0,
                'runningReward': 0.0,
                'avgEpisodeLength': 0.0,
                'avgDensity': 0.0,
                'trainingDuration': time.time() - self.start_time
            }
        
        return {
            'episodeCount': self.episode_count,
            'totalSteps': self.step_count,
            'avgReward': float(np.mean(self.episode_rewards)),
            'maxReward': float(self.best_episode_reward),
            'minReward': float(self.worst_episode_reward),
            'runningReward': float(self.running_reward),
            'avgEpisodeLength': float(np.mean(self.episode_lengths)),
            'avgDensity': float(np.mean(self.avg_densities)) if self.avg_densities else 0.0,
            'trainingDuration': time.time() - self.start_time,
            'recentRewards': self.episode_rewards[-10:] if len(self.episode_rewards) >= 10 else self.episode_rewards
        }
    
    def get_recent_episodes(self, n: int = 10) -> List[EpisodeMetrics]:
        """Get metrics for last N episodes"""
        return self.episode_metrics[-n:]
    
    def flush(self):
        """Flush TensorBoard writer"""
        if self.writer:
            self.writer.flush()
    
    def close(self):
        """Close TensorBoard writer"""
        if self.writer:
            self.writer.close()
        print("[MONITOR] Training monitor closed")


# ============================================
# Custom Callbacks for Stable-Baselines3
# ============================================

if SB3_AVAILABLE:
    class DetailedLoggingCallback(BaseCallback):
        """
        Custom callback for detailed training logging
        
        Integrates with TrainingMonitor for comprehensive logging.
        """
        
        def __init__(self, 
                    monitor: TrainingMonitor = None, 
                    log_interval: int = 1000,
                    verbose: int = 0):
            super().__init__(verbose)
            self.monitor = monitor or TrainingMonitor()
            self.log_interval = log_interval
            
            # Track episode data
            self._episode_rewards = []
            self._episode_lengths = []
        
        def _on_step(self) -> bool:
            """Called after each step"""
            # Log step metrics periodically
            if self.n_calls % self.log_interval == 0:
                if len(self.locals.get('rewards', [])) > 0:
                    reward = self.locals['rewards'][0]
                    action = self.locals.get('actions', np.array([0]))
                    obs = self.locals.get('new_obs', np.array([]))
                    
                    self.monitor.log_step(reward, action, obs)
            
            return True
        
        def _on_rollout_end(self) -> None:
            """Called at end of rollout"""
            # Check for episode completion
            if 'episode_lengths' in self.locals:
                for i, (length, reward) in enumerate(zip(
                    self.locals.get('episode_lengths', []),
                    self.locals.get('episode_rewards', [])
                )):
                    if length is not None and reward is not None:
                        info = self.locals.get('infos', [{}])[i] if i < len(self.locals.get('infos', [])) else {}
                        self.monitor.log_episode(reward, length, info)
        
        def _on_training_end(self) -> None:
            """Called at end of training"""
            self.monitor.flush()
            summary = self.monitor.get_summary()
            print(f"\n[SUMMARY] Training Summary:")
            print(f"   Episodes: {summary['episodeCount']}")
            print(f"   Total Steps: {summary['totalSteps']}")
            print(f"   Avg Reward: {summary['avgReward']:.2f}")
            print(f"   Max Reward: {summary['maxReward']:.2f}")
            print(f"   Duration: {summary['trainingDuration']/60:.1f} minutes")

    
    class EarlyStoppingCallback(BaseCallback):
        """
        Early stopping callback based on reward improvement
        """
        
        def __init__(self, 
                    patience: int = 5,
                    min_improvement: float = 0.01,
                    eval_freq: int = 10000,
                    verbose: int = 0):
            super().__init__(verbose)
            self.patience = patience
            self.min_improvement = min_improvement
            self.eval_freq = eval_freq
            
            self.best_mean_reward = float('-inf')
            self.no_improvement_count = 0
        
        def _on_step(self) -> bool:
            if self.n_calls % self.eval_freq == 0:
                # Get recent episode rewards
                if 'episode_rewards' in self.locals:
                    recent_rewards = self.locals['episode_rewards'][-100:]
                    if len(recent_rewards) > 0:
                        mean_reward = np.mean(recent_rewards)
                        
                        improvement = (mean_reward - self.best_mean_reward) / abs(self.best_mean_reward + 1e-8)
                        
                        if improvement > self.min_improvement:
                            self.best_mean_reward = mean_reward
                            self.no_improvement_count = 0
                            if self.verbose:
                                print(f"[BEST] New best reward: {mean_reward:.2f}")
                        else:
                            self.no_improvement_count += 1
                            if self.verbose:
                                print(f"[PAUSE] No improvement ({self.no_improvement_count}/{self.patience})")
                        
                        if self.no_improvement_count >= self.patience:
                            if self.verbose:
                                print(f"[STOP] Early stopping triggered")
                            return False
            
            return True

