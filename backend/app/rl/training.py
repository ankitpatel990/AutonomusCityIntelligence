"""
RL Agent Training Module

Training and evaluation functions for the PPO traffic agent.
Implements FRD-04 FR-04.3: Training pipeline.

Functions:
- train_rl_agent: Train from scratch
- continue_training: Resume from checkpoint
- evaluate_agent: Evaluate trained model
"""

import os
import time
from typing import Optional

try:
    from stable_baselines3 import PPO
    SB3_AVAILABLE = True
except ImportError:
    SB3_AVAILABLE = False


def train_rl_agent(
    density_tracker = None,
    simulation_manager = None,
    total_timesteps: int = None,
    save_path: str = './models/ppo_traffic_final.zip',
    quick_mode: bool = False
) -> Optional['PPO']:
    """
    Train RL agent from scratch
    
    Args:
        density_tracker: Density tracker instance (optional)
        simulation_manager: Simulation manager instance (optional)
        total_timesteps: Total training steps (default from config)
        save_path: Path to save final model
        quick_mode: Use fewer timesteps for quick testing
    
    Returns:
        Trained PPO agent or None if training failed
    """
    if not SB3_AVAILABLE:
        print("[ERROR] stable-baselines3 not installed")
        return None
    
    print("[START] Starting RL agent training...")
    
    # Import here to avoid circular imports
    from app.rl.traffic_env import TrafficSignalEnv
    from app.rl.ppo_config import (
        create_ppo_agent, 
        create_callbacks, 
        TRAINING_CONFIG,
        ProgressCallback
    )
    
    # Create environment
    env = TrafficSignalEnv(
        density_tracker=density_tracker,
        simulation_manager=simulation_manager,
        config={'maxEpisodeSteps': 500}  # Shorter episodes for training
    )
    
    # Create agent
    agent = create_ppo_agent(env)
    if agent is None:
        return None
    
    # Create callbacks
    callbacks = create_callbacks()
    callbacks.append(ProgressCallback(log_interval=5000))
    
    # Determine timesteps
    if total_timesteps is None:
        if quick_mode:
            total_timesteps = TRAINING_CONFIG['quick_train_timesteps']
        else:
            total_timesteps = TRAINING_CONFIG['total_timesteps']
    
    # Train
    start_time = time.time()
    print(f"[TRAIN] Training for {total_timesteps:,} timesteps...")
    print(f"   This may take a while. Monitor with TensorBoard:")
    print(f"   tensorboard --logdir logs/tensorboard/")
    
    try:
        agent.learn(
            total_timesteps=total_timesteps,
            callback=callbacks,
            progress_bar=True
        )
    except KeyboardInterrupt:
        print("\n[WARN] Training interrupted by user")
    
    duration = time.time() - start_time
    print(f"[OK] Training completed in {duration/60:.1f} minutes")
    
    # Save final model
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    agent.save(save_path)
    print(f"[SAVE] Model saved to: {save_path}")
    
    return agent


def continue_training(
    model_path: str,
    density_tracker = None,
    simulation_manager = None,
    additional_timesteps: int = 100_000,
    save_path: str = None
) -> Optional['PPO']:
    """
    Continue training from saved checkpoint
    
    Args:
        model_path: Path to saved model
        density_tracker: Density tracker instance
        simulation_manager: Simulation manager instance
        additional_timesteps: Additional steps to train
        save_path: Path to save updated model (defaults to model_path)
    
    Returns:
        Updated PPO agent or None if loading failed
    """
    if not SB3_AVAILABLE:
        print("[ERROR] stable-baselines3 not installed")
        return None
    
    if not os.path.exists(model_path):
        print(f"[ERROR] Model not found: {model_path}")
        return None
    
    print(f"[LOAD] Loading model from: {model_path}")
    
    from app.rl.traffic_env import TrafficSignalEnv
    from app.rl.ppo_config import create_callbacks, ProgressCallback
    
    # Create environment
    env = TrafficSignalEnv(
        density_tracker=density_tracker,
        simulation_manager=simulation_manager,
        config={'maxEpisodeSteps': 500}
    )
    
    # Load model
    agent = PPO.load(model_path, env=env)
    print("[OK] Model loaded")
    
    # Create callbacks
    callbacks = create_callbacks()
    callbacks.append(ProgressCallback(log_interval=5000))
    
    # Continue training
    start_time = time.time()
    print(f"[TRAIN] Continuing training for {additional_timesteps:,} timesteps...")
    
    try:
        agent.learn(
            total_timesteps=additional_timesteps,
            callback=callbacks,
            reset_num_timesteps=False,  # Continue from current timestep count
            progress_bar=True
        )
    except KeyboardInterrupt:
        print("\n[WARN] Training interrupted by user")
    
    duration = time.time() - start_time
    print(f"[OK] Training continued for {duration/60:.1f} minutes")
    
    # Save updated model
    if save_path is None:
        save_path = model_path
    
    agent.save(save_path)
    print(f"[SAVE] Updated model saved to: {save_path}")
    
    return agent


def evaluate_agent(
    model_path: str,
    density_tracker = None,
    simulation_manager = None,
    n_episodes: int = 10,
    deterministic: bool = True,
    render: bool = False
) -> dict:
    """
    Evaluate trained RL agent
    
    Args:
        model_path: Path to trained model
        density_tracker: Density tracker instance
        simulation_manager: Simulation manager instance
        n_episodes: Number of evaluation episodes
        deterministic: Use deterministic policy
        render: Render environment during evaluation
    
    Returns:
        Dictionary with evaluation statistics
    """
    if not SB3_AVAILABLE:
        print("[ERROR] stable-baselines3 not installed")
        return {'error': 'SB3 not available'}
    
    if not os.path.exists(model_path):
        print(f"[ERROR] Model not found: {model_path}")
        return {'error': f'Model not found: {model_path}'}
    
    from app.rl.traffic_env import TrafficSignalEnv
    
    print(f"[LOAD] Loading model: {model_path}")
    
    # Create environment
    env = TrafficSignalEnv(
        density_tracker=density_tracker,
        simulation_manager=simulation_manager,
        config={'maxEpisodeSteps': 1000}
    )
    
    # Load model
    agent = PPO.load(model_path)
    print("[OK] Model loaded")
    
    # Run evaluation episodes
    print(f"[EVAL] Running {n_episodes} evaluation episodes...")
    
    episode_rewards = []
    episode_lengths = []
    episode_densities = []
    
    for episode in range(n_episodes):
        obs = env.reset()
        episode_reward = 0.0
        done = False
        truncated = False
        steps = 0
        densities = []
        
        while not done and not truncated:
            action, _ = agent.predict(obs, deterministic=deterministic)
            obs, reward, done, truncated, info = env.step(action)
            episode_reward += reward
            steps += 1
            
            if 'avg_density' in info:
                densities.append(info['avg_density'])
            
            if render:
                env.render()
        
        episode_rewards.append(episode_reward)
        episode_lengths.append(steps)
        if densities:
            episode_densities.append(sum(densities) / len(densities))
        
        print(f"   Episode {episode+1}/{n_episodes}: "
              f"Reward={episode_reward:.2f}, Steps={steps}")
    
    # Calculate statistics
    import numpy as np
    
    results = {
        'modelPath': model_path,
        'nEpisodes': n_episodes,
        'deterministic': deterministic,
        'rewards': {
            'mean': float(np.mean(episode_rewards)),
            'std': float(np.std(episode_rewards)),
            'min': float(min(episode_rewards)),
            'max': float(max(episode_rewards))
        },
        'episodeLengths': {
            'mean': float(np.mean(episode_lengths)),
            'min': int(min(episode_lengths)),
            'max': int(max(episode_lengths))
        },
        'avgDensity': float(np.mean(episode_densities)) if episode_densities else 0.0
    }
    
    print(f"\n[RESULTS] Evaluation Results:")
    print(f"   Average Reward: {results['rewards']['mean']:.2f} +/- {results['rewards']['std']:.2f}")
    print(f"   Min/Max Reward: {results['rewards']['min']:.2f} / {results['rewards']['max']:.2f}")
    print(f"   Average Episode Length: {results['episodeLengths']['mean']:.0f}")
    
    return results


def evaluate_rule_based(
    density_tracker = None,
    simulation_manager = None,
    n_episodes: int = 10
) -> dict:
    """
    Evaluate rule-based baseline strategy
    
    Args:
        density_tracker: Density tracker instance
        simulation_manager: Simulation manager instance
        n_episodes: Number of evaluation episodes
    
    Returns:
        Dictionary with evaluation statistics
    """
    from app.rl.traffic_env import TrafficSignalEnv
    from app.agent.decision import RuleBasedEngine
    from app.agent.perception import PerceivedState
    import numpy as np
    
    print("[EVAL] Evaluating Rule-Based baseline strategy...")
    
    # Create environment
    env = TrafficSignalEnv(
        density_tracker=density_tracker,
        simulation_manager=simulation_manager,
        config={'maxEpisodeSteps': 1000}
    )
    
    # Create rule-based engine
    rule_engine = RuleBasedEngine()
    
    # Run evaluation episodes
    episode_rewards = []
    episode_lengths = []
    episode_densities = []
    
    for episode in range(n_episodes):
        result = env.reset()
        obs = result[0] if isinstance(result, tuple) else result
        
        episode_reward = 0.0
        done = False
        truncated = False
        steps = 0
        densities = []
        
        while not done and not truncated:
            # Create perceived state from observation
            # Convert observation back to state format for rule engine
            state = _observation_to_state(obs, env, density_tracker)
            
            # Get rule-based decisions
            decisions = []
            for junction_id, densities_dict in state.junction_densities.items():
                decision = rule_engine.make_decision(
                    junction_id=junction_id,
                    densities=densities_dict,
                    current_signals=state.signal_states.get(junction_id, {}),
                    predictions=None
                )
                decisions.append(decision)
            
            # Convert decisions to actions (for environment)
            action = _decisions_to_action(decisions, env)
            
            # Step environment
            step_result = env.step(action)
            
            if len(step_result) == 5:
                obs, reward, done, truncated, info = step_result
            else:
                obs, reward, done, info = step_result
                truncated = False
            
            episode_reward += reward
            steps += 1
            
            if 'avg_density' in info:
                densities.append(info['avg_density'])
        
        episode_rewards.append(episode_reward)
        episode_lengths.append(steps)
        if densities:
            episode_densities.append(sum(densities) / len(densities))
        
        print(f"   Episode {episode+1}/{n_episodes}: "
              f"Reward={episode_reward:.2f}, Steps={steps}")
    
    # Calculate statistics
    results = {
        'strategy': 'RULE_BASED',
        'nEpisodes': n_episodes,
        'rewards': {
            'mean': float(np.mean(episode_rewards)),
            'std': float(np.std(episode_rewards)),
            'min': float(min(episode_rewards)),
            'max': float(max(episode_rewards))
        },
        'episodeLengths': {
            'mean': float(np.mean(episode_lengths)),
            'min': int(min(episode_lengths)),
            'max': int(max(episode_lengths))
        },
        'avgDensity': float(np.mean(episode_densities)) if episode_densities else 0.0
    }
    
    print(f"\n[RESULTS] Rule-Based Evaluation Results:")
    print(f"   Average Reward: {results['rewards']['mean']:.2f} +/- {results['rewards']['std']:.2f}")
    print(f"   Min/Max Reward: {results['rewards']['min']:.2f} / {results['rewards']['max']:.2f}")
    print(f"   Average Episode Length: {results['episodeLengths']['mean']:.0f}")
    
    return results


def _observation_to_state(obs, env, density_tracker):
    """Convert observation to PerceivedState format"""
    from app.agent.perception import PerceivedState
    
    # Reconstruct junction densities from observation
    junction_densities = {}
    signal_states = {}
    
    junction_ids = env.get_junction_ids()
    
    for i, junction_id in enumerate(junction_ids):
        if i * 7 + 6 < len(obs):
            # Extract densities (normalized 0-1, convert back to 0-100)
            density_n = obs[i * 7 + 0] * 100.0
            density_e = obs[i * 7 + 1] * 100.0
            density_s = obs[i * 7 + 2] * 100.0
            density_w = obs[i * 7 + 3] * 100.0
            
            junction_densities[junction_id] = {
                'N': density_n,
                'E': density_e,
                'S': density_s,
                'W': density_w
            }
            
            # Extract signal state
            signal_val = obs[i * 7 + 5]
            direction_map = {0.0: 'N', 0.33: 'E', 0.66: 'S', 1.0: 'W'}
            # Find closest match
            closest_dir = min(direction_map.keys(), key=lambda x: abs(x - signal_val))
            green_dir = direction_map[closest_dir]
            
            signal_states[junction_id] = {
                'N': 'GREEN' if green_dir == 'N' else 'RED',
                'E': 'GREEN' if green_dir == 'E' else 'RED',
                'S': 'GREEN' if green_dir == 'S' else 'RED',
                'W': 'GREEN' if green_dir == 'W' else 'RED'
            }
    
    return PerceivedState(
        timestamp=0.0,
        junction_densities=junction_densities,
        signal_states=signal_states,
        emergency_active=False,
        emergency_corridor=None,
        emergency_vehicle_id=None,
        manual_controls=None
    )


def _decisions_to_action(decisions, env):
    """Convert signal decisions to environment action array"""
    import numpy as np
    
    junction_ids = env.get_junction_ids()
    action = np.zeros(len(junction_ids), dtype=np.int32)
    
    direction_map = {'N': 0, 'E': 1, 'S': 2, 'W': 3}
    
    for decision in decisions:
        if decision.junction_id in junction_ids:
            idx = junction_ids.index(decision.junction_id)
            action[idx] = direction_map.get(decision.direction, 0)
    
    return action


def compare_strategies(
    model_path: str,
    density_tracker = None,
    simulation_manager = None,
    n_episodes: int = 5
) -> dict:
    """
    Compare RL agent against rule-based baseline
    
    Args:
        model_path: Path to trained RL model
        density_tracker: Density tracker instance
        simulation_manager: Simulation manager instance
        n_episodes: Episodes to run for each strategy
    
    Returns:
        Comparison statistics with improvement metrics
    """
    print("[COMPARE] Comparing RL vs Rule-Based strategies...")
    print(f"   Running {n_episodes} episodes for each strategy\n")
    
    # Evaluate RL agent
    print("=" * 60)
    print("EVALUATING RL AGENT")
    print("=" * 60)
    rl_results = evaluate_agent(
        model_path=model_path,
        density_tracker=density_tracker,
        simulation_manager=simulation_manager,
        n_episodes=n_episodes
    )
    
    # Evaluate rule-based baseline
    print("\n" + "=" * 60)
    print("EVALUATING RULE-BASED BASELINE")
    print("=" * 60)
    rule_results = evaluate_rule_based(
        density_tracker=density_tracker,
        simulation_manager=simulation_manager,
        n_episodes=n_episodes
    )
    
    # Calculate improvement metrics
    rl_avg_reward = rl_results['rewards']['mean']
    rule_avg_reward = rule_results['rewards']['mean']
    
    rl_avg_density = rl_results.get('avgDensity', 0.0)
    rule_avg_density = rule_results.get('avgDensity', 0.0)
    
    # Improvement calculations
    reward_improvement = 0.0
    if rule_avg_reward != 0:
        reward_improvement = ((rl_avg_reward - rule_avg_reward) / abs(rule_avg_reward)) * 100
    
    density_reduction = 0.0
    if rule_avg_density > 0:
        density_reduction = ((rule_avg_density - rl_avg_density) / rule_avg_density) * 100
    
    # Print comparison summary
    print("\n" + "=" * 60)
    print("COMPARISON SUMMARY")
    print("=" * 60)
    print(f"\nReward Performance:")
    print(f"   RL Agent:      {rl_avg_reward:.2f} (avg)")
    print(f"   Rule-Based:    {rule_avg_reward:.2f} (avg)")
    print(f"   Improvement:  {reward_improvement:+.1f}%")
    
    print(f"\nDensity Performance:")
    print(f"   RL Agent:      {rl_avg_density:.2f} (avg)")
    print(f"   Rule-Based:    {rule_avg_density:.2f} (avg)")
    print(f"   Reduction:     {density_reduction:+.1f}%")
    
    # Check if targets are met
    print(f"\nTarget Validation:")
    target_reward_improvement = 30.0  # 30%+ improvement target
    target_density_reduction = 30.0   # 30%+ density reduction target
    
    reward_met = reward_improvement >= target_reward_improvement
    density_met = density_reduction >= target_density_reduction
    
    print(f"   Reward Improvement ≥ {target_reward_improvement}%: {'[OK]' if reward_met else '[ERROR]'} ({reward_improvement:.1f}%)")
    print(f"   Density Reduction ≥ {target_density_reduction}%: {'[OK]' if density_met else '[ERROR]'} ({density_reduction:.1f}%)")
    
    return {
        'rl': rl_results,
        'ruleBased': rule_results,
        'improvement': {
            'rewardImprovementPercent': round(reward_improvement, 2),
            'densityReductionPercent': round(density_reduction, 2),
            'targetsMet': {
                'rewardImprovement': reward_met,
                'densityReduction': density_met
            }
        },
        'summary': {
            'rlAvgReward': rl_avg_reward,
            'ruleAvgReward': rule_avg_reward,
            'rlAvgDensity': rl_avg_density,
            'ruleAvgDensity': rule_avg_density
        }
    }
