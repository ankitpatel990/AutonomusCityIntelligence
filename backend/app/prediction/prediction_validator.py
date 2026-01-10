"""
Prediction Validator - Live API Validation
FRD-06: AI-Based Congestion Prediction - FR-03.5, FR-03.6

Validates predictions against live TomTom API data to track accuracy.
Compares predicted congestion with actual API data (ground truth).

Part of the Autonomous City Traffic Intelligence System.
"""

from typing import Dict, List, Optional, TYPE_CHECKING
from dataclasses import dataclass, field
import time
import numpy as np

if TYPE_CHECKING:
    from app.prediction.prediction_engine import CongestionPrediction


@dataclass
class PredictionComparison:
    """Single comparison between prediction and actual"""
    road_id: str
    road_name: str
    timestamp: float
    prediction_time: float
    time_ahead: float  # How far ahead was this prediction made
    
    predicted_density: float
    actual_density: float
    absolute_error: float
    relative_error: float
    
    predicted_congestion: str
    actual_congestion: str
    correct_classification: bool
    
    confidence: float
    data_source: str
    
    def to_dict(self) -> dict:
        return {
            'roadId': self.road_id,
            'roadName': self.road_name,
            'timestamp': self.timestamp,
            'predictionTime': self.prediction_time,
            'timeAhead': round(self.time_ahead, 1),
            'predictedDensity': round(self.predicted_density, 2),
            'actualDensity': round(self.actual_density, 2),
            'absoluteError': round(self.absolute_error, 2),
            'relativeError': round(self.relative_error, 2),
            'predictedCongestion': self.predicted_congestion,
            'actualCongestion': self.actual_congestion,
            'correctClassification': self.correct_classification,
            'confidence': round(self.confidence, 2),
            'dataSource': self.data_source
        }


class PredictionValidator:
    """
    Validate predictions against live TomTom API data
    
    Tracks prediction accuracy metrics:
    - Mean Absolute Error (MAE)
    - Root Mean Squared Error (RMSE)
    - Classification Accuracy (predicted level == actual level)
    
    Usage:
        validator = PredictionValidator(live_traffic_service)
        comparison = await validator.validate_prediction(prediction, road)
        accuracy = validator.get_accuracy_metrics()
    """
    
    def __init__(self, live_traffic_service=None):
        """
        Initialize prediction validator
        
        Args:
            live_traffic_service: Optional live traffic service for API calls
        """
        self.live_service = live_traffic_service
        
        # Storage
        self.prediction_history: List[Dict] = []  # Store predictions for later validation
        self.comparison_results: List[PredictionComparison] = []
        
        # Retention
        self.max_results = 1000  # Keep last 1000 comparisons
        
        print("✅ Prediction Validator initialized")
    
    def record_prediction(self, prediction: 'CongestionPrediction'):
        """
        Record a prediction for later validation
        
        Args:
            prediction: CongestionPrediction object
        """
        # Store prediction with validation timestamps
        for timestamp, density in prediction.predictions:
            self.prediction_history.append({
                'road_id': prediction.road_id,
                'predicted_density': density,
                'prediction_time': prediction.predicted_at,
                'validation_time': timestamp,
                'confidence': prediction.confidence,
                'validated': False
            })
        
        # Cleanup old predictions
        current_time = time.time()
        self.prediction_history = [
            p for p in self.prediction_history
            if p['validation_time'] > current_time - 3600  # Keep last hour
        ]
    
    def validate_with_actual(self, 
                             road_id: str, 
                             actual_density: float,
                             road_name: str = "") -> List[PredictionComparison]:
        """
        Validate predictions against actual density measurement
        
        Args:
            road_id: Road identifier
            actual_density: Actual density from measurement/API
            road_name: Road name for display
        
        Returns:
            List of new comparisons
        """
        current_time = time.time()
        new_comparisons = []
        
        # Find predictions that should be validated now
        for pred in self.prediction_history:
            if (pred['road_id'] == road_id and 
                not pred['validated'] and
                abs(current_time - pred['validation_time']) < 30):  # Within 30s window
                
                # Calculate metrics
                predicted = pred['predicted_density']
                absolute_error = abs(actual_density - predicted)
                relative_error = (absolute_error / actual_density * 100) if actual_density > 0 else 0
                
                # Classification comparison
                predicted_level = self._density_to_congestion(predicted)
                actual_level = self._density_to_congestion(actual_density)
                correct = predicted_level == actual_level
                
                comparison = PredictionComparison(
                    road_id=road_id,
                    road_name=road_name or road_id,
                    timestamp=current_time,
                    prediction_time=pred['prediction_time'],
                    time_ahead=pred['validation_time'] - pred['prediction_time'],
                    predicted_density=predicted,
                    actual_density=actual_density,
                    absolute_error=absolute_error,
                    relative_error=relative_error,
                    predicted_congestion=predicted_level,
                    actual_congestion=actual_level,
                    correct_classification=correct,
                    confidence=pred['confidence'],
                    data_source='ACTUAL_MEASUREMENT'
                )
                
                new_comparisons.append(comparison)
                self.comparison_results.append(comparison)
                pred['validated'] = True
        
        # Trim old results
        if len(self.comparison_results) > self.max_results:
            self.comparison_results = self.comparison_results[-self.max_results:]
        
        return new_comparisons
    
    async def validate_prediction_async(self, 
                                        prediction: 'CongestionPrediction',
                                        road_info: Dict) -> Optional[PredictionComparison]:
        """
        Validate prediction against live API data
        
        Args:
            prediction: CongestionPrediction to validate
            road_info: Road information dict with coordinates
        
        Returns:
            Comparison result or None if validation failed
        """
        if not self.live_service:
            return None
        
        try:
            # Fetch current live data for this road
            live_data = await self.live_service.get_traffic_for_road_segment(
                road_info.get('id'),
                road_info.get('start_lat'),
                road_info.get('start_lon'),
                road_info.get('end_lat'),
                road_info.get('end_lon')
            )
            
            if not live_data:
                return None
            
            # Get current prediction (first point)
            if not prediction.predictions:
                return None
            
            _, predicted_density = prediction.predictions[0]
            
            # Convert live congestion to density score
            actual_density = self._congestion_to_density(live_data.get('congestion_level', 'MEDIUM'))
            
            # Calculate metrics
            absolute_error = abs(actual_density - predicted_density)
            relative_error = (absolute_error / actual_density * 100) if actual_density > 0 else 0
            
            # Classification comparison
            predicted_level = self._density_to_congestion(predicted_density)
            actual_level = live_data.get('congestion_level', 'MEDIUM')
            correct = predicted_level == actual_level
            
            current_time = time.time()
            
            comparison = PredictionComparison(
                road_id=prediction.road_id,
                road_name=road_info.get('name', prediction.road_id),
                timestamp=current_time,
                prediction_time=prediction.predicted_at,
                time_ahead=current_time - prediction.predicted_at,
                predicted_density=predicted_density,
                actual_density=actual_density,
                absolute_error=absolute_error,
                relative_error=relative_error,
                predicted_congestion=predicted_level,
                actual_congestion=actual_level,
                correct_classification=correct,
                confidence=prediction.confidence,
                data_source='TOMTOM_API'
            )
            
            self.comparison_results.append(comparison)
            return comparison
            
        except Exception as e:
            print(f"⚠️ Validation failed for {prediction.road_id}: {e}")
            return None
    
    def get_accuracy_metrics(self, time_window: int = 3600) -> Dict:
        """
        Calculate aggregate accuracy metrics
        
        Args:
            time_window: Seconds to look back (default: 1 hour)
        
        Returns:
            Accuracy statistics
        """
        cutoff = time.time() - time_window
        recent = [c for c in self.comparison_results if c.timestamp >= cutoff]
        
        if not recent:
            return {
                'totalComparisons': 0,
                'meanAbsoluteError': 0,
                'rmse': 0,
                'classificationAccuracy': 0,
                'timeWindowHours': time_window / 3600,
                'timestamp': time.time()
            }
        
        # Calculate metrics
        errors = [c.absolute_error for c in recent]
        mae = float(np.mean(errors))
        rmse = float(np.sqrt(np.mean([e**2 for e in errors])))
        classification_accuracy = float(np.mean([c.correct_classification for c in recent]) * 100)
        
        # Accuracy by time ahead
        accuracy_by_time = {}
        for c in recent:
            minutes_ahead = int(c.time_ahead / 60)
            bucket = f"{minutes_ahead}min"
            if bucket not in accuracy_by_time:
                accuracy_by_time[bucket] = {'correct': 0, 'total': 0}
            accuracy_by_time[bucket]['total'] += 1
            if c.correct_classification:
                accuracy_by_time[bucket]['correct'] += 1
        
        for bucket in accuracy_by_time:
            total = accuracy_by_time[bucket]['total']
            correct = accuracy_by_time[bucket]['correct']
            accuracy_by_time[bucket]['accuracy'] = round(correct / total * 100, 1) if total > 0 else 0
        
        return {
            'totalComparisons': len(recent),
            'meanAbsoluteError': round(mae, 2),
            'rmse': round(rmse, 2),
            'classificationAccuracy': round(classification_accuracy, 1),
            'accuracyByTimeAhead': accuracy_by_time,
            'timeWindowHours': time_window / 3600,
            'timestamp': time.time()
        }
    
    def get_best_worst_predictions(self, limit: int = 5) -> Dict:
        """
        Get best and worst predictions
        
        Args:
            limit: Number of predictions to return
        
        Returns:
            Dict with best and worst predictions
        """
        if not self.comparison_results:
            return {'best': [], 'worst': []}
        
        # Sort by absolute error
        sorted_results = sorted(self.comparison_results, key=lambda c: c.absolute_error)
        
        best = [c.to_dict() for c in sorted_results[:limit]]
        worst = [c.to_dict() for c in sorted_results[-limit:]]
        
        return {
            'best': best,
            'worst': list(reversed(worst))
        }
    
    def get_recent_comparisons(self, limit: int = 20) -> List[Dict]:
        """Get most recent comparison results"""
        recent = self.comparison_results[-limit:]
        return [c.to_dict() for c in reversed(recent)]
    
    def _congestion_to_density(self, level: str) -> float:
        """Convert TomTom congestion level to density score"""
        mapping = {'LOW': 25, 'MEDIUM': 50, 'HIGH': 75, 'JAM': 95, 'CRITICAL': 90}
        return mapping.get(level.upper(), 50)
    
    def _density_to_congestion(self, density: float) -> str:
        """Convert density score to congestion level"""
        if density < 25:
            return 'LOW'
        elif density < 50:
            return 'MEDIUM'
        elif density < 75:
            return 'HIGH'
        else:
            return 'CRITICAL'
    
    def clear(self):
        """Clear all validation data"""
        self.prediction_history.clear()
        self.comparison_results.clear()


# Global validator instance
_prediction_validator: Optional[PredictionValidator] = None


def get_prediction_validator() -> Optional[PredictionValidator]:
    """Get the global PredictionValidator instance"""
    return _prediction_validator


def init_prediction_validator(live_traffic_service=None) -> PredictionValidator:
    """Initialize the global PredictionValidator"""
    global _prediction_validator
    _prediction_validator = PredictionValidator(live_traffic_service)
    return _prediction_validator

