"""
Traffic Signal RL Environment

OpenAI Gymnasium environment for traffic signal control using PPO.
Implements FRD-04 FR-04.1: Gym environment wrapper.

Observation Space: Box(63,) - 9 junctions × 7 features
Action Space: MultiDiscrete([4, 4, 4, 4, 4, 4, 4, 4, 4]) - 9 junctions, 4 directions each

Reward: Based on throughput, waiting time, and fairness
"""

# Use gymnasium (modern) with fallback to gym (legacy)
try:
    import gymnasium as gym
    from gymnasium import spaces
    GYMNASIUM_AVAILABLE = True
except ImportError:
    import gym
    from gym import spaces
    GYMNASIUM_AVAILABLE = False

import numpy as np
from typing import Dict, Tuple, Any, Optional, List
import time

from app.density.density_tracker import (
    DensityTracker, 
    JunctionDensityData, 
    CityWideDensityMetrics,
    get_density_tracker
)


class TrafficSignalEnv(gym.Env):
    """
    OpenAI Gym environment for traffic signal control
    
    Observation Space: Box(63,) - 9 junctions × 7 features
    Action Space: MultiDiscrete([4, 4, 4, 4, 4, 4, 4, 4, 4]) - 9 junctions, 4 directions each
    
    Features per junction (7 total):
        [0-3] Density in 4 directions (N, E, S, W) - normalized 0-1
        [4]   Average waiting time (normalized)
        [5]   Current signal state (0-3 for N,E,S,W)
        [6]   Vehicle count at junction (normalized)
    
    Reward: Based on throughput, waiting time, and fairness
    """
    
    metadata = {'render.modes': ['human', 'rgb_array']}
    
    def __init__(self, 
                 density_tracker: DensityTracker = None,
                 simulation_manager = None,
                 config: dict = None):
        """
        Initialize RL environment
        
        Args:
            density_tracker: Density tracker instance
            simulation_manager: Simulation manager instance (optional)
            config: Environment configuration
        """
        super(TrafficSignalEnv, self).__init__()
        
        self.density_tracker = density_tracker or get_density_tracker()
        self.simulation_manager = simulation_manager
        self.config = config or {}
        
        # Number of junctions (fixed at 9 for consistent observation space)
        self.num_junctions = self.config.get('numJunctions', 9)
        self.junction_ids: List[str] = []
        
        # Signal states tracking (must be before _initialize_junctions)
        self.signal_states: Dict[str, str] = {}  # junction_id -> current green direction
        
        # Initialize junction IDs from density tracker
        self._initialize_junctions()
        
        # OBSERVATION SPACE: 63 dimensions
        # 9 junctions × 7 features = 63
        # Features per junction:
        #   [0-3] Density in 4 directions (N, E, S, W) - normalized 0-1
        #   [4]   Average waiting time (normalized)
        #   [5]   Current signal state (0-3 for N,E,S,W)
        #   [6]   Vehicle count at junction (normalized)
        self.observation_space = spaces.Box(
            low=0.0,
            high=1.0,  # Normalized observations
            shape=(self.num_junctions * 7,),
            dtype=np.float32
        )
        
        # ACTION SPACE: MultiDiscrete
        # Each junction can choose 1 of 4 directions to make GREEN
        # [0=North, 1=East, 2=South, 3=West]
        self.action_space = spaces.MultiDiscrete([4] * self.num_junctions)
        
        # Episode tracking
        self.episode_step = 0
        self.max_episode_steps = self.config.get('maxEpisodeSteps', 1000)
        
        # Performance tracking
        self.episode_reward = 0.0
        self.episode_start_time = 0.0
        
        # Previous state for reward calculation
        self.prev_total_waiting_time = 0.0
        self.prev_throughput = 0
        self.prev_avg_density = 0.0
        
        # Reward calculator
        self._reward_calculator = None
        
        print(f"[OK] Traffic RL Environment initialized")
        print(f"   Observation space: {self.observation_space.shape}")
        print(f"   Action space: {self.action_space}")
        print(f"   Max episode steps: {self.max_episode_steps}")
    
    def _initialize_junctions(self):
        """Initialize junction IDs from density tracker"""
        if self.density_tracker and self.density_tracker.junction_densities:
            self.junction_ids = sorted(self.density_tracker.junction_densities.keys())
        
        # Pad or create default junction IDs if needed
        while len(self.junction_ids) < self.num_junctions:
            idx = len(self.junction_ids)
            self.junction_ids.append(f"J-{idx + 1}")
        
        # Truncate if too many
        self.junction_ids = self.junction_ids[:self.num_junctions]
        
        # Initialize signal states to North green
        for junction_id in self.junction_ids:
            self.signal_states[junction_id] = 'N'
    
    @property
    def reward_calculator(self):
        """Lazy load reward calculator"""
        if self._reward_calculator is None:
            from app.rl.rewards import RewardCalculator, RewardWeights
            self._reward_calculator = RewardCalculator(
                weights=RewardWeights(
                    throughput=1.0,
                    waiting_time=0.1,
                    density_balance=0.5,
                    congestion_penalty=2.0,
                    avg_density_penalty=0.1
                )
            )
        return self._reward_calculator
    
    def reset(self, seed: int = None, options: dict = None) -> Tuple[np.ndarray, Dict]:
        """
        Reset environment for new episode
        
        Returns:
            observation: Initial observation
            info: Additional information dictionary
        """
        super().reset(seed=seed)
        
        # Reset simulation if available
        if self.simulation_manager and hasattr(self.simulation_manager, 'reset'):
            self.simulation_manager.reset()
        
        # Reset episode tracking
        self.episode_step = 0
        self.episode_reward = 0.0
        self.episode_start_time = time.time()
        
        # Reset previous metrics
        self.prev_total_waiting_time = 0.0
        self.prev_throughput = 0
        self.prev_avg_density = 0.0
        
        # Reset signal states to North green
        for junction_id in self.junction_ids:
            self.signal_states[junction_id] = 'N'
        
        # Reset reward calculator
        if self._reward_calculator:
            self._reward_calculator.reset()
        
        # Re-initialize junctions in case they changed
        self._initialize_junctions()
        
        # Get initial observation
        observation = self._get_observation()
        
        # Return observation and info dict (Gymnasium API)
        info = {
            'episode_step': 0,
            'num_junctions': len(self.junction_ids)
        }
        
        return observation, info
    
    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        """
        Execute one environment step
        
        Args:
            action: Array of actions (one per junction)
        
        Returns:
            observation: Next state observation
            reward: Reward for this step
            terminated: Whether episode ended naturally
            truncated: Whether episode was cut short
            info: Additional information
        """
        # Apply actions to signals
        self._apply_actions(action)
        
        # Simulate for one time step (e.g., 5 simulation seconds)
        simulation_seconds = self.config.get('stepDuration', 5)
        self._advance_simulation(simulation_seconds)
        
        # Get new observation
        observation = self._get_observation()
        
        # Calculate reward
        reward = self._calculate_reward()
        
        # Check if episode is done
        self.episode_step += 1
        terminated = False  # No natural termination condition
        truncated = self.episode_step >= self.max_episode_steps
        
        # Track episode reward
        self.episode_reward += reward
        
        # Additional info
        city_metrics = self.density_tracker.get_city_metrics()
        info = {
            'episode_step': self.episode_step,
            'episode_reward': self.episode_reward,
            'total_vehicles': city_metrics.total_vehicles,
            'avg_density': city_metrics.avg_density_score,
            'congestion_points': city_metrics.congestion_points
        }
        
        if terminated or truncated:
            info['episode_duration'] = time.time() - self.episode_start_time
        
        return observation, reward, terminated, truncated, info
    
    def _get_observation(self) -> np.ndarray:
        """
        Get current observation (63 dimensions)
        
        Observation structure (7 features × 9 junctions):
        - Density in 4 directions (N, E, S, W) - normalized
        - Average waiting time - normalized
        - Current signal state (0-3 for N,E,S,W) - normalized
        - Vehicle count at junction - normalized
        """
        observation = []
        
        for junction_id in self.junction_ids:
            # Get density for this junction
            junction_data = self.density_tracker.get_junction_density(junction_id)
            
            if junction_data:
                # Density for each direction (4 values, normalized 0-1)
                observation.append(min(junction_data.density_north / 100.0, 1.0))
                observation.append(min(junction_data.density_east / 100.0, 1.0))
                observation.append(min(junction_data.density_south / 100.0, 1.0))
                observation.append(min(junction_data.density_west / 100.0, 1.0))
                
                # Average waiting time (normalized to 0-1, max 100 seconds)
                avg_wait = min(junction_data.avg_waiting_time / 100.0, 1.0)
                observation.append(avg_wait)
                
                # Current signal state (0-3 for N,E,S,W, normalized to 0-1)
                current_green = self.signal_states.get(junction_id, 'N')
                direction_encoding = {'N': 0.0, 'E': 0.33, 'S': 0.66, 'W': 1.0}
                observation.append(direction_encoding.get(current_green, 0.0))
                
                # Vehicle count at junction (normalized, max 50)
                vehicle_count = min(junction_data.total_vehicles / 50.0, 1.0)
                observation.append(vehicle_count)
            else:
                # Default values if no data
                observation.extend([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        
        return np.array(observation, dtype=np.float32)
    
    def _apply_actions(self, actions: np.ndarray):
        """
        Apply RL agent actions to traffic signals
        
        Args:
            actions: Array of actions (one per junction)
                    Each action is 0-3 representing N,E,S,W direction to make GREEN
        """
        direction_map = {0: 'N', 1: 'E', 2: 'S', 3: 'W'}
        
        for i, junction_id in enumerate(self.junction_ids):
            if i < len(actions):
                action_idx = int(actions[i])
                direction = direction_map.get(action_idx, 'N')
                
                # Update internal signal state
                self.signal_states[junction_id] = direction
                
                # If simulation manager is available, apply to simulation
                if self.simulation_manager and hasattr(self.simulation_manager, 'set_signal_green'):
                    self.simulation_manager.set_signal_green(
                        junction_id=junction_id,
                        direction=direction,
                        duration=30  # Default green duration
                    )
    
    def _advance_simulation(self, seconds: float):
        """
        Advance simulation time
        
        Args:
            seconds: Number of simulation seconds to advance
        """
        if self.simulation_manager and hasattr(self.simulation_manager, 'advance_time'):
            self.simulation_manager.advance_time(seconds)
        else:
            # Simulate time passing for density tracker updates
            time.sleep(0.01)  # Small delay for real-time simulation
    
    def _calculate_reward(self) -> float:
        """
        Calculate reward for current state
        
        Uses the RewardCalculator for detailed reward computation.
        
        Reward components:
        1. Throughput improvement (vehicles that cleared junctions)
        2. Waiting time reduction
        3. Density balance (fairness across junctions)
        4. Penalties for congestion
        
        Returns:
            reward: Scalar reward value
        """
        # Get current metrics
        city_metrics = self.density_tracker.get_city_metrics()
        
        # Build current state dict for reward calculator
        current_state = {
            'throughput': self._get_throughput_count(),
            'total_waiting_time': self._get_total_waiting_time(),
            'congestion_points': city_metrics.congestion_points,
            'avg_density': city_metrics.avg_density_score
        }
        
        # Use reward calculator
        reward, breakdown = self.reward_calculator.calculate_reward(
            current_state,
            self.density_tracker.junction_densities
        )
        
        # Log breakdown periodically
        if self.episode_step % 100 == 0 and self.episode_step > 0:
            print(f"   [Step {self.episode_step}] Reward: {reward:.2f}, Breakdown: {breakdown}")
        
        return reward
    
    def _get_throughput_count(self) -> int:
        """Get number of vehicles that have cleared junctions"""
        if self.simulation_manager and hasattr(self.simulation_manager, 'get_throughput_count'):
            return self.simulation_manager.get_throughput_count()
        
        # Estimate from density changes
        city_metrics = self.density_tracker.get_city_metrics()
        return city_metrics.total_vehicles
    
    def _get_total_waiting_time(self) -> float:
        """Get total waiting time across all vehicles"""
        total_wait = 0.0
        
        for junction_data in self.density_tracker.junction_densities.values():
            total_wait += junction_data.avg_waiting_time * junction_data.total_vehicles
        
        return total_wait
    
    def render(self, mode: str = 'human') -> Optional[np.ndarray]:
        """
        Render environment (optional)
        
        Args:
            mode: Render mode ('human' or 'rgb_array')
        
        Returns:
            RGB array if mode is 'rgb_array', None otherwise
        """
        if mode == 'human':
            city_metrics = self.density_tracker.get_city_metrics()
            print(f"Step: {self.episode_step}, "
                  f"Reward: {self.episode_reward:.2f}, "
                  f"Vehicles: {city_metrics.total_vehicles}, "
                  f"Avg Density: {city_metrics.avg_density_score:.1f}")
        return None
    
    def close(self):
        """Clean up environment resources"""
        pass
    
    def get_junction_ids(self) -> List[str]:
        """Get list of junction IDs"""
        return self.junction_ids.copy()
    
    def get_signal_states(self) -> Dict[str, str]:
        """Get current signal states"""
        return self.signal_states.copy()


class TrafficSignalEnvWrapper:
    """
    Wrapper for creating TrafficSignalEnv with lazy initialization
    
    Useful for deferred environment creation during training setup
    """
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        self._env = None
    
    def __call__(self) -> TrafficSignalEnv:
        """Create and return environment instance"""
        if self._env is None:
            self._env = TrafficSignalEnv(config=self.config)
        return self._env
    
    def make_env(self, density_tracker: DensityTracker = None, 
                 simulation_manager = None) -> TrafficSignalEnv:
        """Create environment with injected dependencies"""
        return TrafficSignalEnv(
            density_tracker=density_tracker,
            simulation_manager=simulation_manager,
            config=self.config
        )

