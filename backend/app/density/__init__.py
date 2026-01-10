"""
Density Module

Traffic density tracking and analysis for the Autonomous City Traffic Intelligence System.
Implements FRD-02 Traffic Density Modeling requirements.

This module provides:
- Real-time density tracking with O(1) lookups
- Historical density data with trend analysis
- City-wide metrics aggregation
- Vehicle detection logging
- Data export in CSV/JSON formats
- Live API integration for TomTom data

Usage:
    from app.density import get_density_tracker, DensityLevel
    
    tracker = get_density_tracker()
    tracker.initialize_roads(roads)
    tracker.update(vehicles, roads, junctions, time.time())
    
    density = tracker.get_road_density("R-1")
    metrics = tracker.get_city_metrics()
"""

# Core data structures and tracker
from app.density.density_tracker import (
    DensityLevel,
    TrafficDataSource,
    RoadDensityData,
    JunctionDensityData,
    CityWideDensityMetrics,
    DensityTracker,
    get_density_tracker,
    init_density_tracker
)

# Density calculator
from app.density.density_calculator import DensityCalculator

# Junction aggregator
from app.density.junction_aggregator import JunctionDensityAggregator

# History and trends
from app.density.density_history import (
    DensitySnapshot,
    DensityTrend,
    DensityHistory,
    TrendAnalyzer
)

# City-wide metrics
from app.density.city_metrics import CityDensityCalculator

# Detection logging
from app.density.detection_logger import (
    VehicleDetectionLogger,
    get_detection_logger,
    init_detection_logger
)

# Export functionality
from app.density.density_exporter import DensityExporter

# Live API vehicle conversion
from app.density.traffic_to_vehicle_converter import TrafficToVehicleConverter


__all__ = [
    # Enums
    'DensityLevel',
    'TrafficDataSource',
    'DensityTrend',
    
    # Data classes
    'RoadDensityData',
    'JunctionDensityData',
    'CityWideDensityMetrics',
    'DensitySnapshot',
    
    # Main classes
    'DensityTracker',
    'DensityCalculator',
    'JunctionDensityAggregator',
    'DensityHistory',
    'TrendAnalyzer',
    'CityDensityCalculator',
    'VehicleDetectionLogger',
    'DensityExporter',
    'TrafficToVehicleConverter',
    
    # Factory functions
    'get_density_tracker',
    'init_density_tracker',
    'get_detection_logger',
    'init_detection_logger'
]
