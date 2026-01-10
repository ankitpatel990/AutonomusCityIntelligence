"""
RL System Integration Tests

Comprehensive testing of the RL system including environment, training,
inference, and integration with the agent loop.
Implements FRD-04 Section 8: Testing requirements.

Performance requirements:
- Inference: < 100ms
- Environment step: < 50ms

Run tests:
    pytest tests/test_rl_system.py -v
    pytest tests/test_rl_system.py -k "performance" -v
    pytest tests/test_rl_system.py --cov=app.rl
"""

import pytest
import numpy as np
import time
import os
import tempfile

# Import test fixtures and helpers
from app.density.density_tracker import DensityTracker, init_density_tracker


# ============================================
# Fixtures
# ============================================

@pytest.fixture
def density_tracker():
    """Create a fresh density tracker for testing"""
    return init_density_tracker({})


@pytest.fixture
def mock_junctions():
    """Create mock junctions"""
    from dataclasses import dataclass
    
    @dataclass
    class MockJunction:
        id: str
    
    return [MockJunction(id=f"J-{i+1}") for i in range(9)]


@pytest.fixture
def mock_roads():
    """Create mock roads"""
    from dataclasses import dataclass
    
    @dataclass
    class MockRoad:
        id: str
    
    return [MockRoad(id=f"R-{i+1}") for i in range(20)]


@pytest.fixture
def traffic_env(density_tracker):
    """Create traffic environment for testing"""
    from app.rl.traffic_env import TrafficSignalEnv
    
    # Initialize density tracker with mock data
    density_tracker.initialize_junctions([
        type('Junction', (), {'id': f'J-{i+1}'})() for i in range(9)
    ])
    
    env = TrafficSignalEnv(
        density_tracker=density_tracker,
        simulation_manager=None,
        config={'maxEpisodeSteps': 100}
    )
    
    return env


# ============================================
# Environment Tests
# ============================================

class TestTrafficSignalEnv:
    """Test suite for TrafficSignalEnv"""
    
    def test_environment_creation(self, traffic_env):
        """Test environment creates successfully"""
        assert traffic_env is not None
        assert traffic_env.observation_space is not None
        assert traffic_env.action_space is not None
    
    def test_observation_space(self, traffic_env):
        """Test observation space matches specification (63 dimensions)"""
        expected_shape = (63,)
        assert traffic_env.observation_space.shape == expected_shape, \
            f"Observation space should be {expected_shape}, got {traffic_env.observation_space.shape}"
    
    def test_action_space(self, traffic_env):
        """Test action space matches specification (MultiDiscrete)"""
        # Should be MultiDiscrete([4, 4, 4, 4, 4, 4, 4, 4, 4])
        assert len(traffic_env.action_space.nvec) == 9, "Should have 9 junctions"
        assert all(n == 4 for n in traffic_env.action_space.nvec), \
            "Each junction should have 4 possible actions"
    
    def test_reset(self, traffic_env):
        """Test environment reset returns correct observation"""
        result = traffic_env.reset()
        
        # Handle both old API (obs) and new API (obs, info)
        if isinstance(result, tuple):
            obs, info = result
            assert isinstance(info, dict), "Info should be a dict"
        else:
            obs = result
        
        assert obs.shape == (63,), f"Observation shape mismatch: {obs.shape}"
        assert obs.dtype == np.float32, "Observation should be float32"
        assert np.all(obs >= 0) and np.all(obs <= 1), "Observations should be normalized 0-1"
    
    def test_step(self, traffic_env):
        """Test environment step returns correct values"""
        result = traffic_env.reset()
        obs = result[0] if isinstance(result, tuple) else result
        
        # Random action
        action = traffic_env.action_space.sample()
        
        step_result = traffic_env.step(action)
        
        # Handle 5-tuple (new API) or 4-tuple (old API)
        if len(step_result) == 5:
            obs, reward, terminated, truncated, info = step_result
        else:
            obs, reward, done, info = step_result
            terminated = done
            truncated = False
        
        assert obs.shape == (63,), "Observation shape mismatch"
        assert isinstance(reward, (int, float)), "Reward should be numeric"
        assert isinstance(terminated, bool), "Terminated should be boolean"
        assert isinstance(info, dict), "Info should be dict"
    
    def test_episode_completion(self, traffic_env):
        """Test complete episode runs without errors"""
        result = traffic_env.reset()
        obs = result[0] if isinstance(result, tuple) else result
        
        total_reward = 0.0
        steps = 0
        done = False
        truncated = False
        
        while not done and not truncated and steps < 100:
            action = traffic_env.action_space.sample()
            step_result = traffic_env.step(action)
            
            if len(step_result) == 5:
                obs, reward, done, truncated, info = step_result
            else:
                obs, reward, done, info = step_result
                truncated = False
            
            total_reward += reward
            steps += 1
        
        assert steps > 0, "Should complete at least one step"
        assert isinstance(total_reward, (int, float)), "Total reward should be numeric"
    
    def test_action_application(self, traffic_env):
        """Test actions are correctly applied"""
        result = traffic_env.reset()
        
        # All North green
        action = np.array([0] * 9)
        traffic_env._apply_actions(action)
        
        # Check signal states
        for junction_id in traffic_env.junction_ids:
            assert traffic_env.signal_states[junction_id] == 'N'
        
        # All East green
        action = np.array([1] * 9)
        traffic_env._apply_actions(action)
        
        for junction_id in traffic_env.junction_ids:
            assert traffic_env.signal_states[junction_id] == 'E'


# ============================================
# Reward Tests
# ============================================

class TestRewardCalculator:
    """Test suite for RewardCalculator"""
    
    def test_reward_calculator_creation(self):
        """Test reward calculator creates successfully"""
        from app.rl.rewards import RewardCalculator, RewardWeights
        
        calc = RewardCalculator()
        assert calc is not None
        assert calc.weights is not None
    
    def test_reward_calculation(self):
        """Test reward calculation returns valid values"""
        from app.rl.rewards import RewardCalculator
        
        calc = RewardCalculator()
        
        current_state = {
            'throughput': 10,
            'total_waiting_time': 50.0,
            'congestion_points': 2,
            'avg_density': 15.0
        }
        
        reward, breakdown = calc.calculate_reward(current_state, {})
        
        assert isinstance(reward, (int, float)), "Reward should be numeric"
        assert isinstance(breakdown, dict), "Breakdown should be dict"
        assert len(breakdown) > 0, "Breakdown should have components"
    
    def test_reward_weights(self):
        """Test custom reward weights"""
        from app.rl.rewards import RewardCalculator, RewardWeights
        
        weights = RewardWeights(throughput=2.0, congestion_penalty=5.0)
        calc = RewardCalculator(weights=weights)
        
        assert calc.weights.throughput == 2.0
        assert calc.weights.congestion_penalty == 5.0
    
    def test_episode_summary(self):
        """Test episode summary generation"""
        from app.rl.rewards import RewardCalculator
        
        calc = RewardCalculator()
        
        # Simulate a few steps
        for i in range(10):
            calc.calculate_reward({
                'throughput': i,
                'total_waiting_time': 50.0 - i,
                'congestion_points': 1,
                'avg_density': 20.0
            }, {})
        
        summary = calc.get_episode_summary()
        
        assert 'totalReward' in summary
        assert 'avgReward' in summary
        assert 'steps' in summary
        assert summary['steps'] == 10
    
    def test_reset(self):
        """Test reward calculator reset"""
        from app.rl.rewards import RewardCalculator
        
        calc = RewardCalculator()
        
        # Calculate some rewards
        calc.calculate_reward({'throughput': 10}, {})
        
        # Reset
        calc.reset()
        
        assert len(calc.episode_rewards) == 0
        assert calc.prev_throughput == 0


# ============================================
# Inference Tests
# ============================================

class TestRLInferenceService:
    """Test suite for RLInferenceService"""
    
    def test_inference_service_creation(self):
        """Test inference service creates successfully"""
        from app.rl.inference import RLInferenceService
        
        service = RLInferenceService()
        assert service is not None
        assert not service.is_ready()  # No model loaded
    
    def test_model_not_loaded_error(self):
        """Test error when predicting without model"""
        from app.rl.inference import RLInferenceService
        
        service = RLInferenceService()
        observation = np.random.rand(63).astype(np.float32)
        
        with pytest.raises(RuntimeError):
            service.predict(observation)
    
    def test_invalid_observation_shape(self):
        """Test error on invalid observation shape"""
        from app.rl.inference import RLInferenceService
        
        service = RLInferenceService()
        
        # Skip if no model - we're testing shape validation
        if not service.is_ready():
            pytest.skip("No model loaded for shape validation test")
        
        wrong_shape = np.random.rand(50).astype(np.float32)
        
        with pytest.raises(ValueError):
            service.predict(wrong_shape)
    
    def test_statistics(self):
        """Test inference statistics"""
        from app.rl.inference import RLInferenceService
        
        service = RLInferenceService()
        stats = service.get_statistics()
        
        assert 'modelLoaded' in stats
        assert 'inferenceCount' in stats
        assert 'avgInferenceTime' in stats
        assert stats['modelLoaded'] == False
        assert stats['inferenceCount'] == 0
    
    def test_global_service(self):
        """Test global inference service singleton"""
        from app.rl.inference import get_inference_service, set_inference_service, RLInferenceService
        
        # Get default service
        service1 = get_inference_service()
        service2 = get_inference_service()
        
        assert service1 is service2  # Same instance
        
        # Set new service
        new_service = RLInferenceService()
        set_inference_service(new_service)
        
        service3 = get_inference_service()
        assert service3 is new_service


# ============================================
# Integration Tests
# ============================================

class TestRLIntegration:
    """Integration tests for RL system"""
    
    def test_env_with_density_tracker(self, density_tracker):
        """Test environment integration with density tracker"""
        from app.rl.traffic_env import TrafficSignalEnv
        
        # Initialize junctions
        density_tracker.initialize_junctions([
            type('Junction', (), {'id': f'J-{i+1}'})() for i in range(9)
        ])
        
        env = TrafficSignalEnv(density_tracker=density_tracker)
        
        result = env.reset()
        obs = result[0] if isinstance(result, tuple) else result
        assert obs.shape == (63,)
        
        action = env.action_space.sample()
        step_result = env.step(action)
        
        if len(step_result) == 5:
            obs, reward, _, _, info = step_result
        else:
            obs, reward, _, info = step_result
        
        assert 'episode_step' in info
        assert 'avg_density' in info


# ============================================
# Performance Tests
# ============================================

class TestPerformance:
    """Performance benchmark tests"""
    
    def test_environment_step_performance(self, traffic_env):
        """Test environment step completes in < 50ms"""
        result = traffic_env.reset()
        
        times = []
        for _ in range(100):
            action = traffic_env.action_space.sample()
            
            start = time.perf_counter()
            traffic_env.step(action)
            duration = (time.perf_counter() - start) * 1000  # ms
            
            times.append(duration)
        
        avg_time = np.mean(times)
        max_time = np.max(times)
        
        print(f"\nEnvironment step: avg={avg_time:.3f}ms, max={max_time:.3f}ms")
        
        assert avg_time < 50, f"Step too slow: {avg_time:.2f}ms"
    
    def test_observation_generation_performance(self, traffic_env):
        """Test observation generation is fast"""
        result = traffic_env.reset()
        
        times = []
        for _ in range(1000):
            start = time.perf_counter()
            obs = traffic_env._get_observation()
            duration = (time.perf_counter() - start) * 1000  # ms
            times.append(duration)
        
        avg_time = np.mean(times)
        
        print(f"\nObservation generation: avg={avg_time:.4f}ms")
        
        assert avg_time < 1, f"Observation too slow: {avg_time:.2f}ms"
    
    def test_reward_calculation_performance(self, traffic_env):
        """Test reward calculation is fast"""
        from app.rl.rewards import RewardCalculator
        
        calc = RewardCalculator()
        
        times = []
        for i in range(1000):
            state = {
                'throughput': i,
                'total_waiting_time': 50.0,
                'congestion_points': 2,
                'avg_density': 20.0
            }
            
            start = time.perf_counter()
            calc.calculate_reward(state, {})
            duration = (time.perf_counter() - start) * 1000  # ms
            times.append(duration)
        
        avg_time = np.mean(times)
        
        print(f"\nReward calculation: avg={avg_time:.4f}ms")
        
        assert avg_time < 1, f"Reward too slow: {avg_time:.2f}ms"


# ============================================
# PPO Config Tests (if SB3 available)
# ============================================

class TestPPOConfig:
    """Test PPO configuration (requires stable-baselines3)"""
    
    def test_ppo_config_exists(self):
        """Test PPO config is defined"""
        try:
            from app.rl.ppo_config import PPO_CONFIG, TRAINING_CONFIG
            
            assert 'learning_rate' in PPO_CONFIG
            assert 'n_steps' in PPO_CONFIG
            assert 'total_timesteps' in TRAINING_CONFIG
        except ImportError:
            pytest.skip("stable-baselines3 not installed")
    
    def test_get_device(self):
        """Test device detection"""
        try:
            from app.rl.ppo_config import get_device
            
            device = get_device()
            assert device in ['cuda', 'cpu']
        except ImportError:
            pytest.skip("torch not installed")


# ============================================
# Training Tests (optional, requires SB3)
# ============================================

class TestTraining:
    """Test training functions (requires stable-baselines3)"""
    
    @pytest.mark.slow
    def test_create_ppo_agent(self, traffic_env):
        """Test PPO agent creation"""
        try:
            from app.rl.ppo_config import create_ppo_agent
            
            agent = create_ppo_agent(traffic_env)
            
            if agent is None:
                pytest.skip("PPO agent creation returned None")
            
            assert agent is not None
            assert agent.policy is not None
        except ImportError:
            pytest.skip("stable-baselines3 not installed")
    
    @pytest.mark.slow
    def test_mini_training(self, traffic_env):
        """Test minimal training (100 steps)"""
        try:
            from app.rl.ppo_config import create_ppo_agent
            
            agent = create_ppo_agent(traffic_env)
            
            if agent is None:
                pytest.skip("PPO agent not available")
            
            # Train for minimal steps
            agent.learn(total_timesteps=100, progress_bar=False)
            
            # Verify agent can predict
            result = traffic_env.reset()
            obs = result[0] if isinstance(result, tuple) else result
            action, _ = agent.predict(obs)
            
            assert action.shape == (9,)
        except ImportError:
            pytest.skip("stable-baselines3 not installed")
    
    @pytest.mark.slow
    def test_model_save_load(self, traffic_env):
        """Test model saving and loading"""
        try:
            from app.rl.ppo_config import create_ppo_agent
            from stable_baselines3 import PPO
            
            agent = create_ppo_agent(traffic_env)
            
            if agent is None:
                pytest.skip("PPO agent not available")
            
            # Save to temp file
            with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as f:
                model_path = f.name
            
            try:
                agent.save(model_path)
                assert os.path.exists(model_path)
                
                # Load model
                loaded = PPO.load(model_path)
                assert loaded is not None
                
                # Verify prediction works
                result = traffic_env.reset()
                obs = result[0] if isinstance(result, tuple) else result
                action, _ = loaded.predict(obs)
                assert action.shape == (9,)
            finally:
                if os.path.exists(model_path):
                    os.remove(model_path)
                    
        except ImportError:
            pytest.skip("stable-baselines3 not installed")


# ============================================
# API Tests
# ============================================

class TestRLAPI:
    """Test RL API endpoints"""
    
    def test_models_list_endpoint(self):
        """Test /api/rl/models endpoint structure"""
        # This would require FastAPI TestClient
        # For now, test the route function directly
        from app.api.rl_routes import list_models
        import asyncio
        
        result = asyncio.get_event_loop().run_until_complete(list_models())
        assert isinstance(result, list)
    
    def test_status_endpoint(self):
        """Test /api/rl/status endpoint"""
        from app.api.rl_routes import get_rl_status
        import asyncio
        
        result = asyncio.get_event_loop().run_until_complete(get_rl_status())
        assert hasattr(result, 'model_loaded')
        assert hasattr(result, 'ready')

