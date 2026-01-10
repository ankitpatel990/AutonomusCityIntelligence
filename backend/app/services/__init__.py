"""
Services Package

Contains all business logic services for the Traffic Intelligence System.

Services:
- LiveTrafficService: Fetches real-time traffic data from TomTom API
- MapLoaderService: Loads real city geography from OpenStreetMap
"""

from .live_traffic_service import (
    LiveTrafficService,
    get_live_traffic_service,
    init_live_traffic_service,
    close_live_traffic_service,
    TrafficAPIProvider,
    APIStatus,
)

from .map_loader_service import (
    MapLoaderService,
    get_map_loader_service,
    RealJunction,
    RealRoad,
    OSMLoadResult,
    PredefinedArea,
    PREDEFINED_AREAS,
)

__all__ = [
    # Live Traffic Service
    "LiveTrafficService",
    "get_live_traffic_service",
    "init_live_traffic_service",
    "close_live_traffic_service",
    "TrafficAPIProvider",
    "APIStatus",
    
    # Map Loader Service
    "MapLoaderService",
    "get_map_loader_service",
    "RealJunction",
    "RealRoad",
    "OSMLoadResult",
    "PredefinedArea",
    "PREDEFINED_AREAS",
]
