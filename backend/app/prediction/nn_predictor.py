"""
Neural Network Predictor (Optional)
FRD-06: AI-Based Congestion Prediction - FR-06.6 (Optional)

Simple LSTM neural network for traffic density prediction.
Uses PyTorch for the neural network implementation.

This is an optional enhancement beyond the baseline algorithms.
Falls back gracefully if PyTorch is not available.

Part of the Autonomous City Traffic Intelligence System.
"""

from typing import List, Optional, Tuple
import numpy as np
import os

# Optional PyTorch import
try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    print("ℹ️ PyTorch not available. Neural network predictor disabled.")


if TORCH_AVAILABLE:
    class SimpleLSTM(nn.Module):
        """
        Simple LSTM for traffic prediction
        
        Architecture:
        - Input: Sequence of density values
        - LSTM layers: 2 layers, 32 hidden units
        - Output: Future density values
        
        Input shape: (batch, seq_len, 1)
        Output shape: (batch, output_size)
        """
        
        def __init__(self, 
                     input_size: int = 1, 
                     hidden_size: int = 32, 
                     num_layers: int = 2, 
                     output_size: int = 10,
                     dropout: float = 0.1):
            super(SimpleLSTM, self).__init__()
            
            self.hidden_size = hidden_size
            self.num_layers = num_layers
            
            # LSTM layer
            self.lstm = nn.LSTM(
                input_size=input_size,
                hidden_size=hidden_size,
                num_layers=num_layers,
                batch_first=True,
                dropout=dropout if num_layers > 1 else 0
            )
            
            # Output layer
            self.fc = nn.Linear(hidden_size, output_size)
            
            # Activation for clamping output
            self.sigmoid = nn.Sigmoid()
        
        def forward(self, x: torch.Tensor) -> torch.Tensor:
            """
            Forward pass
            
            Args:
                x: Input tensor (batch, seq_len, input_size)
            
            Returns:
                Predictions tensor (batch, output_size)
            """
            # LSTM forward pass
            lstm_out, _ = self.lstm(x)
            
            # Use last output
            last_output = lstm_out[:, -1, :]
            
            # Predict next N timesteps
            predictions = self.fc(last_output)
            
            # Scale to 0-100 range
            predictions = self.sigmoid(predictions) * 100
            
            return predictions


class NeuralNetworkPredictor:
    """
    Neural network-based traffic predictor
    
    Uses LSTM to learn traffic patterns and predict future density.
    Supports online learning to continuously improve predictions.
    
    Usage:
        predictor = NeuralNetworkPredictor()
        predictions = predictor.predict(density_history)
        predictor.update_online(history, actual_future)
    """
    
    def __init__(self, config: dict = None):
        """
        Initialize NN predictor
        
        Args:
            config: Configuration with options:
                - sequenceLength: Input sequence length (default: 20)
                - predictionHorizon: Output prediction length (default: 10)
                - hiddenSize: LSTM hidden units (default: 32)
                - numLayers: LSTM layers (default: 2)
                - learningRate: Learning rate (default: 0.001)
        """
        self.config = config or {}
        
        # Model parameters
        self.sequence_length = self.config.get('sequenceLength', 20)
        self.prediction_horizon = self.config.get('predictionHorizon', 10)
        self.hidden_size = self.config.get('hiddenSize', 32)
        self.num_layers = self.config.get('numLayers', 2)
        self.learning_rate = self.config.get('learningRate', 0.001)
        
        # Model and training components
        self.model = None
        self.optimizer = None
        self.criterion = None
        self.device = None
        
        # Statistics
        self.total_predictions = 0
        self.total_updates = 0
        self.training_losses: List[float] = []
        
        # Initialize if PyTorch available
        if TORCH_AVAILABLE:
            self._initialize_model()
        else:
            print("⚠️ Neural Network Predictor: PyTorch not available")
    
    def _initialize_model(self):
        """Initialize PyTorch model and training components"""
        try:
            # Set device
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            
            # Create model
            self.model = SimpleLSTM(
                input_size=1,
                hidden_size=self.hidden_size,
                num_layers=self.num_layers,
                output_size=self.prediction_horizon
            ).to(self.device)
            
            # Training components
            self.optimizer = torch.optim.Adam(
                self.model.parameters(), 
                lr=self.learning_rate
            )
            self.criterion = nn.MSELoss()
            
            print("✅ Neural Network Predictor initialized")
            print(f"   Device: {self.device}")
            print(f"   Sequence length: {self.sequence_length}")
            print(f"   Prediction horizon: {self.prediction_horizon}")
            
        except Exception as e:
            print(f"⚠️ Failed to initialize NN model: {e}")
            self.model = None
    
    def is_available(self) -> bool:
        """Check if NN predictor is available"""
        return TORCH_AVAILABLE and self.model is not None
    
    def predict(self, history: List[float]) -> List[float]:
        """
        Predict future density values
        
        Args:
            history: List of historical density values
        
        Returns:
            List of predicted future density values
        """
        if not self.is_available():
            # Return flat prediction as fallback
            last_value = history[-1] if history else 50.0
            return [last_value] * self.prediction_horizon
        
        if len(history) < self.sequence_length:
            # Pad with first value if not enough history
            padding = [history[0]] * (self.sequence_length - len(history))
            history = padding + list(history)
        
        try:
            # Prepare input
            sequence = history[-self.sequence_length:]
            x = torch.tensor(sequence, dtype=torch.float32)
            x = x.unsqueeze(0).unsqueeze(-1).to(self.device)  # (1, seq_len, 1)
            
            # Predict
            self.model.eval()
            with torch.no_grad():
                predictions = self.model(x)
            
            self.total_predictions += 1
            
            # Convert to list
            return predictions.squeeze().cpu().tolist()
            
        except Exception as e:
            print(f"⚠️ NN prediction failed: {e}")
            last_value = history[-1] if history else 50.0
            return [last_value] * self.prediction_horizon
    
    def update_online(self, history: List[float], actual_future: List[float]) -> float:
        """
        Online learning - update model with new data
        
        Args:
            history: Historical sequence
            actual_future: Actual future values (for training)
        
        Returns:
            Training loss
        """
        if not self.is_available():
            return 0.0
        
        if len(history) < self.sequence_length:
            return 0.0
        
        if len(actual_future) < self.prediction_horizon:
            # Pad with last value
            actual_future = list(actual_future) + [actual_future[-1]] * (self.prediction_horizon - len(actual_future))
        
        try:
            # Prepare training data
            sequence = history[-self.sequence_length:]
            x = torch.tensor(sequence, dtype=torch.float32)
            x = x.unsqueeze(0).unsqueeze(-1).to(self.device)
            
            y = torch.tensor(actual_future[:self.prediction_horizon], dtype=torch.float32)
            y = y.unsqueeze(0).to(self.device)
            
            # Train step
            self.model.train()
            self.optimizer.zero_grad()
            
            predictions = self.model(x)
            loss = self.criterion(predictions, y)
            
            loss.backward()
            self.optimizer.step()
            
            loss_value = loss.item()
            self.training_losses.append(loss_value)
            self.total_updates += 1
            
            # Keep only recent losses
            if len(self.training_losses) > 1000:
                self.training_losses = self.training_losses[-1000:]
            
            return loss_value
            
        except Exception as e:
            print(f"⚠️ Online update failed: {e}")
            return 0.0
    
    def save_model(self, path: str):
        """
        Save model to disk
        
        Args:
            path: File path for model
        """
        if not self.is_available():
            print("⚠️ Cannot save - model not available")
            return
        
        try:
            torch.save({
                'model_state_dict': self.model.state_dict(),
                'optimizer_state_dict': self.optimizer.state_dict(),
                'config': self.config,
                'total_predictions': self.total_predictions,
                'total_updates': self.total_updates
            }, path)
            print(f"✅ Model saved to {path}")
        except Exception as e:
            print(f"⚠️ Failed to save model: {e}")
    
    def load_model(self, path: str) -> bool:
        """
        Load model from disk
        
        Args:
            path: File path to load from
        
        Returns:
            True if loaded successfully
        """
        if not TORCH_AVAILABLE:
            print("⚠️ Cannot load - PyTorch not available")
            return False
        
        if not os.path.exists(path):
            print(f"⚠️ Model file not found: {path}")
            return False
        
        try:
            checkpoint = torch.load(path, map_location=self.device)
            
            self.model.load_state_dict(checkpoint['model_state_dict'])
            self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
            self.total_predictions = checkpoint.get('total_predictions', 0)
            self.total_updates = checkpoint.get('total_updates', 0)
            
            print(f"✅ Model loaded from {path}")
            return True
            
        except Exception as e:
            print(f"⚠️ Failed to load model: {e}")
            return False
    
    def get_statistics(self) -> dict:
        """Get predictor statistics"""
        avg_loss = 0.0
        if self.training_losses:
            avg_loss = sum(self.training_losses[-100:]) / min(100, len(self.training_losses))
        
        return {
            'available': self.is_available(),
            'device': str(self.device) if self.device else 'N/A',
            'sequenceLength': self.sequence_length,
            'predictionHorizon': self.prediction_horizon,
            'totalPredictions': self.total_predictions,
            'totalUpdates': self.total_updates,
            'recentAvgLoss': round(avg_loss, 4) if avg_loss else None,
            'pytorchAvailable': TORCH_AVAILABLE
        }


# Global NN predictor instance
_nn_predictor: Optional[NeuralNetworkPredictor] = None


def get_nn_predictor() -> Optional[NeuralNetworkPredictor]:
    """Get the global NeuralNetworkPredictor instance"""
    return _nn_predictor


def init_nn_predictor(config: dict = None) -> NeuralNetworkPredictor:
    """Initialize the global NeuralNetworkPredictor"""
    global _nn_predictor
    _nn_predictor = NeuralNetworkPredictor(config)
    return _nn_predictor

