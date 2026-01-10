#!/usr/bin/env python3
"""
RL Agent Training Script

Command-line interface for training, evaluating, and managing RL models.
Implements FRD-04 FR-04.3: Training pipeline.

Usage:
    python train_rl.py train --timesteps 1000000
    python train_rl.py train --quick  # Quick 10k timesteps for testing
    python train_rl.py continue --model models/checkpoint.zip --timesteps 100000
    python train_rl.py eval --model models/ppo_traffic_final.zip --episodes 10
    python train_rl.py info --model models/ppo_traffic_final.zip
"""

import argparse
import sys
import os

# Add app to path
sys.path.insert(0, os.path.dirname(__file__))


def cmd_train(args):
    """Train RL agent from scratch"""
    print("=" * 60)
    print("  RL AGENT TRAINING - Traffic Signal Optimization")
    print("=" * 60)
    
    from app.rl.training import train_rl_agent
    from app.density import init_density_tracker
    
    # Initialize density tracker
    print("\n📦 Initializing simulation components...")
    density_tracker = init_density_tracker({})
    
    # Determine timesteps
    if args.quick:
        timesteps = 10_000
        print("⚡ Quick training mode (10k timesteps)")
    else:
        timesteps = args.timesteps
    
    print(f"\n🎯 Training for {timesteps:,} timesteps")
    print(f"   Output: {args.output}")
    
    # Train agent
    agent = train_rl_agent(
        density_tracker=density_tracker,
        simulation_manager=None,
        total_timesteps=timesteps,
        save_path=args.output,
        quick_mode=args.quick
    )
    
    if agent:
        print("\n✅ Training complete!")
        print(f"   Model saved: {args.output}")
        print("\n📊 View training progress:")
        print("   tensorboard --logdir logs/tensorboard/")
    else:
        print("\n❌ Training failed!")
        sys.exit(1)


def cmd_continue(args):
    """Continue training from checkpoint"""
    print("=" * 60)
    print("  CONTINUE RL TRAINING")
    print("=" * 60)
    
    if not os.path.exists(args.model):
        print(f"❌ Model not found: {args.model}")
        sys.exit(1)
    
    from app.rl.training import continue_training
    from app.density import init_density_tracker
    
    # Initialize components
    print("\n📦 Initializing simulation components...")
    density_tracker = init_density_tracker({})
    
    print(f"\n📥 Loading model: {args.model}")
    print(f"   Additional timesteps: {args.timesteps:,}")
    
    # Continue training
    agent = continue_training(
        model_path=args.model,
        density_tracker=density_tracker,
        simulation_manager=None,
        additional_timesteps=args.timesteps,
        save_path=args.output or args.model
    )
    
    if agent:
        print("\n✅ Training continued!")
    else:
        print("\n❌ Training failed!")
        sys.exit(1)


def cmd_eval(args):
    """Evaluate trained model"""
    print("=" * 60)
    print("  MODEL EVALUATION")
    print("=" * 60)
    
    if not os.path.exists(args.model):
        print(f"❌ Model not found: {args.model}")
        sys.exit(1)
    
    from app.rl.training import evaluate_agent
    from app.density import init_density_tracker
    
    # Initialize components
    print("\n📦 Initializing simulation components...")
    density_tracker = init_density_tracker({})
    
    # Run evaluation
    results = evaluate_agent(
        model_path=args.model,
        density_tracker=density_tracker,
        simulation_manager=None,
        n_episodes=args.episodes,
        deterministic=not args.stochastic,
        render=args.render
    )
    
    if 'error' in results:
        print(f"\n❌ Evaluation failed: {results['error']}")
        sys.exit(1)
    
    print("\n✅ Evaluation complete!")


def cmd_info(args):
    """Show model information"""
    print("=" * 60)
    print("  MODEL INFORMATION")
    print("=" * 60)
    
    if not os.path.exists(args.model):
        print(f"❌ Model not found: {args.model}")
        sys.exit(1)
    
    from app.rl.inference import RLInferenceService
    
    # Load model
    service = RLInferenceService(args.model)
    info = service.get_model_info()
    
    print(f"\n📋 Model: {args.model}")
    print(f"   Loaded: {info.get('loaded', False)}")
    print(f"   Device: {info.get('device', 'N/A')}")
    print(f"   Policy: {info.get('policyType', 'N/A')}")
    print(f"   Observation Space: {info.get('observationSpace', 'N/A')}")
    print(f"   Action Space: {info.get('actionSpace', 'N/A')}")
    
    # File info
    file_size = os.path.getsize(args.model)
    print(f"\n📁 File size: {file_size / (1024*1024):.2f} MB")


def cmd_benchmark(args):
    """Benchmark inference performance"""
    print("=" * 60)
    print("  INFERENCE BENCHMARK")
    print("=" * 60)
    
    if not os.path.exists(args.model):
        print(f"❌ Model not found: {args.model}")
        sys.exit(1)
    
    import numpy as np
    import time
    from app.rl.inference import RLInferenceService
    
    # Load model
    print(f"\n📥 Loading model: {args.model}")
    service = RLInferenceService(args.model)
    
    if not service.is_ready():
        print("❌ Model failed to load")
        sys.exit(1)
    
    # Generate random observations
    n_iterations = args.iterations
    observations = np.random.rand(n_iterations, 63).astype(np.float32)
    
    # Warm-up
    print("\n🔥 Warming up...")
    for i in range(min(10, n_iterations)):
        service.predict(observations[i])
    
    # Benchmark
    print(f"\n⏱️ Running {n_iterations} inference iterations...")
    
    times = []
    for i in range(n_iterations):
        start = time.perf_counter()
        service.predict(observations[i])
        duration = (time.perf_counter() - start) * 1000  # ms
        times.append(duration)
    
    # Statistics
    avg_time = np.mean(times)
    std_time = np.std(times)
    min_time = np.min(times)
    max_time = np.max(times)
    p50 = np.percentile(times, 50)
    p95 = np.percentile(times, 95)
    p99 = np.percentile(times, 99)
    
    print(f"\n📊 Benchmark Results ({n_iterations} iterations):")
    print(f"   Mean:   {avg_time:.3f} ms ± {std_time:.3f}")
    print(f"   Min:    {min_time:.3f} ms")
    print(f"   Max:    {max_time:.3f} ms")
    print(f"   P50:    {p50:.3f} ms")
    print(f"   P95:    {p95:.3f} ms")
    print(f"   P99:    {p99:.3f} ms")
    
    # Performance check
    threshold = 100.0
    if avg_time < threshold:
        print(f"\n✅ PASS: Inference < {threshold}ms requirement")
    else:
        print(f"\n❌ FAIL: Inference exceeds {threshold}ms requirement")
        sys.exit(1)


def cmd_list(args):
    """List available models"""
    print("=" * 60)
    print("  AVAILABLE MODELS")
    print("=" * 60)
    
    models_dir = args.dir
    
    if not os.path.exists(models_dir):
        print(f"\n⚠️ Models directory not found: {models_dir}")
        return
    
    # Find all .zip files
    models = []
    for root, dirs, files in os.walk(models_dir):
        for file in files:
            if file.endswith('.zip'):
                path = os.path.join(root, file)
                size = os.path.getsize(path)
                mtime = os.path.getmtime(path)
                models.append({
                    'path': path,
                    'name': file,
                    'size': size,
                    'mtime': mtime
                })
    
    if not models:
        print(f"\n📭 No models found in {models_dir}")
        return
    
    # Sort by modification time (newest first)
    models.sort(key=lambda x: x['mtime'], reverse=True)
    
    print(f"\n📁 Found {len(models)} model(s) in {models_dir}:\n")
    
    import datetime
    for m in models:
        mtime_str = datetime.datetime.fromtimestamp(m['mtime']).strftime('%Y-%m-%d %H:%M')
        size_mb = m['size'] / (1024 * 1024)
        print(f"   📦 {m['name']}")
        print(f"      Path: {m['path']}")
        print(f"      Size: {size_mb:.2f} MB")
        print(f"      Modified: {mtime_str}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description='RL Agent Training & Evaluation for Traffic Signal Control',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Train new agent (1M timesteps, ~1-2 hours)
  python train_rl.py train --timesteps 1000000

  # Quick training for testing (10k timesteps, ~5 minutes)
  python train_rl.py train --quick

  # Continue training from checkpoint
  python train_rl.py continue --model models/checkpoint.zip --timesteps 100000

  # Evaluate trained model
  python train_rl.py eval --model models/ppo_traffic_final.zip --episodes 10

  # Benchmark inference performance
  python train_rl.py benchmark --model models/ppo_traffic_final.zip

  # Monitor training with TensorBoard
  tensorboard --logdir logs/tensorboard/
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Train command
    train_parser = subparsers.add_parser('train', help='Train new RL agent')
    train_parser.add_argument(
        '--timesteps', '-t',
        type=int,
        default=1_000_000,
        help='Total training timesteps (default: 1M)'
    )
    train_parser.add_argument(
        '--output', '-o',
        type=str,
        default='./models/ppo_traffic_final.zip',
        help='Output model path'
    )
    train_parser.add_argument(
        '--quick', '-q',
        action='store_true',
        help='Quick training mode (10k timesteps for testing)'
    )
    
    # Continue command
    continue_parser = subparsers.add_parser('continue', help='Continue training from checkpoint')
    continue_parser.add_argument(
        '--model', '-m',
        type=str,
        required=True,
        help='Path to checkpoint model'
    )
    continue_parser.add_argument(
        '--timesteps', '-t',
        type=int,
        default=100_000,
        help='Additional timesteps (default: 100k)'
    )
    continue_parser.add_argument(
        '--output', '-o',
        type=str,
        default=None,
        help='Output path (defaults to input model)'
    )
    
    # Eval command
    eval_parser = subparsers.add_parser('eval', help='Evaluate trained model')
    eval_parser.add_argument(
        '--model', '-m',
        type=str,
        required=True,
        help='Path to trained model'
    )
    eval_parser.add_argument(
        '--episodes', '-e',
        type=int,
        default=10,
        help='Number of evaluation episodes (default: 10)'
    )
    eval_parser.add_argument(
        '--stochastic', '-s',
        action='store_true',
        help='Use stochastic policy (default: deterministic)'
    )
    eval_parser.add_argument(
        '--render', '-r',
        action='store_true',
        help='Render environment during evaluation'
    )
    
    # Info command
    info_parser = subparsers.add_parser('info', help='Show model information')
    info_parser.add_argument(
        '--model', '-m',
        type=str,
        required=True,
        help='Path to model file'
    )
    
    # Benchmark command
    benchmark_parser = subparsers.add_parser('benchmark', help='Benchmark inference performance')
    benchmark_parser.add_argument(
        '--model', '-m',
        type=str,
        required=True,
        help='Path to model file'
    )
    benchmark_parser.add_argument(
        '--iterations', '-i',
        type=int,
        default=1000,
        help='Number of inference iterations (default: 1000)'
    )
    
    # List command
    list_parser = subparsers.add_parser('list', help='List available models')
    list_parser.add_argument(
        '--dir', '-d',
        type=str,
        default='./models',
        help='Models directory (default: ./models)'
    )
    
    args = parser.parse_args()
    
    if args.command == 'train':
        cmd_train(args)
    elif args.command == 'continue':
        cmd_continue(args)
    elif args.command == 'eval':
        cmd_eval(args)
    elif args.command == 'info':
        cmd_info(args)
    elif args.command == 'benchmark':
        cmd_benchmark(args)
    elif args.command == 'list':
        cmd_list(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()

