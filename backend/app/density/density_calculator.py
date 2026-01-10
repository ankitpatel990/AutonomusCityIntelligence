"""
Density Calculator Module

Calculate density scores and classifications for road segments.
Implements configurable thresholds from traffic.json config.

Features:
- Density score calculation (0-100)
- Vehicle count-based classification
- Score-based classification
- Road capacity calculation
"""

from app.density.density_tracker import DensityLevel


class DensityCalculator:
    """
    Calculate density scores and classifications
    
    Supports configurable thresholds for different classification methods.
    All thresholds can be configured via config/traffic.json.
    """
    
    def __init__(self, config: dict = None):
        """
        Initialize calculator with configuration
        
        Args:
            config: Traffic configuration dictionary
        """
        if config is None:
            config = {}
        
        # Extract density thresholds from config
        density_config = config.get('density', {})
        thresholds = density_config.get('thresholds', {})
        
        # Vehicle count thresholds
        self.low_threshold = thresholds.get('lowVehicles', 5)
        self.medium_threshold = thresholds.get('mediumVehicles', 12)
        
        # Score thresholds (0-100)
        self.low_score_threshold = thresholds.get('lowScore', 40)
        self.medium_score_threshold = thresholds.get('mediumScore', 70)
        
        # Vehicle space calculation constants
        self.vehicle_length = 20   # pixels (average vehicle length)
        self.safety_gap = 10       # pixels (safety gap between vehicles)
        self.vehicle_space = self.vehicle_length + self.safety_gap  # 30 pixels total
    
    def calculate_density_score(self, vehicle_count: int, capacity: int) -> float:
        """
        Calculate density score (0-100)
        
        Formula: (current_vehicles / road_capacity) × 100
        Clamped to [0, 100]
        
        Args:
            vehicle_count: Current number of vehicles on road
            capacity: Maximum vehicle capacity of road
            
        Returns:
            Density score from 0 to 100
        """
        if capacity == 0:
            return 0.0
        
        score = (vehicle_count / capacity) * 100
        return min(score, 100.0)
    
    def classify_density(self, vehicle_count: int) -> DensityLevel:
        """
        Classify density based on vehicle count
        
        Default thresholds:
        - LOW: 0-5 vehicles
        - MEDIUM: 6-12 vehicles
        - HIGH: 13+ vehicles
        
        Args:
            vehicle_count: Number of vehicles
            
        Returns:
            DensityLevel enum value
        """
        if vehicle_count < self.low_threshold:
            return DensityLevel.LOW
        elif vehicle_count < self.medium_threshold:
            return DensityLevel.MEDIUM
        else:
            return DensityLevel.HIGH
    
    def classify_by_score(self, density_score: float) -> DensityLevel:
        """
        Classify based on density score (0-100)
        
        Default thresholds:
        - LOW: < 40
        - MEDIUM: 40-70
        - HIGH: > 70
        
        Args:
            density_score: Density score from 0 to 100
            
        Returns:
            DensityLevel enum value
        """
        if density_score < self.low_score_threshold:
            return DensityLevel.LOW
        elif density_score < self.medium_score_threshold:
            return DensityLevel.MEDIUM
        else:
            return DensityLevel.HIGH
    
    def calculate_road_capacity(self, length: float, lanes: int) -> int:
        """
        Calculate road capacity based on length and lanes
        
        Assumptions:
        - Average vehicle length: 20 pixels
        - Safety gap: 10 pixels
        - Total space per vehicle: 30 pixels
        
        Args:
            length: Road length in pixels (or meters for real roads)
            lanes: Number of lanes
            
        Returns:
            Maximum vehicle capacity (minimum 1)
        """
        vehicles_per_lane = length / self.vehicle_space
        total_capacity = int(vehicles_per_lane * lanes)
        return max(total_capacity, 1)
    
    def calculate_congestion_ratio(self, vehicle_count: int, capacity: int) -> float:
        """
        Calculate congestion ratio (0-1)
        
        Args:
            vehicle_count: Current vehicles
            capacity: Road capacity
            
        Returns:
            Ratio from 0 to 1 (clamped)
        """
        if capacity == 0:
            return 0.0
        return min(1.0, vehicle_count / capacity)
    
    def get_color_for_density(self, classification: DensityLevel) -> str:
        """
        Get UI color for density classification
        
        Args:
            classification: DensityLevel enum
            
        Returns:
            Hex color code
        """
        color_map = {
            DensityLevel.LOW: '#2ed573',     # Green
            DensityLevel.MEDIUM: '#ffa502',   # Yellow/Orange
            DensityLevel.HIGH: '#ff4757'      # Red
        }
        return color_map.get(classification, '#cccccc')
    
    def get_thresholds(self) -> dict:
        """Get current threshold configuration"""
        return {
            'vehicleCount': {
                'low': self.low_threshold,
                'medium': self.medium_threshold
            },
            'score': {
                'low': self.low_score_threshold,
                'medium': self.medium_score_threshold
            }
        }

