"""
Live Traffic Service

Fetches real-time traffic data from TomTom API and integrates it
with the simulation system. Implements FRD-01 v2.0 Live Traffic API Integration.

Features:
- TomTom Traffic Flow API integration
- Response caching with TTL
- Parallel fetching for multiple roads
- Fallback to simulation data on API failure
- Congestion level calculation
"""

import aiohttp
import asyncio
import os
import time
import json
from typing import Optional, Dict, List, Any
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum

from app.models import LiveTrafficData, TrafficIncident


class TrafficAPIProvider(str, Enum):
    """Supported traffic API providers"""
    TOMTOM = "tomtom"
    GOOGLE = "google"  # Future support
    HERE = "here"  # Future support


class APIStatus(BaseModel):
    """Status of the traffic API connection"""
    provider: TrafficAPIProvider = TrafficAPIProvider.TOMTOM
    is_configured: bool = False
    last_request_time: Optional[float] = None
    last_success_time: Optional[float] = None
    request_count: int = 0
    error_count: int = 0
    cache_hit_count: int = 0
    cache_miss_count: int = 0
    avg_response_time: float = 0.0


class CacheEntry(BaseModel):
    """Cache entry for API responses"""
    data: LiveTrafficData
    expires_at: float
    cached_at: float = Field(default_factory=time.time)


class LiveTrafficService:
    """
    Fetch live traffic data from TomTom API
    
    Usage:
        service = LiveTrafficService()
        await service.initialize()
        
        # Get traffic for a road segment
        data = await service.get_traffic_for_road(
            road_id="R-1-2",
            start_lat=23.20, start_lon=72.60,
            end_lat=23.25, end_lon=72.65
        )
    """
    
    def __init__(self, api_key: Optional[str] = None, cache_ttl: int = 60):
        """
        Initialize the Live Traffic Service
        
        Args:
            api_key: TomTom API key (defaults to TOMTOM_API_KEY env var)
            cache_ttl: Cache time-to-live in seconds (default 60s)
        """
        self.api_key = api_key or os.getenv("TOMTOM_API_KEY", "")
        self.base_url = "https://api.tomtom.com/traffic/services/4/flowSegmentData"
        self.cache_ttl = cache_ttl
        
        # Response cache
        self._cache: Dict[str, CacheEntry] = {}
        
        # Session for HTTP requests
        self._session: Optional[aiohttp.ClientSession] = None
        
        # Status tracking
        self._status = APIStatus(
            is_configured=bool(self.api_key)
        )
        
        # Request timing
        self._response_times: List[float] = []
        self._max_response_times = 100  # Keep last 100 for averaging
    
    async def initialize(self):
        """Initialize the HTTP session"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=10, connect=5)
            self._session = aiohttp.ClientSession(timeout=timeout)
    
    async def close(self):
        """Close the HTTP session"""
        if self._session and not self._session.closed:
            await self._session.close()
    
    @property
    def is_configured(self) -> bool:
        """Check if API key is configured"""
        return bool(self.api_key)
    
    @property
    def status(self) -> APIStatus:
        """Get current API status"""
        if self._response_times:
            self._status.avg_response_time = sum(self._response_times) / len(self._response_times)
        return self._status
    
    def _get_cache_key(self, road_id: str, lat: float, lon: float) -> str:
        """Generate cache key for a location"""
        # Round coordinates to 4 decimal places for cache key
        lat_rounded = round(lat, 4)
        lon_rounded = round(lon, 4)
        return f"traffic_{road_id}_{lat_rounded}_{lon_rounded}"
    
    def _get_cached(self, cache_key: str) -> Optional[LiveTrafficData]:
        """Get cached response if valid"""
        if cache_key in self._cache:
            entry = self._cache[cache_key]
            if time.time() < entry.expires_at:
                self._status.cache_hit_count += 1
                return entry.data
            else:
                # Remove expired entry
                del self._cache[cache_key]
        
        self._status.cache_miss_count += 1
        return None
    
    def _set_cache(self, cache_key: str, data: LiveTrafficData):
        """Cache a response"""
        self._cache[cache_key] = CacheEntry(
            data=data,
            expires_at=time.time() + self.cache_ttl
        )
    
    def _calculate_congestion_level(self, current_speed: float, free_flow_speed: float) -> str:
        """
        Calculate congestion level from speed ratio
        
        Args:
            current_speed: Current traffic speed (km/h)
            free_flow_speed: Free flow speed (km/h)
            
        Returns:
            Congestion level: LOW, MEDIUM, HIGH, or JAM
        """
        if free_flow_speed <= 0:
            return "LOW"
        
        ratio = current_speed / free_flow_speed
        
        if ratio >= 0.8:
            return "LOW"
        elif ratio >= 0.5:
            return "MEDIUM"
        elif ratio >= 0.2:
            return "HIGH"
        else:
            return "JAM"
    
    async def get_traffic_for_road(
        self,
        road_id: str,
        start_lat: float,
        start_lon: float,
        end_lat: Optional[float] = None,
        end_lon: Optional[float] = None
    ) -> Optional[LiveTrafficData]:
        """
        Fetch traffic data for a road segment from TomTom API
        
        Args:
            road_id: Internal road ID
            start_lat: Start latitude
            start_lon: Start longitude
            end_lat: End latitude (optional, will use midpoint if provided)
            end_lon: End longitude (optional)
            
        Returns:
            LiveTrafficData or None if API fails
        """
        # Use midpoint if end coordinates provided
        if end_lat is not None and end_lon is not None:
            query_lat = (start_lat + end_lat) / 2
            query_lon = (start_lon + end_lon) / 2
        else:
            query_lat = start_lat
            query_lon = start_lon
        
        # Check cache first
        cache_key = self._get_cache_key(road_id, query_lat, query_lon)
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        # Check if API is configured
        if not self.is_configured:
            print(f"[LiveTraffic] API key not configured, returning simulated data for {road_id}")
            return self._generate_simulated_data(road_id)
        
        # Initialize session if needed
        await self.initialize()
        
        # Build API request
        # TomTom Flow Segment Data API
        # https://developer.tomtom.com/traffic-api/documentation/traffic-flow/flow-segment-data
        url = f"{self.base_url}/absolute/10/json"
        params = {
            'key': self.api_key,
            'point': f"{query_lat},{query_lon}",
            'unit': 'KMPH',
            'openLr': 'false'
        }
        
        start_time = time.time()
        self._status.request_count += 1
        self._status.last_request_time = start_time
        
        try:
            async with self._session.get(url, params=params) as response:
                response_time = (time.time() - start_time) * 1000
                self._response_times.append(response_time)
                if len(self._response_times) > self._max_response_times:
                    self._response_times.pop(0)
                
                if response.status == 200:
                    data = await response.json()
                    
                    # Parse TomTom response
                    flow_data = data.get('flowSegmentData', {})
                    
                    current_speed = flow_data.get('currentSpeed', 0)
                    free_flow_speed = flow_data.get('freeFlowSpeed', 50)
                    confidence = flow_data.get('confidence', 50)
                    
                    # Calculate congestion level
                    congestion_level = self._calculate_congestion_level(
                        current_speed, free_flow_speed
                    )
                    
                    # Build response
                    traffic_data = LiveTrafficData(
                        road_id=road_id,
                        current_speed=current_speed,
                        free_flow_speed=free_flow_speed,
                        congestion_level=congestion_level,
                        confidence=confidence,
                        timestamp=datetime.utcnow().isoformat() + "Z",
                        expires_at=time.time() + self.cache_ttl,
                        source="API",
                        provider="tomtom"
                    )
                    
                    # Cache the response
                    self._set_cache(cache_key, traffic_data)
                    
                    self._status.last_success_time = time.time()
                    
                    return traffic_data
                    
                elif response.status == 401:
                    print(f"[LiveTraffic] API key invalid or expired")
                    self._status.error_count += 1
                    return self._generate_simulated_data(road_id)
                    
                elif response.status == 429:
                    print(f"[LiveTraffic] Rate limit exceeded")
                    self._status.error_count += 1
                    return self._generate_simulated_data(road_id)
                    
                else:
                    print(f"[LiveTraffic] API error {response.status} for {road_id}")
                    self._status.error_count += 1
                    return self._generate_simulated_data(road_id)
                    
        except asyncio.TimeoutError:
            print(f"[LiveTraffic] Request timeout for {road_id}")
            self._status.error_count += 1
            return self._generate_simulated_data(road_id)
            
        except aiohttp.ClientError as e:
            print(f"[LiveTraffic] Network error for {road_id}: {e}")
            self._status.error_count += 1
            return self._generate_simulated_data(road_id)
            
        except Exception as e:
            print(f"[LiveTraffic] Unexpected error for {road_id}: {e}")
            self._status.error_count += 1
            return self._generate_simulated_data(road_id)
    
    async def get_traffic_for_roads(
        self,
        roads: List[Dict[str, Any]]
    ) -> Dict[str, LiveTrafficData]:
        """
        Fetch traffic data for multiple roads in parallel
        
        Args:
            roads: List of road dictionaries with:
                - id: Road ID
                - start_lat, start_lon: Start coordinates
                - end_lat, end_lon: End coordinates
                
        Returns:
            Dictionary mapping road_id to LiveTrafficData
        """
        tasks = []
        
        for road in roads:
            task = self.get_traffic_for_road(
                road_id=road['id'],
                start_lat=road.get('start_lat', road.get('startLat', 0)),
                start_lon=road.get('start_lon', road.get('startLon', 0)),
                end_lat=road.get('end_lat', road.get('endLat')),
                end_lon=road.get('end_lon', road.get('endLon'))
            )
            tasks.append(task)
        
        # Execute all requests in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Build result dictionary
        traffic_map: Dict[str, LiveTrafficData] = {}
        
        for road, result in zip(roads, results):
            if isinstance(result, LiveTrafficData):
                traffic_map[road['id']] = result
            elif isinstance(result, Exception):
                print(f"[LiveTraffic] Error fetching {road['id']}: {result}")
                # Use simulated data for failed roads
                traffic_map[road['id']] = self._generate_simulated_data(road['id'])
        
        return traffic_map
    
    def _generate_simulated_data(self, road_id: str) -> LiveTrafficData:
        """
        Generate simulated traffic data when API is unavailable
        
        Args:
            road_id: Road ID for the simulated data
            
        Returns:
            Simulated LiveTrafficData
        """
        import random
        
        # Generate somewhat realistic values
        free_flow = 50.0
        # Vary speed based on time of day (simple simulation)
        hour = datetime.now().hour
        
        # Rush hour simulation (8-10am, 5-7pm)
        if 8 <= hour <= 10 or 17 <= hour <= 19:
            current_speed = random.uniform(15, 35)
        elif 23 <= hour or hour <= 5:
            current_speed = random.uniform(40, 50)
        else:
            current_speed = random.uniform(25, 45)
        
        congestion_level = self._calculate_congestion_level(current_speed, free_flow)
        
        return LiveTrafficData(
            road_id=road_id,
            current_speed=round(current_speed, 1),
            free_flow_speed=free_flow,
            congestion_level=congestion_level,
            confidence=50.0,  # Lower confidence for simulated data
            timestamp=datetime.utcnow().isoformat() + "Z",
            expires_at=time.time() + self.cache_ttl,
            source="SIMULATION",
            provider=None
        )
    
    def clear_cache(self):
        """Clear all cached responses"""
        self._cache.clear()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_hits = self._status.cache_hit_count
        total_misses = self._status.cache_miss_count
        total = total_hits + total_misses
        
        return {
            "entries": len(self._cache),
            "hits": total_hits,
            "misses": total_misses,
            "hit_rate": (total_hits / total * 100) if total > 0 else 0,
            "ttl_seconds": self.cache_ttl
        }


# Global service instance
_live_traffic_service: Optional[LiveTrafficService] = None


def get_live_traffic_service() -> LiveTrafficService:
    """Get the global LiveTrafficService instance"""
    global _live_traffic_service
    if _live_traffic_service is None:
        _live_traffic_service = LiveTrafficService()
    return _live_traffic_service


async def init_live_traffic_service():
    """Initialize the global LiveTrafficService"""
    service = get_live_traffic_service()
    await service.initialize()
    return service


async def close_live_traffic_service():
    """Close the global LiveTrafficService"""
    global _live_traffic_service
    if _live_traffic_service:
        await _live_traffic_service.close()
        _live_traffic_service = None

