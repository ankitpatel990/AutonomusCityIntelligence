"""
Density Tracking Tests

Comprehensive testing of density tracking system including:
- Unit tests for core functionality
- Integration tests for API endpoints
- Performance tests for O(1) lookups
- Accuracy validation

Implements FRD-02 Section 8 testing requirements.
"""

import pytest
import time
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.density.density_tracker import (
    DensityTracker,
    RoadDensityData,
    JunctionDensityData,
    DensityLevel,
    TrafficDataSource
)
from app.density.density_calculator import DensityCalculator
from app.density.density_history import (
    DensityHistory,
    DensitySnapshot,
    TrendAnalyzer,
    DensityTrend
)
from app.density.city_metrics import CityDensityCalculator
from app.density.junction_aggregator import JunctionDensityAggregator
from app.density.density_exporter import DensityExporter


class TestDensityCalculator:
    """Tests for DensityCalculator class"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.config = {
            'density': {
                'thresholds': {
                    'lowVehicles': 5,
                    'mediumVehicles': 12,
                    'lowScore': 40,
                    'mediumScore': 70
                }
            }
        }
        self.calc = DensityCalculator(self.config)
    
    def test_density_score_calculation_normal(self):
        """Test density score calculation with normal values"""
        score = self.calc.calculate_density_score(vehicle_count=10, capacity=20)
        assert score == 50.0, f"Expected 50.0, got {score}"
    
    def test_density_score_calculation_overloaded(self):
        """Test density score is clamped at 100"""
        score = self.calc.calculate_density_score(vehicle_count=30, capacity=20)
        assert score == 100.0, f"Expected 100.0 (clamped), got {score}"
    
    def test_density_score_calculation_zero_capacity(self):
        """Test density score with zero capacity"""
        score = self.calc.calculate_density_score(vehicle_count=5, capacity=0)
        assert score == 0.0, f"Expected 0.0 for zero capacity, got {score}"
    
    def test_density_score_calculation_empty(self):
        """Test density score with no vehicles"""
        score = self.calc.calculate_density_score(vehicle_count=0, capacity=20)
        assert score == 0.0, f"Expected 0.0, got {score}"
    
    def test_density_classification_low(self):
        """Test LOW density classification"""
        result = self.calc.classify_density(3)
        assert result == DensityLevel.LOW
    
    def test_density_classification_medium(self):
        """Test MEDIUM density classification"""
        result = self.calc.classify_density(8)
        assert result == DensityLevel.MEDIUM
    
    def test_density_classification_high(self):
        """Test HIGH density classification"""
        result = self.calc.classify_density(15)
        assert result == DensityLevel.HIGH
    
    def test_density_classification_boundary_low(self):
        """Test boundary between LOW and MEDIUM"""
        assert self.calc.classify_density(4) == DensityLevel.LOW
        assert self.calc.classify_density(5) == DensityLevel.MEDIUM
    
    def test_density_classification_boundary_high(self):
        """Test boundary between MEDIUM and HIGH"""
        assert self.calc.classify_density(11) == DensityLevel.MEDIUM
        assert self.calc.classify_density(12) == DensityLevel.HIGH
    
    def test_classify_by_score_low(self):
        """Test score-based classification - LOW"""
        assert self.calc.classify_by_score(30) == DensityLevel.LOW
    
    def test_classify_by_score_medium(self):
        """Test score-based classification - MEDIUM"""
        assert self.calc.classify_by_score(55) == DensityLevel.MEDIUM
    
    def test_classify_by_score_high(self):
        """Test score-based classification - HIGH"""
        assert self.calc.classify_by_score(85) == DensityLevel.HIGH
    
    def test_road_capacity_calculation(self):
        """Test road capacity calculation"""
        capacity = self.calc.calculate_road_capacity(length=300, lanes=2)
        expected = int((300 / 30) * 2)  # 20 vehicles
        assert capacity == expected, f"Expected {expected}, got {capacity}"
    
    def test_road_capacity_minimum(self):
        """Test road capacity minimum is 1"""
        capacity = self.calc.calculate_road_capacity(length=10, lanes=1)
        assert capacity >= 1


class TestDensityTracker:
    """Tests for DensityTracker class"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.config = {
            'density': {
                'updateInterval': 1.0,
                'historyRetentionSeconds': 600
            }
        }
        self.tracker = DensityTracker(self.config)
    
    def test_initialization(self):
        """Test DensityTracker initialization"""
        assert self.tracker is not None
        assert len(self.tracker.road_densities) == 0
        assert len(self.tracker.junction_densities) == 0
    
    def test_initialize_roads(self):
        """Test road initialization"""
        roads = [
            {'id': 'R-1', 'traffic': {'capacity': 20}},
            {'id': 'R-2', 'traffic': {'capacity': 15}},
            {'id': 'R-3', 'traffic': {'capacity': 25}}
        ]
        
        self.tracker.initialize_roads(roads)
        
        assert len(self.tracker.road_densities) == 3
        assert 'R-1' in self.tracker.road_densities
        assert 'R-2' in self.tracker.road_densities
        assert 'R-3' in self.tracker.road_densities
    
    def test_initialize_junctions(self):
        """Test junction initialization"""
        junctions = [
            {'id': 'J-1'},
            {'id': 'J-2'},
            {'id': 'J-3'}
        ]
        
        self.tracker.initialize_junctions(junctions)
        
        assert len(self.tracker.junction_densities) == 3
    
    def test_o1_lookup_road_density(self):
        """Test O(1) lookup performance for road density"""
        # Populate with test data
        for i in range(100):
            self.tracker.road_densities[f"R-{i}"] = RoadDensityData(
                road_id=f"R-{i}",
                vehicle_count=i,
                density_score=i * 10
            )
        
        # Test lookup performance
        start = time.time()
        for _ in range(10000):
            result = self.tracker.get_road_density("R-50")
        duration = (time.time() - start) * 1000  # ms
        
        # 10000 lookups should be < 10ms total (O(1) performance)
        assert duration < 10.0, f"Lookup too slow: {duration}ms for 10000 lookups"
        assert result is not None
        assert result.road_id == "R-50"
    
    def test_o1_lookup_junction_density(self):
        """Test O(1) lookup performance for junction density"""
        for i in range(50):
            self.tracker.junction_densities[f"J-{i}"] = JunctionDensityData(
                junction_id=f"J-{i}",
                avg_density=i * 2
            )
        
        start = time.time()
        for _ in range(10000):
            result = self.tracker.get_junction_density("J-25")
        duration = (time.time() - start) * 1000
        
        assert duration < 10.0, f"Lookup too slow: {duration}ms"
    
    def test_add_vehicle_to_road(self):
        """Test adding vehicle to road tracking"""
        self.tracker.road_densities['R-1'] = RoadDensityData(
            road_id='R-1',
            capacity=20
        )
        
        self.tracker.add_vehicle_to_road('v-1', 'R-1')
        
        data = self.tracker.get_road_density('R-1')
        assert data.vehicle_count == 1
        assert 'v-1' in data.vehicle_ids
    
    def test_remove_vehicle_from_road(self):
        """Test removing vehicle from road tracking"""
        self.tracker.road_densities['R-1'] = RoadDensityData(
            road_id='R-1',
            vehicle_ids={'v-1', 'v-2'},
            vehicle_count=2,
            capacity=20
        )
        
        self.tracker.remove_vehicle_from_road('v-1', 'R-1')
        
        data = self.tracker.get_road_density('R-1')
        assert data.vehicle_count == 1
        assert 'v-1' not in data.vehicle_ids
    
    def test_data_source_mode_change(self):
        """Test changing traffic data source mode"""
        assert self.tracker.data_source_mode == TrafficDataSource.SIMULATION
        
        self.tracker.set_data_source_mode(TrafficDataSource.LIVE_API)
        assert self.tracker.data_source_mode == TrafficDataSource.LIVE_API
        
        self.tracker.set_data_source_mode(TrafficDataSource.HYBRID)
        assert self.tracker.data_source_mode == TrafficDataSource.HYBRID


class TestDensityHistory:
    """Tests for DensityHistory class"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.history = DensityHistory(retention_seconds=60)
    
    def test_add_snapshot(self):
        """Test adding snapshots to history"""
        snapshot = DensitySnapshot(
            timestamp=time.time(),
            road_id="R-1",
            vehicle_count=5,
            density_score=25.0,
            classification=DensityLevel.LOW
        )
        
        self.history.add_snapshot(snapshot)
        
        history = self.history.get_history("R-1", 60)
        assert len(history) == 1
    
    def test_history_retention(self):
        """Test old data is cleaned up"""
        # Add old snapshot
        old_snapshot = DensitySnapshot(
            timestamp=time.time() - 120,  # 2 minutes ago
            road_id="R-1",
            vehicle_count=5,
            density_score=25.0,
            classification=DensityLevel.LOW
        )
        self.history.add_snapshot(old_snapshot)
        
        # Add recent snapshot (triggers cleanup)
        recent_snapshot = DensitySnapshot(
            timestamp=time.time(),
            road_id="R-1",
            vehicle_count=10,
            density_score=50.0,
            classification=DensityLevel.MEDIUM
        )
        self.history.add_snapshot(recent_snapshot)
        
        # Old data should be removed
        history = self.history.get_history("R-1", 60)
        assert len(history) == 1
        assert history[0].vehicle_count == 10
    
    def test_get_latest(self):
        """Test getting latest snapshot"""
        for i in range(5):
            snapshot = DensitySnapshot(
                timestamp=time.time() + i,
                road_id="R-1",
                vehicle_count=i,
                density_score=i * 10,
                classification=DensityLevel.LOW
            )
            self.history.add_snapshot(snapshot)
        
        latest = self.history.get_latest("R-1")
        assert latest is not None
        assert latest.vehicle_count == 4
    
    def test_get_average_density(self):
        """Test average density calculation"""
        for i in range(10):
            snapshot = DensitySnapshot(
                timestamp=time.time(),
                road_id="R-1",
                vehicle_count=i,
                density_score=i * 10,  # 0, 10, 20, ..., 90
                classification=DensityLevel.LOW
            )
            self.history.add_snapshot(snapshot)
        
        avg = self.history.get_average_density("R-1", 60)
        expected = sum(i * 10 for i in range(10)) / 10  # 45.0
        assert avg == expected


class TestTrendAnalyzer:
    """Tests for TrendAnalyzer class"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.analyzer = TrendAnalyzer(slope_threshold=5.0)
    
    def test_calculate_trend_increasing(self):
        """Test increasing trend detection"""
        base_time = time.time()
        snapshots = [
            DensitySnapshot(
                timestamp=base_time + i,
                road_id="R-1",
                vehicle_count=i * 2,
                density_score=i * 10,
                classification=DensityLevel.LOW
            )
            for i in range(10)
        ]
        
        trend = self.analyzer.calculate_trend(snapshots, window_seconds=60)
        assert trend == DensityTrend.INCREASING
    
    def test_calculate_trend_decreasing(self):
        """Test decreasing trend detection"""
        base_time = time.time()
        snapshots = [
            DensitySnapshot(
                timestamp=base_time + i,
                road_id="R-1",
                vehicle_count=20 - i * 2,
                density_score=100 - i * 10,
                classification=DensityLevel.HIGH
            )
            for i in range(10)
        ]
        
        trend = self.analyzer.calculate_trend(snapshots, window_seconds=60)
        assert trend == DensityTrend.DECREASING
    
    def test_calculate_trend_stable(self):
        """Test stable trend detection"""
        base_time = time.time()
        snapshots = [
            DensitySnapshot(
                timestamp=base_time + i,
                road_id="R-1",
                vehicle_count=10,
                density_score=50.0,  # Constant
                classification=DensityLevel.MEDIUM
            )
            for i in range(10)
        ]
        
        trend = self.analyzer.calculate_trend(snapshots, window_seconds=60)
        assert trend == DensityTrend.STABLE
    
    def test_calculate_rate_of_change(self):
        """Test rate of change calculation"""
        base_time = time.time()
        snapshots = [
            DensitySnapshot(
                timestamp=base_time + i,
                road_id="R-1",
                vehicle_count=i,  # Increases by 1 per second
                density_score=i * 10,
                classification=DensityLevel.LOW
            )
            for i in range(10)
        ]
        
        rate = self.analyzer.calculate_rate_of_change(snapshots)
        # 9 vehicles over 9 seconds = 1 vehicle/second
        assert abs(rate - 1.0) < 0.1
    
    def test_calculate_volatility(self):
        """Test volatility calculation"""
        base_time = time.time()
        # High volatility - alternating high/low
        snapshots = [
            DensitySnapshot(
                timestamp=base_time + i,
                road_id="R-1",
                vehicle_count=5,
                density_score=90 if i % 2 == 0 else 10,  # Alternating
                classification=DensityLevel.LOW
            )
            for i in range(10)
        ]
        
        volatility = self.analyzer.calculate_volatility(snapshots)
        assert volatility > 30  # High volatility expected


class TestCityDensityCalculator:
    """Tests for CityDensityCalculator class"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.calc = CityDensityCalculator()
    
    def test_calculate_city_metrics(self):
        """Test city-wide metrics calculation"""
        road_densities = {
            "R-1": RoadDensityData("R-1", 5, set(), 25.0, DensityLevel.LOW, capacity=20),
            "R-2": RoadDensityData("R-2", 10, set(), 50.0, DensityLevel.MEDIUM, capacity=20),
            "R-3": RoadDensityData("R-3", 15, set(), 75.0, DensityLevel.HIGH, capacity=20),
        }
        
        junction_densities = {
            "J-1": JunctionDensityData("J-1", congestion_level=DensityLevel.LOW),
            "J-2": JunctionDensityData("J-2", congestion_level=DensityLevel.HIGH),
        }
        
        metrics = self.calc.calculate_city_metrics(road_densities, junction_densities)
        
        assert metrics.total_vehicles == 30
        assert metrics.low_density_roads == 1
        assert metrics.medium_density_roads == 1
        assert metrics.high_density_roads == 1
        assert abs(metrics.avg_density_score - 50.0) < 0.1  # (25+50+75)/3
        assert metrics.congestion_points == 1  # Only J-2 is HIGH
    
    def test_get_congestion_hotspots(self):
        """Test congestion hotspot detection"""
        road_densities = {
            "R-1": RoadDensityData("R-1", density_score=80.0),
            "R-2": RoadDensityData("R-2", density_score=50.0),
            "R-3": RoadDensityData("R-3", density_score=90.0),
        }
        
        hotspots = self.calc.get_congestion_hotspots(road_densities, threshold=70.0)
        
        assert len(hotspots) == 2
        assert hotspots[0][0] == "R-3"  # Highest first
        assert hotspots[1][0] == "R-1"
    
    def test_get_density_distribution(self):
        """Test density distribution statistics"""
        road_densities = {
            f"R-{i}": RoadDensityData(f"R-{i}", density_score=i * 10)
            for i in range(1, 11)  # 10, 20, ..., 100
        }
        
        dist = self.calc.get_density_distribution(road_densities)
        
        assert dist['min'] == 10
        assert dist['max'] == 100
        assert dist['mean'] == 55  # (10+20+...+100)/10


class TestDensityExporter:
    """Tests for DensityExporter class"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.exporter = DensityExporter()
        self.road_densities = {
            "R-1": RoadDensityData("R-1", 5, set(), 25.0, DensityLevel.LOW),
            "R-2": RoadDensityData("R-2", 10, set(), 50.0, DensityLevel.MEDIUM),
        }
        self.junction_densities = {
            "J-1": JunctionDensityData("J-1", avg_density=30.0),
        }
    
    def test_export_to_csv(self):
        """Test CSV export"""
        csv = self.exporter.export_to_csv(self.road_densities)
        
        assert 'timestamp' in csv
        assert 'road_id' in csv
        assert 'R-1' in csv
        assert 'R-2' in csv
    
    def test_export_to_json(self):
        """Test JSON export"""
        import json
        
        json_str = self.exporter.export_to_json(
            self.road_densities,
            self.junction_densities
        )
        
        data = json.loads(json_str)
        
        assert 'roads' in data
        assert 'junctions' in data
        assert 'metadata' in data
        assert 'R-1' in data['roads']
    
    def test_format_for_ui(self):
        """Test UI data formatting"""
        ui_data = self.exporter.format_for_ui(self.road_densities)
        
        assert len(ui_data) == 2
        
        for item in ui_data:
            assert 'roadId' in item
            assert 'color' in item
            assert item['color'].startswith('#')
    
    def test_color_mapping(self):
        """Test color mapping for classifications"""
        assert self.exporter.get_color_for_classification(DensityLevel.LOW) == '#2ed573'
        assert self.exporter.get_color_for_classification(DensityLevel.MEDIUM) == '#ffa502'
        assert self.exporter.get_color_for_classification(DensityLevel.HIGH) == '#ff4757'


class TestJunctionDensityAggregator:
    """Tests for JunctionDensityAggregator class"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.aggregator = JunctionDensityAggregator()
    
    def test_calculate_junction_density(self):
        """Test junction density aggregation"""
        junction = {
            'id': 'J-1',
            'connected_roads': {
                'north': 'R-N',
                'east': 'R-E',
                'south': 'R-S',
                'west': 'R-W'
            }
        }
        
        road_densities = {
            'R-N': RoadDensityData('R-N', 5, set(), 25.0, DensityLevel.LOW),
            'R-E': RoadDensityData('R-E', 10, set(), 50.0, DensityLevel.MEDIUM),
            'R-S': RoadDensityData('R-S', 15, set(), 75.0, DensityLevel.HIGH),
            'R-W': RoadDensityData('R-W', 8, set(), 40.0, DensityLevel.MEDIUM),
        }
        
        result = self.aggregator.calculate_junction_density(junction, road_densities)
        
        assert result.junction_id == 'J-1'
        assert result.density_north == 25.0
        assert result.density_east == 50.0
        assert result.density_south == 75.0
        assert result.density_west == 40.0
        assert result.max_density == 75.0
        assert result.total_vehicles == 38  # 5+10+15+8
        assert result.congestion_level == DensityLevel.HIGH  # max > 70
    
    def test_get_most_congested_direction(self):
        """Test finding most congested direction"""
        junction_data = JunctionDensityData(
            junction_id='J-1',
            density_north=30.0,
            density_east=80.0,
            density_south=45.0,
            density_west=20.0
        )
        
        direction = self.aggregator.get_most_congested_direction(junction_data)
        assert direction == 'east'


class TestPerformance:
    """Performance tests for density tracking system"""
    
    def test_update_performance_200_vehicles(self):
        """Test density update performance with 200 vehicles"""
        tracker = DensityTracker({'density': {'updateInterval': 0}})  # No throttling
        
        # Create test data
        roads = [{'id': f'R-{i}', 'traffic': {'capacity': 20}} for i in range(20)]
        junctions = [{'id': f'J-{i}', 'connected_roads': {}} for i in range(9)]
        vehicles = [
            {
                'id': f'v-{i}',
                'current_road': f'R-{i % 20}',
                'position': {'x': 100, 'y': 100}
            }
            for i in range(200)
        ]
        
        # Initialize
        tracker.initialize_roads(roads)
        tracker.initialize_junctions(junctions)
        
        # Measure update time
        start = time.time()
        tracker.update(vehicles, roads, junctions, time.time())
        duration = (time.time() - start) * 1000  # ms
        
        # Should complete in < 50ms
        assert duration < 50, f"Update too slow: {duration}ms (target: <50ms)"
    
    def test_memory_bounded(self):
        """Test that memory usage is bounded by circular buffers"""
        history = DensityHistory(retention_seconds=60)
        
        # Add many snapshots
        for i in range(1000):
            snapshot = DensitySnapshot(
                timestamp=time.time(),
                road_id="R-1",
                vehicle_count=i,
                density_score=50.0,
                classification=DensityLevel.MEDIUM
            )
            history.add_snapshot(snapshot)
        
        # Should be bounded to max_entries
        assert len(history.road_history['R-1']) <= 60


# Helper for running tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

