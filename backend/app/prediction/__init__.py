"""
Congestion Prediction Engine Module
FRD-06: AI-Based Congestion Prediction

This module provides predictive intelligence for traffic congestion,
forecasting density 3-10 minutes ahead for proactive traffic management.

Components:
- PredictionEngine: Main prediction engine with multiple algorithms
- CongestionClassifier: Classify congestion levels and generate alerts
- PredictionValidator: Validate predictions against live API data
- RLValueFunctionPredictor: Extract predictions from RL value function
- NeuralNetworkPredictor: Optional LSTM-based predictor

Algorithms:
- Moving Average (baseline)
- Linear Trend Extrapolation
- Exponential Smoothing (default)
- Neural Network (optional)

Part of the Autonomous City Traffic Intelligence System.
"""

from app.prediction.prediction_engine import (
    PredictionEngine,
    CongestionPrediction,
    get_prediction_engine,
    init_prediction_engine
)

from app.prediction.congestion_classifier import (
    CongestionClassifier,
    CongestionLevel,
    CongestionAlert,
    AlertSeverity,
    get_congestion_classifier,
    init_congestion_classifier
)

from app.prediction.prediction_validator import (
    PredictionValidator,
    PredictionComparison,
    get_prediction_validator,
    init_prediction_validator
)

from app.prediction.rl_value_predictor import (
    RLValueFunctionPredictor,
    RLValuePrediction,
    get_rl_predictor,
    init_rl_predictor
)

from app.prediction.nn_predictor import (
    NeuralNetworkPredictor,
    get_nn_predictor,
    init_nn_predictor,
    TORCH_AVAILABLE
)

from app.prediction.prediction_broadcast import (
    PredictionBroadcastService,
    get_broadcast_service,
    init_broadcast_service
)


__all__ = [
    # Main engine
    'PredictionEngine',
    'CongestionPrediction',
    'get_prediction_engine',
    'init_prediction_engine',
    
    # Classifier
    'CongestionClassifier',
    'CongestionLevel',
    'CongestionAlert',
    'AlertSeverity',
    'get_congestion_classifier',
    'init_congestion_classifier',
    
    # Validator
    'PredictionValidator',
    'PredictionComparison',
    'get_prediction_validator',
    'init_prediction_validator',
    
    # RL Predictor
    'RLValueFunctionPredictor',
    'RLValuePrediction',
    'get_rl_predictor',
    'init_rl_predictor',
    
    # NN Predictor
    'NeuralNetworkPredictor',
    'get_nn_predictor',
    'init_nn_predictor',
    'TORCH_AVAILABLE',
    
    # Broadcast Service
    'PredictionBroadcastService',
    'get_broadcast_service',
    'init_broadcast_service'
]
