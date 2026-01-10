#!/usr/bin/env python
"""
RL Model Training Script

Trains the PPO agent for traffic signal control.
Run from backend directory: python scripts/train_rl_model.py

Options:
    --quick     Quick training with 10k steps (for validation)
    --full      Full training with 100k steps
    --extended  Extended training with 500k steps
"""

import sys
import os
import argparse

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    parser = argparse.ArgumentParser(description='Train RL Traffic Agent')
    parser.add_argument('--quick', action='store_true', help='Quick training (10k steps)')
    parser.add_argument('--full', action='store_true', help='Full training (100k steps)')
    parser.add_argument('--extended', action='store_true', help='Extended training (500k steps)')
    parser.add_argument('--steps', type=int, default=None, help='Custom timesteps')
    args = parser.parse_args()
    
    # Determine timesteps
    if args.steps:
        total_timesteps = args.steps
    elif args.quick:
        total_timesteps = 10_000
    elif args.extended:
        total_timesteps = 500_000
    elif args.full:
        total_timesteps = 100_000
    else:
        total_timesteps = 100_000  # Default to full training
    
    print("=" * 60)
    print("RL TRAFFIC AGENT TRAINING")
    print("=" * 60)
    print(f"Timesteps: {total_timesteps:,}")
    print(f"Mode: {'Quick' if args.quick else 'Extended' if args.extended else 'Full'}")
    print("=" * 60)
    
    # Import training modules
    print("\n[1/4] Importing modules...")
    try:
        from app.rl.training import train_rl_agent
        from app.density.density_tracker import get_density_tracker, init_density_tracker
        print("   [OK] Modules imported successfully")
    except ImportError as e:
        print(f"   [ERROR] Import error: {e}")
        print("\n   Make sure you have installed requirements:")
        print("   pip install stable-baselines3 gymnasium torch tensorboard")
        sys.exit(1)
    
    # Initialize density tracker
    print("\n[2/4] Initializing density tracker...")
    try:
        density_tracker = init_density_tracker({})
        
        # Initialize with mock junctions for training
        class MockJunction:
            def __init__(self, id):
                self.id = id
        
        junctions = [MockJunction(f"J-{i+1}") for i in range(9)]
        density_tracker.initialize_junctions(junctions)
        print(f"   [OK] Density tracker initialized with {len(junctions)} junctions")
    except Exception as e:
        print(f"   [ERROR] Error: {e}")
        sys.exit(1)
    
    # Determine save path
    if args.quick:
        save_path = './models/ppo_traffic_quick.zip'
    elif args.extended:
        save_path = './models/ppo_traffic_extended.zip'
    else:
        save_path = './models/ppo_traffic_final.zip'
    
    # Create models directory
    os.makedirs('./models', exist_ok=True)
    os.makedirs('./logs/tensorboard', exist_ok=True)
    
    print(f"\n[3/4] Starting training...")
    print(f"   Save path: {save_path}")
    print(f"   TensorBoard: ./logs/tensorboard/")
    print(f"\n   Monitor with: tensorboard --logdir logs/tensorboard/")
    print("\n" + "-" * 60)
    
    # Train
    try:
        agent = train_rl_agent(
            density_tracker=density_tracker,
            simulation_manager=None,
            total_timesteps=total_timesteps,
            save_path=save_path,
            quick_mode=args.quick
        )
        
        if agent:
            print("\n" + "-" * 60)
            print("\n[4/4] Training complete!")
            print(f"   [OK] Model saved to: {save_path}")
            
            # Verify model loads correctly
            print("\n[VERIFY] Testing model load...")
            from stable_baselines3 import PPO
            loaded = PPO.load(save_path)
            print(f"   [OK] Model loads successfully")
            print(f"   [OK] Policy: {type(loaded.policy).__name__}")
            print(f"   [OK] Device: {loaded.device}")
            
            print("\n" + "=" * 60)
            print("SUCCESS! Model is ready for use.")
            print("=" * 60)
            print(f"\nNext steps:")
            print(f"  1. Run comparison: python scripts/compare_strategies.py")
            print(f"  2. Start agent with RL: Set strategy to 'RL' in agent")
            print(f"  3. Monitor via API: GET /api/rl/status")
        else:
            print("\n   [ERROR] Training failed")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Training interrupted by user")
        print("   Partial model may have been saved in checkpoints/")
        sys.exit(0)
    except Exception as e:
        print(f"\n   [ERROR] Training error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

