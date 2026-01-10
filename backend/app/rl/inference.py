"""
RL Model Inference Service

Loads trained PPO model and provides fast inference for real-time decision-making.
Implements FRD-04 FR-04.4: Model loading & inference.

Performance requirement: < 100ms inference time.

Usage:
    service = RLInferenceService('./models/ppo_traffic_final.zip')
    actions, _ = service.predict(observation)
"""

import os
import time
import numpy as np
from typing import Tuple, Optional, Dict, Any

try:
    from stable_baselines3 import PPO
    SB3_AVAILABLE = True
except ImportError:
    SB3_AVAILABLE = False


class RLInferenceService:
    """
    RL Model Inference Service
    
    Loads trained PPO model and provides fast inference
    for real-time decision-making in the agent loop.
    
    Features:
    - Model loading and caching
    - Fast inference (< 100ms)
    - Statistics tracking
    - Model hot-reloading
    
    Usage:
        service = RLInferenceService('./models/ppo_traffic_final.zip')
        actions, states = service.predict(observation)
    """
    
    def __init__(self, model_path: str = None):
        """
        Initialize inference service
        
        Args:
            model_path: Path to trained model (optional, can load later)
        """
        self.model: Optional['PPO'] = None
        self.model_path: Optional[str] = None
        
        # Statistics
        self.inference_count = 0
        self.total_inference_time = 0.0
        self.max_inference_time = 0.0
        self.slow_inference_count = 0  # > 100ms
        
        # Performance threshold (ms)
        self.performance_threshold = 100.0
        
        # Auto-load model if path provided
        if model_path:
            self.load_model(model_path)
    
    def load_model(self, model_path: str) -> bool:
        """
        Load trained PPO model
        
        Args:
            model_path: Path to .zip model file
        
        Returns:
            True if loaded successfully, False otherwise
        """
        if not SB3_AVAILABLE:
            print("[ERROR] stable-baselines3 not available")
            return False
        
        if not os.path.exists(model_path):
            print(f"[ERROR] Model not found: {model_path}")
            return False
        
        print(f"[LOAD] Loading RL model from: {model_path}")
        
        start_time = time.time()
        
        try:
            self.model = PPO.load(model_path)
            load_time = time.time() - start_time
            
            self.model_path = model_path
            
            # Reset statistics
            self._reset_stats()
            
            print(f"[OK] Model loaded in {load_time:.2f}s")
            print(f"   Policy: {type(self.model.policy).__name__}")
            print(f"   Device: {self.model.device}")
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to load model: {e}")
            return False
    
    def predict(self, 
                observation: np.ndarray, 
                deterministic: bool = True) -> Tuple[np.ndarray, Optional[Tuple]]:
        """
        Run inference on observation
        
        Args:
            observation: State observation (63-dim vector for 9 junctions x 7 features)
            deterministic: Use deterministic policy (True for production)
        
        Returns:
            actions: Action array (9 values, one per junction, 0-3 for N/E/S/W)
            states: Optional policy states (for recurrent policies)
        
        Raises:
            RuntimeError: If model not loaded
            ValueError: If observation shape is invalid
        """
        if self.model is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")
        
        # Validate observation shape
        expected_shape = (63,)
        if observation.shape != expected_shape:
            # Try to reshape or pad
            if len(observation.flatten()) == 63:
                observation = observation.reshape(expected_shape)
            else:
                raise ValueError(f"Invalid observation shape: {observation.shape}. Expected {expected_shape}")
        
        # Ensure correct dtype
        if observation.dtype != np.float32:
            observation = observation.astype(np.float32)
        
        # Run inference with timing
        start_time = time.time()
        
        actions, states = self.model.predict(
            observation,
            deterministic=deterministic
        )
        
        inference_time = (time.time() - start_time) * 1000  # ms
        
        # Track statistics
        self.inference_count += 1
        self.total_inference_time += inference_time
        self.max_inference_time = max(self.max_inference_time, inference_time)
        
        if inference_time > self.performance_threshold:
            self.slow_inference_count += 1
            print(f"[WARN] Slow inference: {inference_time:.1f}ms (threshold: {self.performance_threshold}ms)")
        
        return actions, states
    
    def predict_batch(self, 
                      observations: np.ndarray,
                      deterministic: bool = True) -> Tuple[np.ndarray, Optional[Tuple]]:
        """
        Run batch inference on multiple observations
        
        Args:
            observations: Batch of observations (N, 63)
            deterministic: Use deterministic policy
        
        Returns:
            actions: Batch of actions (N, 9)
            states: Optional policy states
        """
        if self.model is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")
        
        # Ensure correct shape
        if len(observations.shape) == 1:
            observations = observations.reshape(1, -1)
        
        return self.model.predict(observations, deterministic=deterministic)
    
    def get_action_for_state(self, state_dict: dict) -> Dict[str, int]:
        """
        Convenience method: Get actions from state dictionary
        
        Args:
            state_dict: State dictionary with junction densities
        
        Returns:
            Dictionary mapping junction_id to action (0-3)
        """
        # Convert state dict to observation
        observation = self._state_to_observation(state_dict)
        
        # Get actions
        actions, _ = self.predict(observation)
        
        # Map to junction IDs
        junction_ids = state_dict.get('junction_ids', [f'J-{i+1}' for i in range(9)])
        
        return {jid: int(actions[i]) for i, jid in enumerate(junction_ids) if i < len(actions)}
    
    def _state_to_observation(self, state_dict: dict) -> np.ndarray:
        """Convert state dictionary to observation vector"""
        observation = []
        
        junction_densities = state_dict.get('junction_densities', {})
        junction_ids = sorted(junction_densities.keys()) if junction_densities else []
        
        # Pad to 9 junctions
        for i in range(9):
            if i < len(junction_ids):
                jid = junction_ids[i]
                densities = junction_densities[jid]
                
                # Directional densities (normalized)
                observation.append(min(densities.get('N', 0) / 100.0, 1.0))
                observation.append(min(densities.get('E', 0) / 100.0, 1.0))
                observation.append(min(densities.get('S', 0) / 100.0, 1.0))
                observation.append(min(densities.get('W', 0) / 100.0, 1.0))
                
                # Waiting time (normalized)
                observation.append(0.0)  # Placeholder
                
                # Signal state (normalized)
                observation.append(0.0)  # Placeholder
                
                # Vehicle count (normalized)
                observation.append(min(densities.get('total', 0) / 50.0, 1.0))
            else:
                observation.extend([0.0] * 7)
        
        return np.array(observation, dtype=np.float32)
    
    def _reset_stats(self):
        """Reset inference statistics"""
        self.inference_count = 0
        self.total_inference_time = 0.0
        self.max_inference_time = 0.0
        self.slow_inference_count = 0
    
    def get_statistics(self) -> dict:
        """Get inference statistics"""
        avg_time = (
            self.total_inference_time / self.inference_count 
            if self.inference_count > 0 else 0.0
        )
        
        return {
            'modelPath': self.model_path,
            'modelLoaded': self.model is not None,
            'inferenceCount': self.inference_count,
            'avgInferenceTime': round(avg_time, 2),
            'maxInferenceTime': round(self.max_inference_time, 2),
            'slowInferenceCount': self.slow_inference_count,
            'performanceThreshold': self.performance_threshold,
            'device': str(self.model.device) if self.model else None
        }
    
    def reload_model(self):
        """Reload model from disk (e.g., after retraining)"""
        if not self.model_path:
            raise RuntimeError("No model path set")
        
        print("[RELOAD] Reloading model...")
        self.load_model(self.model_path)
    
    def is_ready(self) -> bool:
        """Check if model is loaded and ready"""
        return self.model is not None
    
    def get_model_info(self) -> dict:
        """Get information about loaded model"""
        if not self.model:
            return {'loaded': False}
        
        return {
            'loaded': True,
            'path': self.model_path,
            'device': str(self.model.device),
            'policyType': type(self.model.policy).__name__,
            'observationSpace': str(self.model.observation_space),
            'actionSpace': str(self.model.action_space)
        }


# ============================================
# Global Inference Service Instance
# ============================================

_inference_service: Optional[RLInferenceService] = None


def get_inference_service() -> RLInferenceService:
    """
    Get global inference service instance
    
    Creates service if not exists, attempts to load default model.
    """
    global _inference_service
    
    if _inference_service is None:
        _inference_service = RLInferenceService()
        
        # Try to load default model
        default_model_path = './models/ppo_traffic_final.zip'
        
        if os.path.exists(default_model_path):
            _inference_service.load_model(default_model_path)
        else:
            print("[WARN] No default model found at ./models/ppo_traffic_final.zip")
            print("   RL inference will not be available until model is loaded.")
    
    return _inference_service


def set_inference_service(service: RLInferenceService):
    """Set global inference service"""
    global _inference_service
    _inference_service = service


def init_inference_service(model_path: str = None) -> RLInferenceService:
    """
    Initialize global inference service with model
    
    Args:
        model_path: Path to model file
    
    Returns:
        Initialized inference service
    """
    global _inference_service
    
    _inference_service = RLInferenceService(model_path)
    return _inference_service
