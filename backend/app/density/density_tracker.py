"""
Density Tracker Module

Core density tracking and management class with O(1) lookups.
Implements FRD-02 Traffic Density Modeling requirements.

Features:
- Real-time vehicle tracking per road segment
- O(1) lookup performance for density queries
- Configurable density thresholds
- Integration with live traffic API
"""

from typing import Dict, Set, Optional, List, Any
from dataclasses import dataclass, field
from enum import Enum
import time

from app.config import get_config


class DensityLevel(str, Enum):
    """Traffic density classification levels"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class TrafficDataSource(str, Enum):
    """Traffic data source modes"""
    LIVE_API = "LIVE_API"
    SIMULATION = "SIMULATION"
    HYBRID = "HYBRID"
    MANUAL = "MANUAL"


@dataclass
class RoadDensityData:
    """
    Density data for a road segment
    
    Tracks vehicle count, IDs, density score, and classification
    for a single road segment with O(1) access.
    """
    road_id: str
    vehicle_count: int = 0
    vehicle_ids: Set[str] = field(default_factory=set)
    density_score: float = 0.0
    classification: DensityLevel = DensityLevel.LOW
    timestamp: float = field(default_factory=time.time)
    
    # Optional: capacity for density calculations
    capacity: int = 20
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses"""
        return {
            'roadId': self.road_id,
            'vehicleCount': self.vehicle_count,
            'vehicleIds': list(self.vehicle_ids),
            'densityScore': round(self.density_score, 2),
            'classification': self.classification.value,
            'timestamp': self.timestamp,
            'capacity': self.capacity
        }


@dataclass
class JunctionDensityData:
    """
    Aggregated density metrics for a junction
    
    Combines density data from all 4 connected roads (N/E/S/W).
    """
    junction_id: str
    
    # Density per direction (0-100)
    density_north: float = 0.0
    density_east: float = 0.0
    density_south: float = 0.0
    density_west: float = 0.0
    
    # Aggregate metrics
    avg_density: float = 0.0
    max_density: float = 0.0
    total_vehicles: int = 0
    avg_waiting_time: float = 0.0
    
    # Classification
    congestion_level: DensityLevel = DensityLevel.LOW
    
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses"""
        return {
            'junctionId': self.junction_id,
            'densities': {
                'north': round(self.density_north, 2),
                'east': round(self.density_east, 2),
                'south': round(self.density_south, 2),
                'west': round(self.density_west, 2)
            },
            'avgDensity': round(self.avg_density, 2),
            'maxDensity': round(self.max_density, 2),
            'totalVehicles': self.total_vehicles,
            'avgWaitingTime': round(self.avg_waiting_time, 2),
            'congestionLevel': self.congestion_level.value,
            'timestamp': self.timestamp
        }


@dataclass
class CityWideDensityMetrics:
    """City-wide traffic density metrics"""
    total_vehicles: int = 0
    total_road_capacity: int = 0
    avg_density_score: float = 0.0
    
    # Classification breakdown
    low_density_roads: int = 0
    medium_density_roads: int = 0
    high_density_roads: int = 0
    
    # Congestion metrics
    congestion_points: int = 0
    congestion_percentage: float = 0.0
    
    # Peak tracking
    peak_density_road: str = ""
    peak_density_score: float = 0.0
    
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses"""
        return {
            'totalVehicles': self.total_vehicles,
            'totalRoadCapacity': self.total_road_capacity,
            'avgDensityScore': round(self.avg_density_score, 2),
            'roadBreakdown': {
                'low': self.low_density_roads,
                'medium': self.medium_density_roads,
                'high': self.high_density_roads
            },
            'congestionPoints': self.congestion_points,
            'congestionPercentage': round(self.congestion_percentage, 2),
            'peak': {
                'roadId': self.peak_density_road,
                'densityScore': round(self.peak_density_score, 2)
            },
            'timestamp': self.timestamp
        }


class DensityTracker:
    """
    Main density tracking and management class
    
    Provides O(1) lookups for road and junction densities.
    Updates real-time based on vehicle positions.
    
    Usage:
        tracker = DensityTracker(config)
        tracker.initialize_roads(roads)
        tracker.initialize_junctions(junctions)
        tracker.update(vehicles, roads, junctions, current_time)
        
        # O(1) lookup
        density = tracker.get_road_density("R-1")
    """
    
    def __init__(self, config: dict = None):
        """
        Initialize the DensityTracker
        
        Args:
            config: Configuration dictionary (defaults to traffic config)
        """
        if config is None:
            cfg = get_config()
            config = cfg.get_traffic_config() if cfg else {}
        
        self.config = config
        
        # Core data structures - O(1) lookup
        self.road_densities: Dict[str, RoadDensityData] = {}
        self.junction_densities: Dict[str, JunctionDensityData] = {}
        
        # State tracking
        self.last_update: float = 0.0
        self.update_interval: float = config.get('density', {}).get('updateInterval', 1.0)
        
        # Statistics
        self.total_updates: int = 0
        
        # Traffic data source mode
        self.data_source_mode: TrafficDataSource = TrafficDataSource.SIMULATION
        
        # Lazy imports to avoid circular dependencies
        self._calculator = None
        self._aggregator = None
        self._history = None
        self._detection_logger = None
        
        print(f"[OK] DensityTracker initialized with update interval: {self.update_interval}s")
    
    @property
    def calculator(self):
        """Lazy load density calculator"""
        if self._calculator is None:
            from app.density.density_calculator import DensityCalculator
            self._calculator = DensityCalculator(self.config)
        return self._calculator
    
    @property
    def aggregator(self):
        """Lazy load junction aggregator"""
        if self._aggregator is None:
            from app.density.junction_aggregator import JunctionDensityAggregator
            self._aggregator = JunctionDensityAggregator()
        return self._aggregator
    
    @property
    def history(self):
        """Lazy load density history"""
        if self._history is None:
            from app.density.density_history import DensityHistory
            retention = self.config.get('density', {}).get('historyRetentionSeconds', 600)
            self._history = DensityHistory(retention_seconds=retention)
        return self._history
    
    def initialize_roads(self, roads: list):
        """
        Initialize density tracking for all roads
        
        Args:
            roads: List of RoadSegment objects
        """
        for road in roads:
            road_id = road.id if hasattr(road, 'id') else road.get('id', str(road))
            capacity = 20  # Default capacity
            
            if hasattr(road, 'traffic') and hasattr(road.traffic, 'capacity'):
                capacity = road.traffic.capacity
            elif isinstance(road, dict):
                capacity = road.get('traffic', {}).get('capacity', 20)
            
            self.road_densities[road_id] = RoadDensityData(
                road_id=road_id,
                vehicle_count=0,
                vehicle_ids=set(),
                density_score=0.0,
                classification=DensityLevel.LOW,
                capacity=capacity
            )
        
        print(f"[OK] Initialized density tracking for {len(roads)} roads")
    
    def initialize_junctions(self, junctions: list):
        """
        Initialize density tracking for all junctions
        
        Args:
            junctions: List of Junction objects
        """
        for junction in junctions:
            junction_id = junction.id if hasattr(junction, 'id') else junction.get('id', str(junction))
            
            self.junction_densities[junction_id] = JunctionDensityData(
                junction_id=junction_id
            )
        
        print(f"[OK] Initialized density tracking for {len(junctions)} junctions")
    
    def get_road_density(self, road_id: str) -> Optional[RoadDensityData]:
        """
        O(1) lookup for road density
        
        Args:
            road_id: Road identifier
            
        Returns:
            RoadDensityData or None if not found
        """
        return self.road_densities.get(road_id)
    
    def get_junction_density(self, junction_id: str) -> Optional[JunctionDensityData]:
        """
        O(1) lookup for junction density
        
        Args:
            junction_id: Junction identifier
            
        Returns:
            JunctionDensityData or None if not found
        """
        return self.junction_densities.get(junction_id)
    
    def update_road_density(self, road_id: str, data: RoadDensityData):
        """
        O(1) update for road density
        
        Args:
            road_id: Road identifier
            data: New density data
        """
        self.road_densities[road_id] = data
        self.last_update = time.time()
    
    def add_vehicle_to_road(self, vehicle_id: str, road_id: str):
        """
        Add a vehicle to a road's tracking
        
        Args:
            vehicle_id: Vehicle identifier
            road_id: Road identifier
        """
        if road_id in self.road_densities:
            data = self.road_densities[road_id]
            if vehicle_id not in data.vehicle_ids:
                data.vehicle_ids.add(vehicle_id)
                data.vehicle_count = len(data.vehicle_ids)
                self._recalculate_road_density(road_id)
    
    def remove_vehicle_from_road(self, vehicle_id: str, road_id: str):
        """
        Remove a vehicle from a road's tracking
        
        Args:
            vehicle_id: Vehicle identifier
            road_id: Road identifier
        """
        if road_id in self.road_densities:
            data = self.road_densities[road_id]
            if vehicle_id in data.vehicle_ids:
                data.vehicle_ids.discard(vehicle_id)
                data.vehicle_count = len(data.vehicle_ids)
                self._recalculate_road_density(road_id)
    
    def _recalculate_road_density(self, road_id: str):
        """Recalculate density score and classification for a road"""
        if road_id not in self.road_densities:
            return
        
        data = self.road_densities[road_id]
        
        # Calculate score
        data.density_score = self.calculator.calculate_density_score(
            data.vehicle_count,
            data.capacity
        )
        
        # Classify
        data.classification = self.calculator.classify_density(data.vehicle_count)
        data.timestamp = time.time()
    
    def update(self, vehicles: list, roads: list, junctions: list, current_time: float):
        """
        Main update method - called every frame from agent loop
        
        Updates:
        1. Road densities based on vehicle positions
        2. Junction densities (aggregated)
        3. Classifications
        
        Throttled to configured interval (default 1 second)
        
        Args:
            vehicles: List of Vehicle objects
            roads: List of RoadSegment objects
            junctions: List of Junction objects
            current_time: Current simulation time
        """
        # Throttle updates to configured interval
        if current_time - self.last_update < self.update_interval:
            return
        
        # Update road densities
        self._update_road_densities(vehicles, roads, current_time)
        
        # Update junction densities (aggregated from roads)
        self._update_junction_densities(junctions, current_time)
        
        # Record history
        self._record_history(current_time)
        
        # Update statistics
        self.total_updates += 1
        self.last_update = current_time
    
    def _update_road_densities(self, vehicles: list, roads: list, current_time: float):
        """Update density for all road segments"""
        # Clear previous vehicle tracking
        for road in roads:
            road_id = road.id if hasattr(road, 'id') else road.get('id', str(road))
            
            if road_id not in self.road_densities:
                capacity = 20
                if hasattr(road, 'traffic') and hasattr(road.traffic, 'capacity'):
                    capacity = road.traffic.capacity
                elif isinstance(road, dict):
                    capacity = road.get('traffic', {}).get('capacity', 20)
                
                self.road_densities[road_id] = RoadDensityData(
                    road_id=road_id,
                    capacity=capacity
                )
            
            self.road_densities[road_id].vehicle_ids.clear()
            self.road_densities[road_id].vehicle_count = 0
        
        # Track vehicles on roads
        for vehicle in vehicles:
            current_road = None
            vehicle_id = None
            
            if hasattr(vehicle, 'current_road'):
                current_road = vehicle.current_road
                vehicle_id = vehicle.id
            elif isinstance(vehicle, dict):
                current_road = vehicle.get('current_road') or vehicle.get('currentRoad')
                vehicle_id = vehicle.get('id')
            
            if current_road and current_road in self.road_densities:
                road_data = self.road_densities[current_road]
                road_data.vehicle_ids.add(vehicle_id)
                road_data.vehicle_count = len(road_data.vehicle_ids)
        
        # Calculate density scores and classifications
        for road in roads:
            road_id = road.id if hasattr(road, 'id') else road.get('id', str(road))
            
            if road_id not in self.road_densities:
                continue
            
            road_data = self.road_densities[road_id]
            
            # Get capacity
            capacity = road_data.capacity
            if capacity == 0:
                length = 300  # default
                lanes = 2
                if hasattr(road, 'geometry'):
                    length = road.geometry.length if hasattr(road.geometry, 'length') else 300
                    lanes = road.geometry.lanes if hasattr(road.geometry, 'lanes') else 2
                elif isinstance(road, dict):
                    geometry = road.get('geometry', {})
                    length = geometry.get('length', 300)
                    lanes = geometry.get('lanes', 2)
                
                capacity = self.calculator.calculate_road_capacity(length, lanes)
                road_data.capacity = capacity
            
            # Calculate score
            road_data.density_score = self.calculator.calculate_density_score(
                road_data.vehicle_count,
                capacity
            )
            
            # Classify
            road_data.classification = self.calculator.classify_density(
                road_data.vehicle_count
            )
            
            road_data.timestamp = current_time
    
    def _update_junction_densities(self, junctions: list, current_time: float):
        """Update aggregated density for all junctions"""
        for junction in junctions:
            junction_id = junction.id if hasattr(junction, 'id') else junction.get('id', str(junction))
            
            self.junction_densities[junction_id] = self.aggregator.calculate_junction_density(
                junction,
                self.road_densities
            )
    
    def _record_history(self, current_time: float):
        """Record current densities to history"""
        from app.density.density_history import DensitySnapshot
        
        for road_id, data in self.road_densities.items():
            snapshot = DensitySnapshot(
                timestamp=current_time,
                road_id=road_id,
                vehicle_count=data.vehicle_count,
                density_score=data.density_score,
                classification=data.classification
            )
            self.history.add_snapshot(snapshot)
    
    def get_city_metrics(self) -> CityWideDensityMetrics:
        """
        Get city-wide density metrics
        
        Returns:
            CityWideDensityMetrics with aggregated statistics
        """
        from app.density.city_metrics import CityDensityCalculator
        calculator = CityDensityCalculator()
        return calculator.calculate_city_metrics(
            self.road_densities,
            self.junction_densities
        )
    
    def get_all_road_densities(self) -> List[dict]:
        """Get density data for all roads"""
        return [data.to_dict() for data in self.road_densities.values()]
    
    def get_all_junction_densities(self) -> List[dict]:
        """Get density data for all junctions"""
        return [data.to_dict() for data in self.junction_densities.values()]
    
    def set_data_source_mode(self, mode: TrafficDataSource):
        """
        Set the traffic data source mode
        
        Args:
            mode: TrafficDataSource enum value
        """
        self.data_source_mode = mode
        print(f"[MODE] Traffic data source mode changed to: {mode.value}")
    
    def get_stats(self) -> dict:
        """Get tracker statistics"""
        return {
            'totalRoads': len(self.road_densities),
            'totalJunctions': len(self.junction_densities),
            'totalUpdates': self.total_updates,
            'lastUpdate': self.last_update,
            'updateInterval': self.update_interval,
            'dataSourceMode': self.data_source_mode.value
        }


# Global density tracker instance
_density_tracker: Optional[DensityTracker] = None


def get_density_tracker() -> DensityTracker:
    """Get the global DensityTracker instance"""
    global _density_tracker
    if _density_tracker is None:
        _density_tracker = DensityTracker()
    return _density_tracker


def init_density_tracker(config: dict = None) -> DensityTracker:
    """Initialize the global DensityTracker with config"""
    global _density_tracker
    _density_tracker = DensityTracker(config)
    return _density_tracker

