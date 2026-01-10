"""
Density Exporter Module

Export density data to various formats for analysis and UI visualization.
Implements FRD-02 FR-02.10 requirements.

Features:
- CSV export with configurable columns
- JSON export for API consumption
- UI-ready data formatting with colors
- Time-filtered exports
"""

import csv
import json
from io import StringIO
from typing import Dict, List
import time

from app.density.density_tracker import (
    RoadDensityData,
    JunctionDensityData,
    DensityLevel
)


class DensityExporter:
    """
    Export density data to various formats
    
    Supports CSV, JSON, and UI-ready formats for frontend visualization.
    """
    
    # Color mapping for UI visualization
    COLOR_MAP = {
        DensityLevel.LOW: '#2ed573',      # Green
        DensityLevel.MEDIUM: '#ffa502',    # Yellow/Orange
        DensityLevel.HIGH: '#ff4757'       # Red
    }
    
    def __init__(self):
        """Initialize the exporter"""
        pass
    
    def export_to_csv(
        self,
        road_densities: Dict[str, RoadDensityData],
        include_headers: bool = True
    ) -> str:
        """
        Export density data to CSV format
        
        CSV Columns:
        timestamp, road_id, vehicle_count, density_score, classification
        
        Args:
            road_densities: Dictionary of road_id -> RoadDensityData
            include_headers: Whether to include column headers
            
        Returns:
            CSV string
        """
        output = StringIO()
        writer = csv.writer(output)
        
        # Header
        if include_headers:
            writer.writerow([
                'timestamp',
                'road_id',
                'vehicle_count',
                'density_score',
                'classification',
                'capacity'
            ])
        
        # Data rows (sorted by road_id for consistency)
        for road_id in sorted(road_densities.keys()):
            data = road_densities[road_id]
            writer.writerow([
                data.timestamp,
                road_id,
                data.vehicle_count,
                f"{data.density_score:.2f}",
                data.classification.value,
                data.capacity
            ])
        
        return output.getvalue()
    
    def export_junctions_to_csv(
        self,
        junction_densities: Dict[str, JunctionDensityData]
    ) -> str:
        """
        Export junction density data to CSV
        
        Args:
            junction_densities: Dictionary of junction_id -> JunctionDensityData
            
        Returns:
            CSV string
        """
        output = StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            'timestamp',
            'junction_id',
            'density_north',
            'density_east',
            'density_south',
            'density_west',
            'avg_density',
            'max_density',
            'total_vehicles',
            'congestion_level'
        ])
        
        # Data rows
        for junction_id in sorted(junction_densities.keys()):
            data = junction_densities[junction_id]
            writer.writerow([
                data.timestamp,
                junction_id,
                f"{data.density_north:.2f}",
                f"{data.density_east:.2f}",
                f"{data.density_south:.2f}",
                f"{data.density_west:.2f}",
                f"{data.avg_density:.2f}",
                f"{data.max_density:.2f}",
                data.total_vehicles,
                data.congestion_level.value
            ])
        
        return output.getvalue()
    
    def format_for_ui(
        self,
        road_densities: Dict[str, RoadDensityData]
    ) -> List[dict]:
        """
        Format density data for UI visualization
        
        Returns list of objects with color-coded density info
        suitable for Canvas overlays.
        
        Args:
            road_densities: Dictionary of road_id -> RoadDensityData
            
        Returns:
            List of UI-ready density objects
        """
        ui_data = []
        
        for road_id, data in road_densities.items():
            color = self.COLOR_MAP.get(data.classification, '#cccccc')
            
            ui_data.append({
                'roadId': road_id,
                'vehicleCount': data.vehicle_count,
                'densityScore': round(data.density_score, 1),
                'classification': data.classification.value,
                'color': color,
                'opacity': self._calculate_opacity(data.density_score),
                'timestamp': data.timestamp
            })
        
        return ui_data
    
    def format_junctions_for_ui(
        self,
        junction_densities: Dict[str, JunctionDensityData]
    ) -> List[dict]:
        """
        Format junction density data for UI visualization
        
        Args:
            junction_densities: Dictionary of junction_id -> JunctionDensityData
            
        Returns:
            List of UI-ready junction density objects
        """
        ui_data = []
        
        for junction_id, data in junction_densities.items():
            color = self.COLOR_MAP.get(data.congestion_level, '#cccccc')
            
            ui_data.append({
                'junctionId': junction_id,
                'densities': {
                    'north': round(data.density_north, 1),
                    'east': round(data.density_east, 1),
                    'south': round(data.density_south, 1),
                    'west': round(data.density_west, 1)
                },
                'avgDensity': round(data.avg_density, 1),
                'totalVehicles': data.total_vehicles,
                'congestionLevel': data.congestion_level.value,
                'color': color,
                'timestamp': data.timestamp
            })
        
        return ui_data
    
    def _calculate_opacity(self, density_score: float) -> float:
        """
        Calculate overlay opacity based on density score
        
        Higher density = higher opacity for better visibility.
        
        Args:
            density_score: Score from 0-100
            
        Returns:
            Opacity value from 0.3 to 1.0
        """
        # Map 0-100 to 0.3-1.0
        min_opacity = 0.3
        max_opacity = 1.0
        
        normalized = density_score / 100
        return min_opacity + (max_opacity - min_opacity) * normalized
    
    def export_to_json(
        self,
        road_densities: Dict[str, RoadDensityData],
        junction_densities: Dict[str, JunctionDensityData],
        include_metadata: bool = True
    ) -> str:
        """
        Export complete density data to JSON
        
        Args:
            road_densities: Dictionary of road_id -> RoadDensityData
            junction_densities: Dictionary of junction_id -> JunctionDensityData
            include_metadata: Whether to include export metadata
            
        Returns:
            JSON string
        """
        data = {
            'roads': {
                road_id: {
                    'vehicleCount': d.vehicle_count,
                    'densityScore': round(d.density_score, 2),
                    'classification': d.classification.value,
                    'capacity': d.capacity,
                    'timestamp': d.timestamp
                }
                for road_id, d in road_densities.items()
            },
            'junctions': {
                junction_id: {
                    'densityNorth': round(d.density_north, 2),
                    'densityEast': round(d.density_east, 2),
                    'densitySouth': round(d.density_south, 2),
                    'densityWest': round(d.density_west, 2),
                    'avgDensity': round(d.avg_density, 2),
                    'maxDensity': round(d.max_density, 2),
                    'totalVehicles': d.total_vehicles,
                    'congestionLevel': d.congestion_level.value,
                    'timestamp': d.timestamp
                }
                for junction_id, d in junction_densities.items()
            }
        }
        
        if include_metadata:
            data['metadata'] = {
                'exportedAt': time.time(),
                'totalRoads': len(road_densities),
                'totalJunctions': len(junction_densities),
                'format': 'TrafficDensityExport',
                'version': '1.0'
            }
        
        return json.dumps(data, indent=2)
    
    def export_history_to_csv(
        self,
        history: List,  # List of DensitySnapshot
        road_id: str = None
    ) -> str:
        """
        Export density history to CSV
        
        Args:
            history: List of DensitySnapshot objects
            road_id: Optional filter by road ID
            
        Returns:
            CSV string
        """
        output = StringIO()
        writer = csv.writer(output)
        
        writer.writerow([
            'timestamp',
            'road_id',
            'vehicle_count',
            'density_score',
            'classification'
        ])
        
        for snapshot in history:
            if road_id and snapshot.road_id != road_id:
                continue
            
            writer.writerow([
                snapshot.timestamp,
                snapshot.road_id,
                snapshot.vehicle_count,
                f"{snapshot.density_score:.2f}",
                snapshot.classification.value
            ])
        
        return output.getvalue()
    
    def get_color_for_classification(
        self,
        classification: DensityLevel
    ) -> str:
        """
        Get hex color for a density classification
        
        Args:
            classification: DensityLevel enum
            
        Returns:
            Hex color code
        """
        return self.COLOR_MAP.get(classification, '#cccccc')
    
    def get_gradient_color(
        self,
        density_score: float
    ) -> str:
        """
        Get gradient color based on density score
        
        Interpolates between green (0) and red (100).
        
        Args:
            density_score: Score from 0-100
            
        Returns:
            Hex color code
        """
        # Clamp score to 0-100
        score = max(0, min(100, density_score))
        
        # Interpolate RGB
        if score < 50:
            # Green to Yellow
            ratio = score / 50
            r = int(46 + (255 - 46) * ratio)
            g = int(213 + (165 - 213) * ratio)
            b = int(115 + (2 - 115) * ratio)
        else:
            # Yellow to Red
            ratio = (score - 50) / 50
            r = int(255 + (255 - 255) * ratio)
            g = int(165 + (71 - 165) * ratio)
            b = int(2 + (87 - 2) * ratio)
        
        return f'#{r:02x}{g:02x}{b:02x}'

