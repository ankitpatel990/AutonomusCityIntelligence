"""
Reward Function Module

Advanced reward calculator for RL training with configurable weights.
Implements FRD-04 FR-04.5: Reward function design.

Reward Components:
1. Throughput - Vehicles that cleared junctions
2. Waiting time - Reduction in total waiting time
3. Density balance - Fairness across junctions
4. Congestion penalty - Penalty for congestion points
5. Average density penalty - Penalty for high overall density
6. Emergency bonus - Bonus for handling emergencies
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, Tuple, List, Any, Optional


@dataclass
class RewardWeights:
    """Configurable reward function weights"""
    throughput: float = 1.0         # Vehicles that cleared junctions
    waiting_time: float = 0.1       # Reduction in waiting time
    density_balance: float = 0.5    # Fairness across junctions
    congestion_penalty: float = 2.0  # Penalty for congestion
    avg_density_penalty: float = 0.1 # Penalty for high average density
    emergency_bonus: float = 5.0    # Bonus for handling emergency
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'throughput': self.throughput,
            'waitingTime': self.waiting_time,
            'densityBalance': self.density_balance,
            'congestionPenalty': self.congestion_penalty,
            'avgDensityPenalty': self.avg_density_penalty,
            'emergencyBonus': self.emergency_bonus
        }


@dataclass
class RewardBreakdown:
    """Detailed breakdown of reward components"""
    throughput: float = 0.0
    waiting_time: float = 0.0
    balance: float = 0.0
    congestion: float = 0.0
    avg_density: float = 0.0
    emergency: float = 0.0
    total: float = 0.0
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'throughput': round(self.throughput, 4),
            'waitingTime': round(self.waiting_time, 4),
            'balance': round(self.balance, 4),
            'congestion': round(self.congestion, 4),
            'avgDensity': round(self.avg_density, 4),
            'emergency': round(self.emergency, 4),
            'total': round(self.total, 4)
        }


class RewardCalculator:
    """
    Advanced reward calculator with detailed metrics
    
    Tracks reward components separately for analysis and debugging.
    Provides configurable weights for reward shaping.
    
    Usage:
        calc = RewardCalculator(weights=RewardWeights(throughput=1.5))
        reward, breakdown = calc.calculate_reward(current_state, junction_densities)
        summary = calc.get_episode_summary()
    """
    
    def __init__(self, weights: RewardWeights = None):
        """
        Initialize reward calculator
        
        Args:
            weights: Custom reward weights (defaults if None)
        """
        self.weights = weights or RewardWeights()
        
        # Previous state for delta calculations
        self.prev_throughput = 0
        self.prev_total_waiting = 0.0
        
        # Episode metrics
        self.episode_rewards: List[float] = []
        self.reward_components: List[RewardBreakdown] = []
        
        # Statistics
        self.total_steps = 0
    
    def calculate_reward(self, 
                        current_state: dict,
                        junction_densities: Dict[str, Any]) -> Tuple[float, dict]:
        """
        Calculate reward with detailed breakdown
        
        Args:
            current_state: Dictionary with:
                - throughput: int - vehicles that cleared
                - total_waiting_time: float - total waiting time
                - congestion_points: int - number of congestion hotspots
                - avg_density: float - average density score
                - emergency_handled: bool (optional) - emergency was handled
            junction_densities: Dict of junction density data
        
        Returns:
            reward: Total reward (float)
            breakdown: Dict of reward components
        """
        breakdown = RewardBreakdown()
        
        # Component 1: Throughput (vehicles cleared)
        throughput = current_state.get('throughput', 0)
        throughput_delta = throughput - self.prev_throughput
        breakdown.throughput = throughput_delta * self.weights.throughput
        self.prev_throughput = throughput
        
        # Component 2: Waiting time reduction
        total_waiting = current_state.get('total_waiting_time', 0.0)
        waiting_delta = self.prev_total_waiting - total_waiting  # Positive if reduced
        breakdown.waiting_time = waiting_delta * self.weights.waiting_time
        self.prev_total_waiting = total_waiting
        
        # Component 3: Density balance (fairness)
        densities = self._extract_avg_densities(junction_densities)
        if densities:
            density_std = np.std(densities)
            breakdown.balance = -density_std * self.weights.density_balance
        else:
            breakdown.balance = 0.0
        
        # Component 4: Congestion penalty
        congestion_points = current_state.get('congestion_points', 0)
        breakdown.congestion = -congestion_points * self.weights.congestion_penalty
        
        # Component 5: Average density penalty
        avg_density = current_state.get('avg_density', 0.0)
        breakdown.avg_density = -avg_density * self.weights.avg_density_penalty
        
        # Component 6: Emergency handling bonus
        if current_state.get('emergency_handled', False):
            breakdown.emergency = self.weights.emergency_bonus
        
        # Total reward
        breakdown.total = (
            breakdown.throughput +
            breakdown.waiting_time +
            breakdown.balance +
            breakdown.congestion +
            breakdown.avg_density +
            breakdown.emergency
        )
        
        # Track for analysis
        self.reward_components.append(breakdown)
        self.episode_rewards.append(breakdown.total)
        self.total_steps += 1
        
        return breakdown.total, breakdown.to_dict()
    
    def _extract_avg_densities(self, junction_densities: Dict[str, Any]) -> List[float]:
        """Extract average density values from junction data"""
        densities = []
        
        for junction_data in junction_densities.values():
            if hasattr(junction_data, 'avg_density'):
                densities.append(junction_data.avg_density)
            elif hasattr(junction_data, 'density_north'):
                # Calculate average from directional densities
                avg = (
                    junction_data.density_north +
                    junction_data.density_east +
                    junction_data.density_south +
                    junction_data.density_west
                ) / 4.0
                densities.append(avg)
            elif isinstance(junction_data, dict):
                densities.append(junction_data.get('avgDensity', 0.0))
        
        return densities
    
    def get_episode_summary(self) -> dict:
        """
        Get summary of episode rewards
        
        Returns:
            Dictionary with episode statistics and component breakdown
        """
        if not self.episode_rewards:
            return {
                'totalReward': 0.0,
                'avgReward': 0.0,
                'minReward': 0.0,
                'maxReward': 0.0,
                'steps': 0,
                'componentBreakdown': {}
            }
        
        return {
            'totalReward': sum(self.episode_rewards),
            'avgReward': float(np.mean(self.episode_rewards)),
            'minReward': float(min(self.episode_rewards)),
            'maxReward': float(max(self.episode_rewards)),
            'steps': len(self.episode_rewards),
            'componentBreakdown': self._get_component_summary()
        }
    
    def _get_component_summary(self) -> dict:
        """Get average contribution of each reward component"""
        if not self.reward_components:
            return {}
        
        # Sum each component across episode
        totals = {
            'throughput': 0.0,
            'waitingTime': 0.0,
            'balance': 0.0,
            'congestion': 0.0,
            'avgDensity': 0.0,
            'emergency': 0.0
        }
        
        for breakdown in self.reward_components:
            totals['throughput'] += breakdown.throughput
            totals['waitingTime'] += breakdown.waiting_time
            totals['balance'] += breakdown.balance
            totals['congestion'] += breakdown.congestion
            totals['avgDensity'] += breakdown.avg_density
            totals['emergency'] += breakdown.emergency
        
        return {k: round(v, 4) for k, v in totals.items()}
    
    def get_recent_rewards(self, n: int = 100) -> List[float]:
        """Get last N rewards"""
        return self.episode_rewards[-n:]
    
    def get_moving_average(self, window: int = 100) -> float:
        """Get moving average of recent rewards"""
        if len(self.episode_rewards) < window:
            return float(np.mean(self.episode_rewards)) if self.episode_rewards else 0.0
        return float(np.mean(self.episode_rewards[-window:]))
    
    def reset(self):
        """Reset for new episode"""
        self.prev_throughput = 0
        self.prev_total_waiting = 0.0
        self.episode_rewards = []
        self.reward_components = []
        self.total_steps = 0
    
    def update_weights(self, weights: RewardWeights):
        """Update reward weights"""
        self.weights = weights
    
    def get_weights(self) -> RewardWeights:
        """Get current weights"""
        return self.weights


class AdaptiveRewardCalculator(RewardCalculator):
    """
    Adaptive reward calculator that adjusts weights based on performance
    
    Automatically increases/decreases weights based on:
    - If congestion is high, increase congestion penalty
    - If throughput is low, increase throughput reward
    - If waiting times are high, increase waiting time reward
    """
    
    def __init__(self, 
                 weights: RewardWeights = None,
                 adaptation_rate: float = 0.01):
        super().__init__(weights)
        self.adaptation_rate = adaptation_rate
        self.target_avg_density = 30.0  # Target average density
        self.target_throughput = 10.0   # Target throughput per step
    
    def adapt_weights(self, current_state: dict):
        """
        Adapt weights based on current performance
        
        Args:
            current_state: Current system state
        """
        avg_density = current_state.get('avg_density', 0.0)
        throughput = current_state.get('throughput', 0)
        congestion = current_state.get('congestion_points', 0)
        
        # Increase congestion penalty if many congestion points
        if congestion > 3:
            self.weights.congestion_penalty = min(
                self.weights.congestion_penalty * (1 + self.adaptation_rate),
                10.0  # Max penalty
            )
        
        # Increase throughput reward if low throughput
        if throughput < self.target_throughput:
            self.weights.throughput = min(
                self.weights.throughput * (1 + self.adaptation_rate),
                5.0  # Max reward
            )
        
        # Increase density penalty if high density
        if avg_density > self.target_avg_density:
            self.weights.avg_density_penalty = min(
                self.weights.avg_density_penalty * (1 + self.adaptation_rate),
                1.0  # Max penalty
            )

