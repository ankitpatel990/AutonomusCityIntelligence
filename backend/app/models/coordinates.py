"""
Coordinate System Models

Models for GPS coordinates, canvas coordinates, and coordinate conversion.
Used for mapping between real-world GPS positions and canvas pixels.
"""

from pydantic import BaseModel, Field
from typing import Optional


class MapBounds(BaseModel):
    """
    Geographic bounding box
    
    Defines the area covered by a map in GPS coordinates.
    """
    north: float                          # Maximum latitude
    south: float                          # Minimum latitude
    east: float                           # Maximum longitude
    west: float                           # Minimum longitude
    
    class Config:
        json_schema_extra = {
            "example": {
                "north": 23.2500,
                "south": 23.2000,
                "east": 72.6500,
                "west": 72.6000
            }
        }
    
    @property
    def lat_range(self) -> float:
        """Get latitude range"""
        return self.north - self.south
    
    @property
    def lon_range(self) -> float:
        """Get longitude range"""
        return self.east - self.west
    
    @property
    def center(self) -> tuple[float, float]:
        """Get center point (lat, lon)"""
        return (
            (self.north + self.south) / 2,
            (self.east + self.west) / 2
        )
    
    def contains(self, lat: float, lon: float) -> bool:
        """Check if a point is within bounds"""
        return (
            self.south <= lat <= self.north and
            self.west <= lon <= self.east
        )


class GPSCoordinate(BaseModel):
    """GPS coordinate (latitude, longitude)"""
    lat: float                            # Latitude (-90 to 90)
    lon: float                            # Longitude (-180 to 180)
    
    class Config:
        json_schema_extra = {
            "example": {"lat": 23.2156, "lon": 72.6369}
        }


class CanvasCoordinate(BaseModel):
    """Canvas coordinate in pixels"""
    x: float
    y: float
    
    class Config:
        json_schema_extra = {
            "example": {"x": 600, "y": 400}
        }


class CoordinateConverter:
    """
    Convert between GPS and Canvas coordinates
    
    Uses linear projection which is accurate enough for city-scale maps.
    For larger areas, consider using proper map projections.
    """
    
    def __init__(
        self, 
        canvas_width: int, 
        canvas_height: int, 
        map_bounds: MapBounds,
        padding: int = 20
    ):
        """
        Initialize converter
        
        Args:
            canvas_width: Width of canvas in pixels
            canvas_height: Height of canvas in pixels
            map_bounds: Geographic bounds of the map
            padding: Padding from canvas edges in pixels
        """
        self.canvas_width = canvas_width
        self.canvas_height = canvas_height
        self.map_bounds = map_bounds
        self.padding = padding
        
        # Pre-calculate ranges for efficiency
        self.lat_range = map_bounds.north - map_bounds.south
        self.lon_range = map_bounds.east - map_bounds.west
        
        # Usable canvas area
        self.usable_width = canvas_width - 2 * padding
        self.usable_height = canvas_height - 2 * padding
    
    def gps_to_canvas(self, lat: float, lon: float) -> CanvasCoordinate:
        """
        Convert GPS coordinates to canvas pixels
        
        Args:
            lat: Latitude
            lon: Longitude
            
        Returns:
            CanvasCoordinate with x, y in pixels
        """
        # Normalize to 0-1 range
        x_normalized = (lon - self.map_bounds.west) / self.lon_range
        # Note: Y is inverted because canvas Y increases downward
        y_normalized = (self.map_bounds.north - lat) / self.lat_range
        
        # Scale to canvas with padding
        x = self.padding + x_normalized * self.usable_width
        y = self.padding + y_normalized * self.usable_height
        
        return CanvasCoordinate(x=round(x, 2), y=round(y, 2))
    
    def canvas_to_gps(self, x: float, y: float) -> GPSCoordinate:
        """
        Convert canvas pixels to GPS coordinates
        
        Args:
            x: X position in pixels
            y: Y position in pixels
            
        Returns:
            GPSCoordinate with lat, lon
        """
        # Normalize from canvas space
        x_normalized = (x - self.padding) / self.usable_width
        y_normalized = (y - self.padding) / self.usable_height
        
        # Convert to GPS
        lon = self.map_bounds.west + x_normalized * self.lon_range
        lat = self.map_bounds.north - y_normalized * self.lat_range
        
        return GPSCoordinate(lat=round(lat, 6), lon=round(lon, 6))
    
    def gps_to_canvas_batch(self, points: list[tuple[float, float]]) -> list[CanvasCoordinate]:
        """Convert multiple GPS points to canvas coordinates"""
        return [self.gps_to_canvas(lat, lon) for lat, lon in points]
    
    def canvas_to_gps_batch(self, points: list[tuple[float, float]]) -> list[GPSCoordinate]:
        """Convert multiple canvas points to GPS coordinates"""
        return [self.canvas_to_gps(x, y) for x, y in points]


# Pre-defined map areas for Gandhinagar
GANDHINAGAR_BOUNDS = MapBounds(
    north=23.2500,
    south=23.1800,
    east=72.6800,
    west=72.6000
)

GIFT_CITY_BOUNDS = MapBounds(
    north=23.1700,
    south=23.1500,
    east=72.7000,
    west=72.6700
)

SECTOR_5_BOUNDS = MapBounds(
    north=23.2300,
    south=23.2100,
    east=72.6500,
    west=72.6200
)

