"""
Prediction Engine - AI-Based Congestion Prediction
FRD-06: AI-Based Congestion Prediction

Predicts traffic density 3-10 minutes ahead using:
- Time-series analysis (moving average, trend)
- Exponential smoothing
- Optional: RL Value Function extraction
- Optional: Simple LSTM neural network

Part of the Autonomous City Traffic Intelligence System.
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from collections import deque
import time

from app.density.density_history import DensitySnapshot


@dataclass
class CongestionPrediction:
    """
    Prediction for a road segment
    
    Contains predicted density values for future time points
    with confidence scores and algorithm information.
    """
    road_id: str
    predicted_at: float
    predictions: List[Tuple[float, float]]  # [(timestamp, density), ...]
    confidence: float
    prediction_horizon: int  # minutes
    algorithm: str
    current_density: float = 0.0
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses"""
        return {
            'roadId': self.road_id,
            'predictedAt': self.predicted_at,
            'predictions': [
                {
                    'timestamp': ts,
                    'minutesAhead': int((ts - self.predicted_at) / 60),
                    'predictedDensity': round(density, 2)
                }
                for ts, density in self.predictions
            ],
            'confidence': round(self.confidence, 2),
            'predictionHorizon': self.prediction_horizon,
            'algorithm': self.algorithm,
            'currentDensity': round(self.current_density, 2)
        }


class PredictionEngine:
    """
    AI-based congestion prediction engine
    
    Predicts traffic density 3-10 minutes ahead using:
    - Time-series analysis (moving average, trend)
    - Historical patterns
    - Optional: Simple neural network
    
    Algorithms (selectable):
    1. Moving Average (baseline)
    2. Linear Trend Extrapolation
    3. Exponential Smoothing (default)
    4. Simple LSTM (optional, if time permits)
    
    Usage:
        engine = PredictionEngine(config={'algorithm': 'exponential_smoothing'})
        engine.record_density('ROAD-1', 45.0, 12)
        prediction = engine.predict('ROAD-1')
    """
    
    # Algorithm constants
    ALGORITHM_MOVING_AVERAGE = 'moving_average'
    ALGORITHM_LINEAR_TREND = 'linear_trend'
    ALGORITHM_EXPONENTIAL_SMOOTHING = 'exponential_smoothing'
    ALGORITHM_NEURAL_NETWORK = 'neural_network'
    
    def __init__(self, config: dict = None):
        """
        Initialize prediction engine
        
        Args:
            config: Configuration dict with options:
                - predictionHorizon: Minutes to predict ahead (default: 10)
                - predictionInterval: Interval between predictions (default: 1 min)
                - updateFrequency: Seconds between prediction updates (default: 30)
                - algorithm: Algorithm to use (default: exponential_smoothing)
        """
        self.config = config or {}
        
        # Prediction settings
        self.prediction_horizon = self.config.get('predictionHorizon', 10)  # minutes
        self.prediction_interval = self.config.get('predictionInterval', 1)  # minutes
        self.update_frequency = self.config.get('updateFrequency', 30)  # seconds
        
        # Algorithm selection
        self.algorithm = self.config.get('algorithm', self.ALGORITHM_EXPONENTIAL_SMOOTHING)
        
        # Algorithm-specific settings
        self.algorithms_config = self.config.get('algorithms', {})
        
        # Historical data storage
        # road_id -> deque of DensitySnapshot-like data (last 30 minutes)
        self.history_length = 30 * 60  # 30 minutes in seconds
        self.density_history: Dict[str, deque] = {}
        
        # Cached predictions
        self.predictions_cache: Dict[str, CongestionPrediction] = {}
        self.last_prediction_time: float = 0
        
        # Statistics
        self.total_predictions = 0
        self.prediction_accuracy: List[float] = []  # Track accuracy over time
        
        # Optional: Neural network predictor
        self._nn_predictor = None
        
        print("✅ Prediction Engine initialized")
        print(f"   Algorithm: {self.algorithm}")
        print(f"   Horizon: {self.prediction_horizon} minutes")
        print(f"   Update frequency: {self.update_frequency}s")
    
    def record_density(self, 
                       road_id: str, 
                       density_score: float, 
                       vehicle_count: int):
        """
        Record current density measurement
        
        Args:
            road_id: Road segment ID
            density_score: Current density score (0-100)
            vehicle_count: Number of vehicles
        """
        snapshot = {
            'timestamp': time.time(),
            'road_id': road_id,
            'density_score': density_score,
            'vehicle_count': vehicle_count
        }
        
        # Initialize deque if needed
        if road_id not in self.density_history:
            self.density_history[road_id] = deque(maxlen=1000)  # Keep last 1000 samples
        
        # Add snapshot
        self.density_history[road_id].append(snapshot)
        
        # Clean old data (older than history_length)
        self._clean_old_data(road_id)
    
    def record_from_snapshot(self, snapshot: DensitySnapshot):
        """
        Record density from DensitySnapshot object
        
        Args:
            snapshot: DensitySnapshot from density tracker
        """
        self.record_density(
            road_id=snapshot.road_id,
            density_score=snapshot.density_score,
            vehicle_count=snapshot.vehicle_count
        )
    
    def _clean_old_data(self, road_id: str):
        """Remove data older than history_length"""
        if road_id not in self.density_history:
            return
        
        current_time = time.time()
        cutoff_time = current_time - self.history_length
        
        history = self.density_history[road_id]
        
        # Remove old snapshots from left
        while history and history[0]['timestamp'] < cutoff_time:
            history.popleft()
    
    def predict(self, road_id: str, force: bool = False) -> Optional[CongestionPrediction]:
        """
        Predict congestion for a road segment
        
        Args:
            road_id: Road segment ID
            force: Force prediction even if cache is fresh
        
        Returns:
            CongestionPrediction or None if insufficient data
        """
        current_time = time.time()
        
        # Check if update needed (unless forced)
        if not force:
            if (road_id in self.predictions_cache and 
                current_time - self.last_prediction_time < self.update_frequency):
                return self.predictions_cache.get(road_id)
        
        # Check if we have enough historical data
        if road_id not in self.density_history:
            return None
        
        history = list(self.density_history[road_id])
        if len(history) < 10:  # Need at least 10 samples
            return None
        
        # Get current density
        current_density = history[-1]['density_score'] if history else 0.0
        
        # Generate prediction based on algorithm
        if self.algorithm == self.ALGORITHM_MOVING_AVERAGE:
            prediction = self._predict_moving_average(road_id, history, current_density)
        elif self.algorithm == self.ALGORITHM_LINEAR_TREND:
            prediction = self._predict_linear_trend(road_id, history, current_density)
        elif self.algorithm == self.ALGORITHM_EXPONENTIAL_SMOOTHING:
            prediction = self._predict_exponential_smoothing(road_id, history, current_density)
        elif self.algorithm == self.ALGORITHM_NEURAL_NETWORK:
            prediction = self._predict_neural_network(road_id, history, current_density)
        else:
            # Default to exponential smoothing
            prediction = self._predict_exponential_smoothing(road_id, history, current_density)
        
        # Cache prediction
        self.predictions_cache[road_id] = prediction
        self.total_predictions += 1
        
        return prediction
    
    def predict_all_roads(self, road_ids: List[str] = None) -> Dict[str, CongestionPrediction]:
        """
        Predict congestion for all roads or specified list
        
        Args:
            road_ids: List of road segment IDs (None = all tracked roads)
        
        Returns:
            Dict of road_id -> CongestionPrediction
        """
        # Use all tracked roads if none specified
        if road_ids is None:
            road_ids = list(self.density_history.keys())
        
        predictions = {}
        
        for road_id in road_ids:
            pred = self.predict(road_id)
            if pred:
                predictions[road_id] = pred
        
        # Update last prediction time
        self.last_prediction_time = time.time()
        
        return predictions
    
    def _predict_moving_average(self, 
                                 road_id: str, 
                                 history: List[dict],
                                 current_density: float) -> CongestionPrediction:
        """
        Predict using moving average (baseline)
        
        Simple assumption: future will be average of recent past
        """
        # Get window size from config
        window_size = self.algorithms_config.get('moving_average', {}).get('windowSize', 10)
        window_size = min(window_size, len(history))
        
        recent = history[-window_size:]
        
        # Calculate average density
        avg_density = np.mean([s['density_score'] for s in recent])
        
        # Generate predictions (flat line at average)
        current_time = time.time()
        predictions = []
        
        for i in range(self.prediction_horizon):
            future_time = current_time + ((i + 1) * 60)  # i+1 minutes ahead
            predictions.append((future_time, float(avg_density)))
        
        return CongestionPrediction(
            road_id=road_id,
            predicted_at=current_time,
            predictions=predictions,
            confidence=0.6,  # Low confidence for simple average
            prediction_horizon=self.prediction_horizon,
            algorithm=self.ALGORITHM_MOVING_AVERAGE,
            current_density=current_density
        )
    
    def _predict_linear_trend(self,
                              road_id: str,
                              history: List[dict],
                              current_density: float) -> CongestionPrediction:
        """
        Predict using linear trend extrapolation
        
        Fits a line to recent data and extrapolates
        """
        # Get window size from config
        window_size = self.algorithms_config.get('linear_trend', {}).get('windowSize', 20)
        window_size = min(window_size, len(history))
        
        recent = history[-window_size:]
        
        # Extract timestamps and densities
        timestamps = np.array([s['timestamp'] for s in recent])
        densities = np.array([s['density_score'] for s in recent])
        
        # Normalize timestamps (relative to first)
        timestamps_norm = timestamps - timestamps[0]
        time_range = timestamps_norm[-1] if len(timestamps_norm) > 0 else 1
        
        # Avoid division by zero by normalizing time range
        if time_range > 0:
            timestamps_norm = timestamps_norm / time_range
        
        # Fit linear regression
        if len(timestamps_norm) >= 2 and np.std(timestamps_norm) > 1e-10:
            try:
                coeffs = np.polyfit(timestamps_norm, densities, 1)  # Linear fit
                slope, intercept = float(coeffs[0]), float(coeffs[1])
            except np.linalg.LinAlgError:
                # Fall back to simple calculation
                slope = 0.0
                intercept = float(np.mean(densities))
        else:
            slope, intercept = 0.0, float(np.mean(densities))
        
        # Generate predictions
        current_time = time.time()
        predictions = []
        
        # Slope is per normalized time unit, so we need to scale predictions
        for i in range(self.prediction_horizon):
            future_time = current_time + ((i + 1) * 60)
            
            # Use simple extrapolation from current trend
            # slope represents change over normalized window
            time_factor = (i + 1) / self.prediction_horizon
            predicted_density = densities[-1] + (slope * time_factor)
            
            # Clamp to valid range
            predicted_density = max(0.0, min(100.0, predicted_density))
            
            predictions.append((future_time, float(predicted_density)))
        
        # Confidence based on trend stability
        confidence = 0.7 if abs(slope) < 0.1 else 0.5
        
        return CongestionPrediction(
            road_id=road_id,
            predicted_at=current_time,
            predictions=predictions,
            confidence=confidence,
            prediction_horizon=self.prediction_horizon,
            algorithm=self.ALGORITHM_LINEAR_TREND,
            current_density=current_density
        )
    
    def _predict_exponential_smoothing(self,
                                        road_id: str,
                                        history: List[dict],
                                        current_density: float) -> CongestionPrediction:
        """
        Predict using exponential smoothing
        
        Weights recent observations more heavily
        """
        # Get smoothing factor from config
        alpha = self.algorithms_config.get('exponential_smoothing', {}).get('alpha', 0.3)
        
        # Get densities
        densities = [s['density_score'] for s in history]
        
        # Exponential smoothing
        smoothed = densities[0]
        for density in densities[1:]:
            smoothed = alpha * density + (1 - alpha) * smoothed
        
        # Calculate trend
        if len(densities) >= 5:
            trend = densities[-1] - densities[-5]
        elif len(densities) >= 2:
            trend = densities[-1] - densities[-2]
        else:
            trend = 0.0
        
        # Generate predictions
        current_time = time.time()
        predictions = []
        
        for i in range(self.prediction_horizon):
            future_time = current_time + ((i + 1) * 60)
            # Apply trend with dampening
            predicted_density = smoothed + (trend * (i + 1) * 0.5)
            
            # Clamp to valid range
            predicted_density = max(0.0, min(100.0, predicted_density))
            
            predictions.append((future_time, float(predicted_density)))
        
        return CongestionPrediction(
            road_id=road_id,
            predicted_at=current_time,
            predictions=predictions,
            confidence=0.75,
            prediction_horizon=self.prediction_horizon,
            algorithm=self.ALGORITHM_EXPONENTIAL_SMOOTHING,
            current_density=current_density
        )
    
    def _predict_neural_network(self,
                                 road_id: str,
                                 history: List[dict],
                                 current_density: float) -> CongestionPrediction:
        """
        Predict using neural network (if available)
        
        Falls back to exponential smoothing if NN not loaded
        """
        if self._nn_predictor is None:
            # Fall back to exponential smoothing
            return self._predict_exponential_smoothing(road_id, history, current_density)
        
        try:
            # Extract density values
            densities = [s['density_score'] for s in history]
            
            # Get predictions from NN
            future_values = self._nn_predictor.predict(densities)
            
            # Format predictions
            current_time = time.time()
            predictions = []
            
            for i, density in enumerate(future_values[:self.prediction_horizon]):
                future_time = current_time + ((i + 1) * 60)
                predicted_density = max(0.0, min(100.0, float(density)))
                predictions.append((future_time, predicted_density))
            
            return CongestionPrediction(
                road_id=road_id,
                predicted_at=current_time,
                predictions=predictions,
                confidence=0.80,  # Higher confidence for NN
                prediction_horizon=len(predictions),
                algorithm=self.ALGORITHM_NEURAL_NETWORK,
                current_density=current_density
            )
        except Exception as e:
            print(f"⚠️ NN prediction failed for {road_id}: {e}")
            return self._predict_exponential_smoothing(road_id, history, current_density)
    
    def set_neural_network_predictor(self, nn_predictor):
        """
        Set the neural network predictor
        
        Args:
            nn_predictor: NeuralNetworkPredictor instance
        """
        self._nn_predictor = nn_predictor
        print("✅ Neural network predictor set")
    
    def set_algorithm(self, algorithm: str):
        """
        Change the prediction algorithm
        
        Args:
            algorithm: Algorithm name
        """
        valid_algorithms = [
            self.ALGORITHM_MOVING_AVERAGE,
            self.ALGORITHM_LINEAR_TREND,
            self.ALGORITHM_EXPONENTIAL_SMOOTHING,
            self.ALGORITHM_NEURAL_NETWORK
        ]
        
        if algorithm not in valid_algorithms:
            raise ValueError(f"Invalid algorithm: {algorithm}. Valid: {valid_algorithms}")
        
        self.algorithm = algorithm
        self.predictions_cache.clear()  # Clear cache on algorithm change
        print(f"✅ Algorithm changed to: {algorithm}")
    
    def get_statistics(self) -> dict:
        """Get prediction engine statistics"""
        avg_history = 0.0
        if self.density_history:
            avg_history = np.mean([len(h) for h in self.density_history.values()])
        
        return {
            'algorithm': self.algorithm,
            'totalPredictions': self.total_predictions,
            'trackedRoads': len(self.density_history),
            'avgHistoryLength': round(avg_history, 1),
            'predictionHorizon': self.prediction_horizon,
            'updateFrequency': self.update_frequency,
            'cacheSize': len(self.predictions_cache),
            'lastPredictionTime': self.last_prediction_time
        }
    
    def clear_cache(self):
        """Clear prediction cache"""
        self.predictions_cache.clear()
        self.last_prediction_time = 0
    
    def clear_history(self, road_id: str = None):
        """
        Clear history for a road or all roads
        
        Args:
            road_id: Road to clear (None = all roads)
        """
        if road_id:
            if road_id in self.density_history:
                self.density_history[road_id].clear()
        else:
            self.density_history.clear()
        
        self.clear_cache()


# Global prediction engine instance
_prediction_engine: Optional[PredictionEngine] = None


def get_prediction_engine() -> Optional[PredictionEngine]:
    """Get the global PredictionEngine instance"""
    return _prediction_engine


def init_prediction_engine(config: dict = None) -> PredictionEngine:
    """Initialize the global PredictionEngine with config"""
    global _prediction_engine
    _prediction_engine = PredictionEngine(config)
    return _prediction_engine

