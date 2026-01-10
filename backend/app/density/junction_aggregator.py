"""
Junction Density Aggregator Module

Aggregate density metrics from connected roads to calculate
junction-level density data.

Features:
- Aggregate density from N/E/S/W roads
- Calculate average and max density
- Determine junction congestion level
"""

from typing import Dict
import time

from app.density.density_tracker import (
    RoadDensityData,
    JunctionDensityData,
    DensityLevel
)


class JunctionDensityAggregator:
    """
    Aggregate density metrics for junctions
    
    Combines data from all 4 connected roads (N/E/S/W) to create
    a comprehensive view of junction traffic density.
    """
    
    def __init__(self):
        """Initialize the aggregator"""
        # Congestion thresholds for junction classification
        self.high_threshold = 70
        self.medium_threshold = 40
    
    def calculate_junction_density(
        self,
        junction,
        road_densities: Dict[str, RoadDensityData]
    ) -> JunctionDensityData:
        """
        Calculate aggregated density for junction
        
        Aggregates density from all 4 connected roads (N/E/S/W)
        
        Args:
            junction: Junction object with connected_roads attribute
            road_densities: Dictionary of road_id -> RoadDensityData
            
        Returns:
            JunctionDensityData with aggregated metrics
        """
        junction_id = junction.id if hasattr(junction, 'id') else junction.get('id', str(junction))
        
        data = JunctionDensityData(junction_id=junction_id)
        
        # Direction mapping
        directions = {
            'north': 'density_north',
            'east': 'density_east',
            'south': 'density_south',
            'west': 'density_west'
        }
        
        densities = []
        total_vehicles = 0
        waiting_times = []
        
        # Get connected roads
        connected_roads = None
        if hasattr(junction, 'connected_roads'):
            connected_roads = junction.connected_roads
        elif isinstance(junction, dict):
            connected_roads = junction.get('connected_roads') or junction.get('connectedRoads')
        
        if connected_roads is None:
            return data
        
        for direction, attr_name in directions.items():
            road_id = None
            
            # Get road ID from connected roads
            if hasattr(connected_roads, direction):
                road_id = getattr(connected_roads, direction, None)
            elif isinstance(connected_roads, dict):
                road_id = connected_roads.get(direction)
            
            if road_id and road_id in road_densities:
                road_data = road_densities[road_id]
                density_score = road_data.density_score
                
                # Set directional density
                setattr(data, attr_name, density_score)
                densities.append(density_score)
                total_vehicles += road_data.vehicle_count
        
        # Calculate aggregate metrics
        if densities:
            data.avg_density = sum(densities) / len(densities)
            data.max_density = max(densities)
        
        data.total_vehicles = total_vehicles
        
        # Classify congestion level based on max density
        if data.max_density >= self.high_threshold:
            data.congestion_level = DensityLevel.HIGH
        elif data.max_density >= self.medium_threshold:
            data.congestion_level = DensityLevel.MEDIUM
        else:
            data.congestion_level = DensityLevel.LOW
        
        data.timestamp = time.time()
        
        return data
    
    def get_most_congested_direction(
        self,
        junction_data: JunctionDensityData
    ) -> str:
        """
        Get the direction with highest density
        
        Args:
            junction_data: JunctionDensityData
            
        Returns:
            Direction string ('north', 'east', 'south', or 'west')
        """
        directions = {
            'north': junction_data.density_north,
            'east': junction_data.density_east,
            'south': junction_data.density_south,
            'west': junction_data.density_west
        }
        
        return max(directions, key=directions.get)
    
    def get_congestion_priority_order(
        self,
        junction_data: JunctionDensityData
    ) -> list:
        """
        Get directions ordered by congestion (highest first)
        
        Args:
            junction_data: JunctionDensityData
            
        Returns:
            List of direction strings ordered by density
        """
        directions = {
            'north': junction_data.density_north,
            'east': junction_data.density_east,
            'south': junction_data.density_south,
            'west': junction_data.density_west
        }
        
        return sorted(directions.keys(), key=lambda d: directions[d], reverse=True)
    
    def calculate_imbalance_score(
        self,
        junction_data: JunctionDensityData
    ) -> float:
        """
        Calculate density imbalance across directions
        
        Higher score means more uneven distribution.
        Returns 0 if all directions have same density.
        
        Args:
            junction_data: JunctionDensityData
            
        Returns:
            Imbalance score (0-100)
        """
        densities = [
            junction_data.density_north,
            junction_data.density_east,
            junction_data.density_south,
            junction_data.density_west
        ]
        
        if not densities or max(densities) == 0:
            return 0.0
        
        # Calculate standard deviation as imbalance measure
        avg = sum(densities) / len(densities)
        variance = sum((d - avg) ** 2 for d in densities) / len(densities)
        std_dev = variance ** 0.5
        
        # Normalize to 0-100 scale (assuming max std_dev is ~50)
        return min(100, std_dev * 2)

