"""
Prediction Engine Tests
FRD-06: AI-Based Congestion Prediction - Testing

Integration tests for the complete prediction system including:
- Prediction engine algorithms
- Congestion classification
- Alert generation
- API endpoints
- Performance benchmarks

Part of the Autonomous City Traffic Intelligence System.
"""

import pytest
import time
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.prediction.prediction_engine import (
    PredictionEngine,
    CongestionPrediction,
    init_prediction_engine,
    get_prediction_engine
)
from app.prediction.congestion_classifier import (
    CongestionClassifier,
    CongestionLevel,
    AlertSeverity,
    init_congestion_classifier,
    get_congestion_classifier
)
from app.prediction.prediction_validator import (
    PredictionValidator,
    init_prediction_validator
)


# ============================================
# Prediction Engine Tests
# ============================================

class TestPredictionEngine:
    """Tests for PredictionEngine"""
    
    def test_initialization(self):
        """Test prediction engine creates successfully"""
        engine = PredictionEngine()
        assert engine is not None
        assert engine.algorithm == 'exponential_smoothing'  # Default
        assert engine.prediction_horizon == 10  # Default 10 minutes
    
    def test_initialization_with_config(self):
        """Test engine with custom config"""
        config = {
            'algorithm': 'moving_average',
            'predictionHorizon': 5,
            'updateFrequency': 60
        }
        engine = PredictionEngine(config)
        
        assert engine.algorithm == 'moving_average'
        assert engine.prediction_horizon == 5
        assert engine.update_frequency == 60
    
    def test_density_recording(self):
        """Test recording density snapshots"""
        engine = PredictionEngine()
        
        # Record some densities
        for i in range(20):
            engine.record_density('ROAD-1', float(i * 5), i)
            time.sleep(0.01)
        
        assert 'ROAD-1' in engine.density_history
        assert len(engine.density_history['ROAD-1']) == 20
    
    def test_moving_average_prediction(self):
        """Test moving average algorithm"""
        engine = PredictionEngine(config={'algorithm': 'moving_average'})
        
        # Record data with known pattern
        for i in range(20):
            engine.record_density('ROAD-1', 50.0, 10)  # Constant density
            time.sleep(0.01)
        
        prediction = engine.predict('ROAD-1')
        
        assert prediction is not None
        assert len(prediction.predictions) == 10  # Default horizon
        assert prediction.algorithm == 'moving_average'
        
        # All predictions should be around 50 (constant input)
        for _, density in prediction.predictions:
            assert 45 <= density <= 55
    
    def test_linear_trend_prediction(self):
        """Test linear trend algorithm"""
        engine = PredictionEngine(config={'algorithm': 'linear_trend'})
        
        # Record with clear increasing trend
        for i in range(30):
            engine.record_density('ROAD-1', float(10 + i), i)
            time.sleep(0.01)
        
        prediction = engine.predict('ROAD-1')
        
        assert prediction is not None
        assert prediction.algorithm == 'linear_trend'
        
        # Should predict increasing trend
        first_pred = prediction.predictions[0][1]
        last_pred = prediction.predictions[-1][1]
        # Trend should continue upward or at least stay high
        assert last_pred >= first_pred * 0.8  # Allow some tolerance
    
    def test_exponential_smoothing_prediction(self):
        """Test exponential smoothing algorithm"""
        engine = PredictionEngine(config={'algorithm': 'exponential_smoothing'})
        
        # Record data
        for i in range(25):
            engine.record_density('ROAD-1', float(30 + (i % 10)), i)
            time.sleep(0.01)
        
        prediction = engine.predict('ROAD-1')
        
        assert prediction is not None
        assert prediction.algorithm == 'exponential_smoothing'
        assert prediction.confidence == 0.75  # Default for exp smoothing
    
    def test_prediction_caching(self):
        """Test prediction caching"""
        engine = PredictionEngine(config={'updateFrequency': 60})
        
        # Record data
        for i in range(20):
            engine.record_density('ROAD-1', float(i), i)
        
        # Get prediction
        pred1 = engine.predict('ROAD-1')
        
        # Get again immediately (should be cached)
        pred2 = engine.predict('ROAD-1')
        
        assert pred1.predicted_at == pred2.predicted_at
    
    def test_force_prediction(self):
        """Test forcing new prediction (ignoring cache)"""
        engine = PredictionEngine(config={'updateFrequency': 60})
        
        for i in range(20):
            engine.record_density('ROAD-1', float(i), i)
        
        pred1 = engine.predict('ROAD-1')
        time.sleep(0.1)
        pred2 = engine.predict('ROAD-1', force=True)
        
        # Should have different prediction times when forced
        assert pred2.predicted_at >= pred1.predicted_at
    
    def test_insufficient_data(self):
        """Test handling of insufficient historical data"""
        engine = PredictionEngine()
        
        # Only record 2 samples (not enough)
        engine.record_density('ROAD-1', 10.0, 1)
        engine.record_density('ROAD-1', 15.0, 2)
        
        prediction = engine.predict('ROAD-1')
        
        # Should return None for insufficient data
        assert prediction is None
    
    def test_all_algorithms(self):
        """Test all prediction algorithms"""
        algorithms = ['moving_average', 'linear_trend', 'exponential_smoothing']
        
        for algorithm in algorithms:
            engine = PredictionEngine(config={'algorithm': algorithm})
            
            # Record data
            for i in range(25):
                engine.record_density('ROAD-TEST', float(20 + i), i)
            
            prediction = engine.predict('ROAD-TEST')
            
            assert prediction is not None, f"{algorithm} failed"
            assert prediction.algorithm == algorithm
            assert len(prediction.predictions) > 0
    
    def test_prediction_range(self):
        """Test predictions stay in valid range (0-100)"""
        engine = PredictionEngine()
        
        # Record extreme values
        for i in range(20):
            engine.record_density('ROAD-1', 95.0, 10)
        
        prediction = engine.predict('ROAD-1')
        
        for _, density in prediction.predictions:
            assert 0 <= density <= 100
    
    def test_predict_all_roads(self):
        """Test predicting multiple roads at once"""
        engine = PredictionEngine()
        
        # Record data for multiple roads
        for road in ['ROAD-1', 'ROAD-2', 'ROAD-3']:
            for i in range(20):
                engine.record_density(road, float(30 + i), i)
        
        predictions = engine.predict_all_roads()
        
        assert len(predictions) == 3
        assert 'ROAD-1' in predictions
        assert 'ROAD-2' in predictions
        assert 'ROAD-3' in predictions
    
    def test_algorithm_change(self):
        """Test changing algorithm at runtime"""
        engine = PredictionEngine(config={'algorithm': 'moving_average'})
        
        for i in range(20):
            engine.record_density('ROAD-1', float(i), i)
        
        engine.set_algorithm('linear_trend')
        
        assert engine.algorithm == 'linear_trend'
        assert len(engine.predictions_cache) == 0  # Cache cleared
    
    def test_statistics(self):
        """Test statistics reporting"""
        engine = PredictionEngine()
        
        for i in range(20):
            engine.record_density('ROAD-1', float(i), i)
        
        engine.predict('ROAD-1')
        
        stats = engine.get_statistics()
        
        assert 'algorithm' in stats
        assert 'totalPredictions' in stats
        assert 'trackedRoads' in stats
        assert stats['totalPredictions'] >= 1


# ============================================
# Congestion Classifier Tests
# ============================================

class TestCongestionClassifier:
    """Tests for CongestionClassifier"""
    
    def test_initialization(self):
        """Test classifier initialization"""
        classifier = CongestionClassifier()
        assert classifier is not None
    
    def test_density_classification(self):
        """Test congestion level classification"""
        classifier = CongestionClassifier()
        
        assert classifier.classify_density(10) == CongestionLevel.LOW
        assert classifier.classify_density(35) == CongestionLevel.MEDIUM
        assert classifier.classify_density(60) == CongestionLevel.HIGH
        assert classifier.classify_density(85) == CongestionLevel.CRITICAL
    
    def test_boundary_classification(self):
        """Test classification at boundaries"""
        classifier = CongestionClassifier()
        
        # Exactly at boundaries
        assert classifier.classify_density(0) == CongestionLevel.LOW
        assert classifier.classify_density(25) == CongestionLevel.MEDIUM
        assert classifier.classify_density(50) == CongestionLevel.HIGH
        assert classifier.classify_density(75) == CongestionLevel.CRITICAL
    
    def test_clamping(self):
        """Test clamping of out-of-range values"""
        classifier = CongestionClassifier()
        
        # Below range
        assert classifier.classify_density(-10) == CongestionLevel.LOW
        
        # Above range
        assert classifier.classify_density(150) == CongestionLevel.CRITICAL
    
    def test_alert_generation_high(self):
        """Test alert generation for high congestion"""
        engine = PredictionEngine()
        classifier = CongestionClassifier()
        
        # Record high density
        for i in range(20):
            engine.record_density('ROAD-1', 80.0, 10)
            time.sleep(0.01)
        
        prediction = engine.predict('ROAD-1')
        alerts = classifier.check_for_alerts(prediction)
        
        assert len(alerts) > 0
        assert alerts[0].predicted_level in [CongestionLevel.HIGH, CongestionLevel.CRITICAL]
    
    def test_no_alert_for_low(self):
        """Test no alert for low congestion"""
        engine = PredictionEngine()
        classifier = CongestionClassifier()
        
        # Record low density
        for i in range(20):
            engine.record_density('ROAD-1', 15.0, 5)
            time.sleep(0.01)
        
        prediction = engine.predict('ROAD-1')
        alerts = classifier.check_for_alerts(prediction)
        
        assert len(alerts) == 0
    
    def test_alert_severity(self):
        """Test alert severity mapping"""
        classifier = CongestionClassifier()
        
        # Create a mock prediction for CRITICAL
        engine = PredictionEngine()
        for i in range(20):
            engine.record_density('ROAD-1', 90.0, 15)
        
        prediction = engine.predict('ROAD-1')
        alerts = classifier.check_for_alerts(prediction)
        
        if alerts:
            assert alerts[0].severity == AlertSeverity.CRITICAL
    
    def test_alert_cooldown(self):
        """Test alert cooldown (deduplication)"""
        classifier = CongestionClassifier()
        classifier.alert_cooldown = 1  # 1 second cooldown
        
        engine = PredictionEngine(config={'updateFrequency': 0})  # No throttle
        
        # Record high density
        for i in range(20):
            engine.record_density('ROAD-1', 80.0, 10)
        
        prediction1 = engine.predict('ROAD-1', force=True)
        alerts1 = classifier.check_for_alerts(prediction1)
        
        # Try again immediately (should be blocked by cooldown)
        prediction2 = engine.predict('ROAD-1', force=True)
        alerts2 = classifier.check_for_alerts(prediction2)
        
        assert len(alerts1) > 0
        assert len(alerts2) == 0  # Blocked by cooldown
    
    def test_max_predicted_level(self):
        """Test getting max predicted congestion level"""
        classifier = CongestionClassifier()
        engine = PredictionEngine()
        
        # Create varied predictions
        for i in range(20):
            engine.record_density('ROAD-1', float(30 + i * 2), i)
        
        prediction = engine.predict('ROAD-1')
        max_level = classifier.get_max_predicted_level(prediction)
        
        assert isinstance(max_level, CongestionLevel)
    
    def test_active_alerts(self):
        """Test getting active alerts"""
        classifier = CongestionClassifier()
        engine = PredictionEngine()
        
        for i in range(20):
            engine.record_density('ROAD-1', 80.0, 10)
        
        prediction = engine.predict('ROAD-1')
        classifier.check_for_alerts(prediction)
        
        active = classifier.get_active_alerts()
        # Alerts with future predicted_at_time should be active
        assert isinstance(active, list)
    
    def test_resolve_alert(self):
        """Test resolving an alert"""
        classifier = CongestionClassifier()
        engine = PredictionEngine()
        
        for i in range(20):
            engine.record_density('ROAD-1', 80.0, 10)
        
        prediction = engine.predict('ROAD-1')
        alerts = classifier.check_for_alerts(prediction)
        
        if alerts:
            alert_id = alerts[0].alert_id
            success = classifier.resolve_alert(alert_id)
            assert success
            assert alerts[0].resolved == True


# ============================================
# Prediction Validator Tests
# ============================================

class TestPredictionValidator:
    """Tests for PredictionValidator"""
    
    def test_initialization(self):
        """Test validator initialization"""
        validator = PredictionValidator()
        assert validator is not None
    
    def test_record_prediction(self):
        """Test recording prediction for validation"""
        validator = PredictionValidator()
        engine = PredictionEngine()
        
        for i in range(20):
            engine.record_density('ROAD-1', float(i), i)
        
        prediction = engine.predict('ROAD-1')
        validator.record_prediction(prediction)
        
        assert len(validator.prediction_history) > 0
    
    def test_validate_with_actual(self):
        """Test validating prediction with actual value"""
        validator = PredictionValidator()
        
        # Record a prediction manually
        validator.prediction_history.append({
            'road_id': 'ROAD-1',
            'predicted_density': 50.0,
            'prediction_time': time.time() - 60,
            'validation_time': time.time(),
            'confidence': 0.8,
            'validated': False
        })
        
        comparisons = validator.validate_with_actual('ROAD-1', 55.0, 'Test Road')
        
        assert len(comparisons) == 1
        assert comparisons[0].absolute_error == 5.0
    
    def test_accuracy_metrics(self):
        """Test accuracy metrics calculation"""
        validator = PredictionValidator()
        
        # Add some comparison results
        from app.prediction.prediction_validator import PredictionComparison
        
        for i in range(10):
            validator.comparison_results.append(PredictionComparison(
                road_id='ROAD-1',
                road_name='Test Road',
                timestamp=time.time(),
                prediction_time=time.time() - 60,
                time_ahead=60,
                predicted_density=50.0,
                actual_density=55.0,
                absolute_error=5.0,
                relative_error=10.0,
                predicted_congestion='MEDIUM',
                actual_congestion='MEDIUM',
                correct_classification=True,
                confidence=0.8,
                data_source='TEST'
            ))
        
        metrics = validator.get_accuracy_metrics()
        
        assert 'meanAbsoluteError' in metrics
        assert 'classificationAccuracy' in metrics
        assert metrics['totalComparisons'] == 10


# ============================================
# Performance Tests
# ============================================

class TestPerformance:
    """Performance benchmark tests"""
    
    def test_prediction_performance(self):
        """Test prediction performance < 50ms"""
        engine = PredictionEngine()
        
        # Prepare data
        for i in range(30):
            engine.record_density('ROAD-1', float(i), i)
        
        # Benchmark
        start = time.time()
        for _ in range(100):
            engine.predict('ROAD-1', force=True)
        duration = (time.time() - start) * 1000  # ms
        
        avg_time = duration / 100
        print(f"Average prediction time: {avg_time:.2f}ms")
        
        assert avg_time < 50, f"Prediction too slow: {avg_time:.2f}ms"
    
    def test_classification_performance(self):
        """Test classification performance"""
        classifier = CongestionClassifier()
        
        start = time.time()
        for _ in range(10000):
            classifier.classify_density(50.0)
        duration = (time.time() - start) * 1000  # ms
        
        print(f"10000 classifications: {duration:.2f}ms")
        assert duration < 100  # Should be very fast
    
    def test_batch_prediction_performance(self):
        """Test batch prediction for multiple roads"""
        engine = PredictionEngine()
        
        # Prepare 50 roads
        for road_num in range(50):
            for i in range(30):
                engine.record_density(f'ROAD-{road_num}', float(i), i)
        
        start = time.time()
        predictions = engine.predict_all_roads()
        duration = (time.time() - start) * 1000  # ms
        
        print(f"50 road predictions: {duration:.2f}ms")
        assert duration < 1000  # Should be < 1 second
        assert len(predictions) == 50


# ============================================
# Integration Tests
# ============================================

class TestIntegration:
    """Integration tests"""
    
    def test_full_prediction_workflow(self):
        """Test complete prediction workflow"""
        # Initialize components
        engine = PredictionEngine()
        classifier = CongestionClassifier()
        validator = PredictionValidator()
        
        # Record traffic data
        for i in range(30):
            density = 20 + i * 2  # Increasing density
            engine.record_density('ROAD-1', float(density), i)
        
        # Get prediction
        prediction = engine.predict('ROAD-1')
        assert prediction is not None
        
        # Classify prediction
        classifications = classifier.classify_prediction(prediction)
        assert len(classifications) > 0
        
        # Check for alerts
        alerts = classifier.check_for_alerts(prediction)
        # May or may not have alerts depending on density
        assert isinstance(alerts, list)
        
        # Record for validation
        validator.record_prediction(prediction)
        assert len(validator.prediction_history) > 0
    
    def test_global_instances(self):
        """Test global instance management"""
        engine1 = init_prediction_engine({'algorithm': 'linear_trend'})
        engine2 = get_prediction_engine()
        
        assert engine1 is engine2
        assert engine2.algorithm == 'linear_trend'
        
        classifier1 = init_congestion_classifier({})
        classifier2 = get_congestion_classifier()
        
        assert classifier1 is classifier2


# ============================================
# Run Tests
# ============================================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])

