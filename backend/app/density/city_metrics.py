"""
City-Wide Metrics Module

Calculate aggregate city-wide density metrics.
Implements FRD-02 FR-02.8 requirements.

Features:
- Total vehicle count aggregation
- Average density calculation
- Congestion point counting
- Peak tracking
- Classification breakdown
"""

from typing import Dict
import time

from app.density.density_tracker import (
    RoadDensityData,
    JunctionDensityData,
    CityWideDensityMetrics,
    DensityLevel
)


class CityDensityCalculator:
    """
    Calculate city-wide density metrics
    
    Aggregates data from all roads and junctions to provide
    a comprehensive view of city-wide traffic conditions.
    """
    
    def __init__(self):
        """Initialize the calculator"""
        pass
    
    def calculate_city_metrics(
        self,
        road_densities: Dict[str, RoadDensityData],
        junction_densities: Dict[str, JunctionDensityData]
    ) -> CityWideDensityMetrics:
        """
        Calculate comprehensive city-wide metrics
        
        Aggregates:
        - Total vehicles across all roads
        - Average density score
        - Classification breakdown
        - Congestion points (HIGH density junctions)
        - Peak density tracking
        
        Args:
            road_densities: Dictionary of road_id -> RoadDensityData
            junction_densities: Dictionary of junction_id -> JunctionDensityData
            
        Returns:
            CityWideDensityMetrics with all aggregated data
        """
        metrics = CityWideDensityMetrics()
        
        # Aggregate road-level data
        total_density = 0.0
        road_count = 0
        
        for road_id, data in road_densities.items():
            metrics.total_vehicles += data.vehicle_count
            metrics.total_road_capacity += data.capacity
            total_density += data.density_score
            road_count += 1
            
            # Classification counts
            if data.classification == DensityLevel.LOW:
                metrics.low_density_roads += 1
            elif data.classification == DensityLevel.MEDIUM:
                metrics.medium_density_roads += 1
            else:
                metrics.high_density_roads += 1
            
            # Track peak density
            if data.density_score > metrics.peak_density_score:
                metrics.peak_density_score = data.density_score
                metrics.peak_density_road = road_id
        
        # Calculate averages
        if road_count > 0:
            metrics.avg_density_score = total_density / road_count
        
        # Count congestion points (HIGH density junctions)
        metrics.congestion_points = sum(
            1 for jd in junction_densities.values()
            if jd.congestion_level == DensityLevel.HIGH
        )
        
        # Congestion percentage
        total_junctions = len(junction_densities)
        if total_junctions > 0:
            metrics.congestion_percentage = (
                metrics.congestion_points / total_junctions
            ) * 100
        
        metrics.timestamp = time.time()
        
        return metrics
    
    def get_congestion_hotspots(
        self,
        road_densities: Dict[str, RoadDensityData],
        threshold: float = 70.0
    ) -> list:
        """
        Get list of roads above congestion threshold
        
        Args:
            road_densities: Dictionary of road_id -> RoadDensityData
            threshold: Density score threshold (default 70)
            
        Returns:
            List of (road_id, density_score) tuples, sorted by density
        """
        hotspots = [
            (road_id, data.density_score)
            for road_id, data in road_densities.items()
            if data.density_score >= threshold
        ]
        
        return sorted(hotspots, key=lambda x: x[1], reverse=True)
    
    def get_congested_junctions(
        self,
        junction_densities: Dict[str, JunctionDensityData]
    ) -> list:
        """
        Get list of HIGH density junctions
        
        Args:
            junction_densities: Dictionary of junction_id -> JunctionDensityData
            
        Returns:
            List of JunctionDensityData with HIGH congestion
        """
        return [
            jd for jd in junction_densities.values()
            if jd.congestion_level == DensityLevel.HIGH
        ]
    
    def calculate_throughput_estimate(
        self,
        metrics: CityWideDensityMetrics
    ) -> float:
        """
        Estimate city-wide throughput capacity
        
        Based on current density and capacity utilization.
        
        Args:
            metrics: Current city metrics
            
        Returns:
            Estimated vehicles/hour throughput
        """
        if metrics.total_road_capacity == 0:
            return 0.0
        
        # Calculate utilization
        utilization = metrics.total_vehicles / metrics.total_road_capacity
        
        # Throughput decreases as utilization increases (congestion effect)
        # At 100% utilization, throughput drops significantly
        efficiency = 1.0 - (utilization ** 2)
        efficiency = max(0.1, efficiency)  # Minimum 10% efficiency
        
        # Base throughput per vehicle
        base_throughput = 30  # vehicles/hour estimated
        
        return metrics.total_vehicles * base_throughput * efficiency
    
    def get_density_distribution(
        self,
        road_densities: Dict[str, RoadDensityData]
    ) -> dict:
        """
        Get distribution of density scores
        
        Args:
            road_densities: Dictionary of road_id -> RoadDensityData
            
        Returns:
            Dictionary with distribution statistics
        """
        if not road_densities:
            return {
                'min': 0,
                'max': 0,
                'mean': 0,
                'median': 0,
                'percentile_90': 0
            }
        
        scores = [data.density_score for data in road_densities.values()]
        scores.sort()
        
        n = len(scores)
        
        return {
            'min': scores[0],
            'max': scores[-1],
            'mean': sum(scores) / n,
            'median': scores[n // 2],
            'percentile_90': scores[int(n * 0.9)] if n > 0 else 0
        }
    
    def compare_to_baseline(
        self,
        current: CityWideDensityMetrics,
        baseline: CityWideDensityMetrics
    ) -> dict:
        """
        Compare current metrics to a baseline
        
        Args:
            current: Current metrics
            baseline: Baseline metrics (e.g., rule-based)
            
        Returns:
            Dictionary with comparison statistics
        """
        if baseline.avg_density_score == 0:
            return {'improvement': 0, 'vehicle_change': 0, 'congestion_change': 0}
        
        density_improvement = (
            (baseline.avg_density_score - current.avg_density_score) /
            baseline.avg_density_score
        ) * 100
        
        vehicle_change = current.total_vehicles - baseline.total_vehicles
        
        congestion_change = current.congestion_points - baseline.congestion_points
        
        return {
            'densityImprovement': round(density_improvement, 2),
            'vehicleChange': vehicle_change,
            'congestionPointChange': congestion_change
        }

