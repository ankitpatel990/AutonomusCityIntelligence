"""
RL Value Function Predictor
FRD-06: AI-Based Congestion Prediction - FR-03.1

Extracts congestion predictions from trained RL agent's value function.
The critic network (value function) implicitly learns to predict future
rewards, which correlates with future traffic states.

Part of the Autonomous City Traffic Intelligence System.
"""

import numpy as np
from typing import Dict, Optional, TYPE_CHECKING
from dataclasses import dataclass
import time

if TYPE_CHECKING:
    from stable_baselines3 import PPO


@dataclass
class RLValuePrediction:
    """Prediction from RL value function"""
    junction_id: str
    congestion_risk: float  # 0-100
    value_estimate: float
    confidence: float
    timestamp: float
    
    def to_dict(self) -> dict:
        return {
            'junctionId': self.junction_id,
            'congestionRisk': round(self.congestion_risk, 2),
            'valueEstimate': round(self.value_estimate, 2),
            'confidence': round(self.confidence, 2),
            'timestamp': self.timestamp
        }


class RLValueFunctionPredictor:
    """
    Extract predictions from RL agent value function
    
    The RL agent's critic (value function) V(s) estimates expected
    future rewards. Lower values indicate worse future states,
    which typically correlates with higher congestion.
    
    Usage:
        predictor = RLValueFunctionPredictor(rl_model)
        predictions = predictor.predict_congestion(observation)
    """
    
    def __init__(self, rl_model: 'PPO' = None):
        """
        Initialize RL value function predictor
        
        Args:
            rl_model: Trained stable-baselines3 PPO model
        """
        self.rl_model = rl_model
        self.value_net = None
        
        # Try to access value function
        if rl_model is not None:
            try:
                # For stable-baselines3 PPO
                if hasattr(rl_model, 'policy') and hasattr(rl_model.policy, 'value_net'):
                    self.value_net = rl_model.policy.value_net
                    print("✅ RL Value Function Predictor initialized with value network")
                else:
                    print("⚠️ Could not access value network from RL model")
            except Exception as e:
                print(f"⚠️ Error accessing RL model: {e}")
        else:
            print("ℹ️ RLValueFunctionPredictor initialized without model")
    
    def set_model(self, rl_model: 'PPO'):
        """
        Set or update the RL model
        
        Args:
            rl_model: Trained PPO model
        """
        self.rl_model = rl_model
        
        if hasattr(rl_model, 'policy') and hasattr(rl_model.policy, 'value_net'):
            self.value_net = rl_model.policy.value_net
            print("✅ RL model set with value network")
        else:
            self.value_net = None
            print("⚠️ Could not access value network from RL model")
    
    def is_ready(self) -> bool:
        """Check if predictor has a valid model"""
        return self.rl_model is not None
    
    def predict_congestion(self, observation: np.ndarray) -> Dict[str, RLValuePrediction]:
        """
        Predict future congestion using RL value function
        
        Args:
            observation: Current state observation (numpy array)
        
        Returns:
            Dict of junction_id -> RLValuePrediction
        """
        if not self.is_ready():
            return {}
        
        try:
            import torch
            
            # Get value estimate from the model
            with torch.no_grad():
                obs_tensor = torch.FloatTensor(observation).unsqueeze(0)
                
                if self.value_net is not None:
                    # Direct value network access
                    value_estimate = self.value_net(obs_tensor).item()
                else:
                    # Use predict_values method
                    value_estimate = self.rl_model.policy.predict_values(obs_tensor).item()
            
            # Map value to congestion risk
            # Lower value → worse future state → higher congestion
            overall_risk = self._value_to_congestion_risk(value_estimate)
            
            # Decompose into per-junction predictions
            predictions = self._decompose_prediction(observation, overall_risk, value_estimate)
            
            return predictions
            
        except Exception as e:
            print(f"⚠️ RL prediction failed: {e}")
            return {}
    
    def _value_to_congestion_risk(self, value: float) -> float:
        """
        Map value function output to congestion risk (0-100)
        
        Value typically ranges from -1000 to +500 depending on reward design.
        Lower value = higher congestion risk.
        
        Args:
            value: Value function estimate
        
        Returns:
            Congestion risk score (0-100)
        """
        # Normalize based on typical value ranges
        # This mapping should be calibrated based on actual reward design
        if value > 0:
            # Positive value indicates good state
            risk = max(0, 50 - value / 10)
        else:
            # Negative value indicates bad state
            risk = min(100, 50 + abs(value) / 20)
        
        return np.clip(risk, 0, 100)
    
    def _decompose_prediction(self, 
                              observation: np.ndarray, 
                              overall_risk: float,
                              value_estimate: float) -> Dict[str, RLValuePrediction]:
        """
        Decompose overall risk into per-junction predictions
        
        Uses observation structure to estimate per-junction risk.
        Assumes observation contains per-junction features.
        
        Args:
            observation: Full state observation
            overall_risk: Overall congestion risk
            value_estimate: Raw value estimate
        
        Returns:
            Dict of junction_id -> RLValuePrediction
        """
        predictions = {}
        current_time = time.time()
        
        # Assuming 9-junction grid (J-1 to J-9)
        # Each junction has 7 features in the observation
        # Structure: [density_n, density_e, density_s, density_w, phase, phase_time, ...]
        
        num_junctions = 9
        features_per_junction = 7
        
        try:
            for i in range(num_junctions):
                junction_id = f"J-{i + 1}"
                
                # Extract junction features
                start_idx = i * features_per_junction
                end_idx = start_idx + features_per_junction
                
                if end_idx <= len(observation):
                    junction_obs = observation[start_idx:end_idx]
                    
                    # Average density from the 4 directions (first 4 features)
                    if len(junction_obs) >= 4:
                        avg_density = np.mean(junction_obs[:4])
                        
                        # Combine with overall risk
                        # Higher local density = higher local risk
                        local_risk = (overall_risk * 0.5) + (avg_density * 0.5)
                        local_risk = np.clip(local_risk, 0, 100)
                    else:
                        local_risk = overall_risk
                else:
                    local_risk = overall_risk
                
                # Confidence based on model certainty
                confidence = 0.7 if abs(value_estimate) > 10 else 0.5
                
                predictions[junction_id] = RLValuePrediction(
                    junction_id=junction_id,
                    congestion_risk=float(local_risk),
                    value_estimate=float(value_estimate),
                    confidence=confidence,
                    timestamp=current_time
                )
        
        except Exception as e:
            print(f"⚠️ Error decomposing prediction: {e}")
            # Return at least overall prediction
            predictions['OVERALL'] = RLValuePrediction(
                junction_id='OVERALL',
                congestion_risk=float(overall_risk),
                value_estimate=float(value_estimate),
                confidence=0.5,
                timestamp=current_time
            )
        
        return predictions
    
    def get_statistics(self) -> dict:
        """Get predictor statistics"""
        return {
            'modelLoaded': self.is_ready(),
            'valueNetworkAvailable': self.value_net is not None,
            'timestamp': time.time()
        }


# Global RL predictor instance
_rl_predictor: Optional[RLValueFunctionPredictor] = None


def get_rl_predictor() -> Optional[RLValueFunctionPredictor]:
    """Get the global RLValueFunctionPredictor instance"""
    return _rl_predictor


def init_rl_predictor(rl_model=None) -> RLValueFunctionPredictor:
    """Initialize the global RLValueFunctionPredictor"""
    global _rl_predictor
    _rl_predictor = RLValueFunctionPredictor(rl_model)
    return _rl_predictor

