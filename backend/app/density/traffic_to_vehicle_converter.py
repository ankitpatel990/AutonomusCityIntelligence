"""
Traffic to Vehicle Converter Module

Convert TomTom API traffic data to vehicle objects for visualization.
Implements FRD-02 FR-02.1A, FR-02.2A requirements.

Features:
- Congestion level to vehicle count conversion
- Vehicle spawning on roads based on API data
- Number plate generation
- Heading calculation from road direction
"""

from typing import List, Dict, Optional, Any
import random
import string
import math
import time

from app.models.vehicle import Vehicle, Position
from app.models.live_traffic import LiveTrafficData


class TrafficToVehicleConverter:
    """
    Convert TomTom API traffic data to vehicle objects
    
    Maps abstract congestion levels to concrete vehicle counts
    and spawns vehicles along roads based on API data.
    """
    
    # Density mapping: vehicles per kilometer by congestion level
    DENSITY_MAP = {
        'LOW': 5,
        'MEDIUM': 15,
        'HIGH': 30,
        'JAM': 50
    }
    
    # Vehicle type distribution
    VEHICLE_TYPES = {
        'car': 0.70,      # 70% cars
        'bike': 0.25,     # 25% bikes
        'ambulance': 0.05  # 5% ambulances
    }
    
    def __init__(self, config: dict = None):
        """
        Initialize the converter
        
        Args:
            config: Configuration dictionary (optional)
        """
        if config is None:
            config = {}
        
        # Get density mapping from config if available
        live_api_config = config.get('liveApi', {})
        congestion_mapping = live_api_config.get('congestionMapping', {})
        
        if congestion_mapping:
            for level, data in congestion_mapping.items():
                if 'vehiclesPerKm' in data:
                    self.DENSITY_MAP[level] = data['vehiclesPerKm']
    
    def calculate_vehicle_count(
        self,
        congestion_level: str,
        road_length_meters: float
    ) -> int:
        """
        Calculate how many vehicles to spawn based on API congestion
        
        Args:
            congestion_level: LOW/MEDIUM/HIGH/JAM from TomTom
            road_length_meters: Road length in meters
            
        Returns:
            Number of vehicles to spawn (minimum 1)
        """
        density_per_km = self.DENSITY_MAP.get(congestion_level, 10)
        road_length_km = road_length_meters / 1000
        vehicle_count = int(density_per_km * road_length_km)
        
        return max(1, vehicle_count)
    
    def spawn_vehicles_for_road(
        self,
        road,
        live_traffic: LiveTrafficData,
        coordinate_converter=None
    ) -> List[Vehicle]:
        """
        Create vehicle objects matching API congestion
        
        Distributes vehicles evenly along the road with speeds
        matching the API-reported traffic conditions.
        
        Args:
            road: Real road with GPS coordinates
            live_traffic: TomTom API data
            coordinate_converter: GPS to Canvas converter (optional)
            
        Returns:
            List of spawned Vehicle objects
        """
        # Get road attributes
        road_id = road.id if hasattr(road, 'id') else road.get('id')
        road_length = road.length if hasattr(road, 'length') else road.get('length', 100)
        
        # Get GPS coordinates
        start_lat = road.start_lat if hasattr(road, 'start_lat') else road.get('start_lat', road.get('startLat', 0))
        start_lon = road.start_lon if hasattr(road, 'start_lon') else road.get('start_lon', road.get('startLon', 0))
        end_lat = road.end_lat if hasattr(road, 'end_lat') else road.get('end_lat', road.get('endLat', 0))
        end_lon = road.end_lon if hasattr(road, 'end_lon') else road.get('end_lon', road.get('endLon', 0))
        
        # Get canvas coordinates
        start_x = road.start_x if hasattr(road, 'start_x') else road.get('start_x', road.get('startX', 0))
        start_y = road.start_y if hasattr(road, 'start_y') else road.get('start_y', road.get('startY', 0))
        end_x = road.end_x if hasattr(road, 'end_x') else road.get('end_x', road.get('endX', 0))
        end_y = road.end_y if hasattr(road, 'end_y') else road.get('end_y', road.get('endY', 0))
        
        # Get destination junction
        end_junction = road.end_junction_id if hasattr(road, 'end_junction_id') else road.get('end_junction_id', road.get('endJunctionId', ''))
        
        # Calculate vehicle count from congestion level
        vehicle_count = self.calculate_vehicle_count(
            live_traffic.congestion_level,
            road_length
        )
        
        vehicles = []
        
        for i in range(vehicle_count):
            # Position ratio along road (distribute evenly with some randomness)
            base_ratio = (i + 0.5) / vehicle_count
            jitter = random.uniform(-0.1, 0.1) / vehicle_count
            position_ratio = max(0, min(1, base_ratio + jitter))
            
            # Interpolate position
            if coordinate_converter and start_lat and start_lon and end_lat and end_lon:
                # Use GPS coordinates
                lat = start_lat + (end_lat - start_lat) * position_ratio
                lon = start_lon + (end_lon - start_lon) * position_ratio
                
                canvas_pos = coordinate_converter.gps_to_canvas(lat, lon)
                canvas_x = canvas_pos.x
                canvas_y = canvas_pos.y
            else:
                # Use canvas coordinates directly
                canvas_x = start_x + (end_x - start_x) * position_ratio
                canvas_y = start_y + (end_y - start_y) * position_ratio
            
            # Generate plate number
            plate = self._generate_plate()
            
            # Select vehicle type
            vehicle_type = self._select_vehicle_type()
            
            # Calculate heading
            heading = self._calculate_heading(start_x, start_y, end_x, end_y)
            
            # Create vehicle
            vehicle = Vehicle(
                number_plate=plate,
                type=vehicle_type,
                position=Position(x=canvas_x, y=canvas_y),
                speed=live_traffic.current_speed,
                heading=heading,
                current_road=road_id,
                destination=end_junction,
                source='LIVE_TRAFFIC_API'
            )
            
            # Set GPS coordinates if available
            if start_lat and start_lon and end_lat and end_lon:
                vehicle.lat = start_lat + (end_lat - start_lat) * position_ratio
                vehicle.lon = start_lon + (end_lon - start_lon) * position_ratio
            
            vehicles.append(vehicle)
        
        return vehicles
    
    def _generate_plate(self) -> str:
        """
        Generate random Indian number plate
        
        Format: XX00XX0000 (e.g., GJ01AB1234)
        
        Returns:
            Number plate string
        """
        # State codes (Gujarat variations for Gandhinagar demo)
        state = random.choice(['GJ', 'GJ', 'GJ', 'MH', 'RJ', 'DL'])
        district = random.randint(1, 50)
        letters = ''.join(random.choices(string.ascii_uppercase, k=2))
        numbers = random.randint(1000, 9999)
        
        return f"{state}{district:02d}{letters}{numbers}"
    
    def _select_vehicle_type(self) -> str:
        """
        Select vehicle type based on distribution
        
        Returns:
            Vehicle type: 'car', 'bike', or 'ambulance'
        """
        rand = random.random()
        cumulative = 0
        
        for vehicle_type, probability in self.VEHICLE_TYPES.items():
            cumulative += probability
            if rand <= cumulative:
                return vehicle_type
        
        return 'car'  # Default
    
    def _calculate_heading(
        self,
        start_x: float,
        start_y: float,
        end_x: float,
        end_y: float
    ) -> float:
        """
        Calculate heading angle from road direction
        
        Args:
            start_x, start_y: Start position
            end_x, end_y: End position
            
        Returns:
            Heading angle in degrees (0-360)
        """
        dx = end_x - start_x
        dy = end_y - start_y
        
        # atan2 returns angle in radians from -pi to pi
        angle_rad = math.atan2(dy, dx)
        
        # Convert to degrees (0-360)
        angle_deg = math.degrees(angle_rad)
        
        # Normalize to 0-360
        return (angle_deg + 360) % 360
    
    def update_vehicles_from_api(
        self,
        existing_vehicles: List[Vehicle],
        roads: List,
        traffic_data: Dict[str, LiveTrafficData],
        coordinate_converter=None
    ) -> List[Vehicle]:
        """
        Update vehicle list based on new API data
        
        Adjusts vehicle counts on roads to match API congestion levels.
        Preserves existing vehicles where possible.
        
        Args:
            existing_vehicles: Current vehicle list
            roads: List of road objects
            traffic_data: Dictionary of road_id -> LiveTrafficData
            coordinate_converter: GPS to Canvas converter
            
        Returns:
            Updated list of vehicles
        """
        # Group existing vehicles by road
        vehicles_by_road: Dict[str, List[Vehicle]] = {}
        other_vehicles = []  # Vehicles not on tracked roads
        
        for vehicle in existing_vehicles:
            road_id = vehicle.current_road
            if road_id and road_id in traffic_data:
                if road_id not in vehicles_by_road:
                    vehicles_by_road[road_id] = []
                vehicles_by_road[road_id].append(vehicle)
            else:
                other_vehicles.append(vehicle)
        
        updated_vehicles = list(other_vehicles)
        
        for road in roads:
            road_id = road.id if hasattr(road, 'id') else road.get('id')
            
            if road_id not in traffic_data:
                # Keep existing vehicles if no API data
                if road_id in vehicles_by_road:
                    updated_vehicles.extend(vehicles_by_road[road_id])
                continue
            
            live_traffic = traffic_data[road_id]
            road_length = road.length if hasattr(road, 'length') else road.get('length', 100)
            
            # Calculate target vehicle count
            target_count = self.calculate_vehicle_count(
                live_traffic.congestion_level,
                road_length
            )
            
            # Get existing vehicles on this road
            current_vehicles = vehicles_by_road.get(road_id, [])
            current_count = len(current_vehicles)
            
            if current_count == target_count:
                # Perfect match - keep all
                updated_vehicles.extend(current_vehicles)
            elif current_count > target_count:
                # Too many vehicles - remove some
                updated_vehicles.extend(current_vehicles[:target_count])
            else:
                # Too few vehicles - keep existing and spawn more
                updated_vehicles.extend(current_vehicles)
                
                # Spawn additional vehicles
                additional = self.spawn_vehicles_for_road(
                    road,
                    live_traffic,
                    coordinate_converter
                )
                
                # Only add the difference
                needed = target_count - current_count
                updated_vehicles.extend(additional[:needed])
        
        return updated_vehicles
    
    def get_congestion_summary(
        self,
        traffic_data: Dict[str, LiveTrafficData]
    ) -> dict:
        """
        Get summary of congestion levels across all roads
        
        Args:
            traffic_data: Dictionary of road_id -> LiveTrafficData
            
        Returns:
            Summary dictionary with counts per congestion level
        """
        summary = {
            'LOW': 0,
            'MEDIUM': 0,
            'HIGH': 0,
            'JAM': 0,
            'total': len(traffic_data)
        }
        
        for data in traffic_data.values():
            level = data.congestion_level
            if level in summary:
                summary[level] += 1
        
        return summary

