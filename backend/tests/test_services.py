"""
Service Tests

Tests for LiveTrafficService and MapLoaderService.
Covers PROMPT 9 (TomTom API) and PROMPT 10 (OSMnx) requirements.
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.live_traffic_service import (
    LiveTrafficService,
    get_live_traffic_service,
    TrafficAPIProvider,
)
from app.services.map_loader_service import (
    MapLoaderService,
    get_map_loader_service,
    PREDEFINED_AREAS,
    OSMLoadResult,
)
from app.models import MapBounds, LiveTrafficData


# ============================================
# Live Traffic Service Tests
# ============================================

class TestLiveTrafficService:
    """Tests for TomTom API integration"""
    
    def test_service_initialization(self):
        """Test service initializes correctly"""
        service = LiveTrafficService()
        assert service is not None
        assert service.cache_ttl == 60
        assert service._cache == {}
    
    def test_service_with_api_key(self):
        """Test service with API key configured"""
        service = LiveTrafficService(api_key="test_key_123")
        assert service.is_configured is True
        assert service.api_key == "test_key_123"
    
    def test_service_without_api_key(self):
        """Test service without API key"""
        service = LiveTrafficService(api_key="")
        assert service.is_configured is False
    
    def test_congestion_level_calculation(self):
        """Test congestion level calculation from speed ratio"""
        service = LiveTrafficService()
        
        # Low congestion (ratio >= 0.8)
        assert service._calculate_congestion_level(45, 50) == "LOW"
        assert service._calculate_congestion_level(50, 50) == "LOW"
        
        # Medium congestion (0.5 <= ratio < 0.8)
        assert service._calculate_congestion_level(35, 50) == "MEDIUM"
        assert service._calculate_congestion_level(30, 50) == "MEDIUM"
        
        # High congestion (0.2 <= ratio < 0.5)
        assert service._calculate_congestion_level(20, 50) == "HIGH"
        assert service._calculate_congestion_level(15, 50) == "HIGH"
        
        # Jam (ratio < 0.2)
        assert service._calculate_congestion_level(5, 50) == "JAM"
        assert service._calculate_congestion_level(0, 50) == "JAM"
        
        # Edge case: free flow speed is 0
        assert service._calculate_congestion_level(30, 0) == "LOW"
    
    def test_cache_key_generation(self):
        """Test cache key generation"""
        service = LiveTrafficService()
        
        key1 = service._get_cache_key("R-1", 23.2345, 72.6789)
        key2 = service._get_cache_key("R-1", 23.2345, 72.6789)
        key3 = service._get_cache_key("R-2", 23.2345, 72.6789)
        
        assert key1 == key2  # Same road and location
        assert key1 != key3  # Different road
    
    def test_cache_operations(self):
        """Test cache set and get operations"""
        service = LiveTrafficService(cache_ttl=60)
        
        # Create test data
        traffic_data = LiveTrafficData(
            road_id="R-1",
            current_speed=30.0,
            free_flow_speed=50.0,
            congestion_level="MEDIUM",
            confidence=80.0,
            timestamp="2026-01-10T10:00:00Z",
            source="API"
        )
        
        cache_key = "test_key"
        
        # Cache should be empty initially
        assert service._get_cached(cache_key) is None
        
        # Set cache
        service._set_cache(cache_key, traffic_data)
        
        # Get cached value
        cached = service._get_cached(cache_key)
        assert cached is not None
        assert cached.road_id == "R-1"
        assert cached.current_speed == 30.0
    
    def test_simulated_data_generation(self):
        """Test simulated data generation when API is unavailable"""
        service = LiveTrafficService(api_key="")
        
        data = service._generate_simulated_data("R-test")
        
        assert data is not None
        assert data.road_id == "R-test"
        assert data.source == "SIMULATION"
        assert data.current_speed >= 0
        assert data.free_flow_speed == 50.0
        assert data.congestion_level in ["LOW", "MEDIUM", "HIGH", "JAM"]
    
    def test_cache_stats(self):
        """Test cache statistics"""
        service = LiveTrafficService()
        
        stats = service.get_cache_stats()
        
        assert "entries" in stats
        assert "hits" in stats
        assert "misses" in stats
        assert "hit_rate" in stats
        assert "ttl_seconds" in stats
    
    def test_api_status(self):
        """Test API status reporting"""
        service = LiveTrafficService(api_key="test_key")
        
        status = service.status
        
        assert status.provider == TrafficAPIProvider.TOMTOM
        assert status.is_configured is True
        assert status.request_count == 0
        assert status.error_count == 0
    
    @pytest.mark.asyncio
    async def test_get_traffic_without_api_key(self):
        """Test getting traffic data without API key returns simulated data"""
        service = LiveTrafficService(api_key="")
        
        data = await service.get_traffic_for_road(
            road_id="R-1",
            start_lat=23.20,
            start_lon=72.60
        )
        
        assert data is not None
        assert data.source == "SIMULATION"
        assert data.road_id == "R-1"
    
    @pytest.mark.asyncio
    async def test_get_traffic_for_multiple_roads(self):
        """Test parallel fetching for multiple roads"""
        service = LiveTrafficService(api_key="")  # No API key - will use simulated
        
        roads = [
            {"id": "R-1", "start_lat": 23.20, "start_lon": 72.60, "end_lat": 23.21, "end_lon": 72.61},
            {"id": "R-2", "start_lat": 23.21, "start_lon": 72.61, "end_lat": 23.22, "end_lon": 72.62},
            {"id": "R-3", "start_lat": 23.22, "start_lon": 72.62, "end_lat": 23.23, "end_lon": 72.63},
        ]
        
        result = await service.get_traffic_for_roads(roads)
        
        assert len(result) == 3
        assert "R-1" in result
        assert "R-2" in result
        assert "R-3" in result
        
        for road_id, data in result.items():
            assert data.road_id == road_id
            assert data.source == "SIMULATION"
    
    @pytest.mark.asyncio
    async def test_service_cleanup(self):
        """Test service initialization and cleanup"""
        service = LiveTrafficService()
        
        await service.initialize()
        assert service._session is not None
        
        await service.close()
        # Session should be closed


# ============================================
# Map Loader Service Tests
# ============================================

class TestMapLoaderService:
    """Tests for OpenStreetMap integration"""
    
    def test_service_initialization(self):
        """Test service initializes correctly"""
        service = MapLoaderService()
        assert service is not None
        assert service.canvas_width == 1200
        assert service.canvas_height == 800
    
    def test_custom_canvas_size(self):
        """Test service with custom canvas size"""
        service = MapLoaderService(canvas_width=1920, canvas_height=1080)
        assert service.canvas_width == 1920
        assert service.canvas_height == 1080
    
    def test_get_predefined_areas(self):
        """Test getting predefined map areas"""
        service = MapLoaderService()
        areas = service.get_predefined_areas()
        
        assert len(areas) > 0
        assert "gift_city" in areas
        assert "sector_1_5" in areas
        
        gift_city = areas["gift_city"]
        assert gift_city.name == "GIFT City"
        assert gift_city.bounds is not None
    
    def test_predefined_areas_have_bounds(self):
        """Test all predefined areas have valid bounds"""
        for key, area in PREDEFINED_AREAS.items():
            assert area.bounds is not None
            assert area.bounds.north > area.bounds.south
            assert area.bounds.east > area.bounds.west
    
    def test_mock_data_generation(self):
        """Test mock data generation when OSMnx is unavailable"""
        service = MapLoaderService()
        
        bounds = MapBounds(north=23.2, south=23.1, east=72.7, west=72.6)
        result = service._generate_mock_data(
            area_id="test_area",
            area_name="Test Area",
            bounds=bounds
        )
        
        assert result is not None
        assert result.map_area.id == "test_area"
        assert result.map_area.name == "Test Area"
        assert len(result.junctions) == 9  # 3x3 grid
        assert len(result.roads) == 12  # 6 horizontal + 6 vertical
    
    def test_mock_junctions_have_coordinates(self):
        """Test mock junctions have GPS and canvas coordinates"""
        service = MapLoaderService()
        
        result = service._generate_mock_data(
            area_id="test",
            area_name="Test",
            bounds=MapBounds(north=23.2, south=23.1, east=72.7, west=72.6)
        )
        
        for junction in result.junctions:
            # GPS coordinates should be within bounds
            assert 23.1 <= junction.lat <= 23.2
            assert 72.6 <= junction.lon <= 72.7
            
            # Canvas coordinates should be set
            assert junction.x > 0
            assert junction.y > 0
            assert junction.x < service.canvas_width
            assert junction.y < service.canvas_height
    
    def test_mock_roads_connect_junctions(self):
        """Test mock roads properly connect junctions"""
        service = MapLoaderService()
        
        result = service._generate_mock_data(
            area_id="test",
            area_name="Test"
        )
        
        junction_ids = {j.id for j in result.junctions}
        
        for road in result.roads:
            assert road.start_junction_id in junction_ids
            assert road.end_junction_id in junction_ids
            assert road.start_junction_id != road.end_junction_id
    
    def test_mock_junctions_have_signals(self):
        """Test mock junctions have traffic signals"""
        service = MapLoaderService()
        
        result = service._generate_mock_data(
            area_id="test",
            area_name="Test"
        )
        
        for junction in result.junctions:
            assert junction.signals is not None
            assert junction.signals.north is not None
            assert junction.signals.east is not None
            assert junction.signals.south is not None
            assert junction.signals.west is not None
    
    def test_load_predefined_area_returns_result(self):
        """Test loading predefined area returns valid result"""
        service = MapLoaderService()
        
        result = service.load_predefined_area("gift_city")
        
        assert isinstance(result, OSMLoadResult)
        assert result.map_area is not None
        assert result.junctions is not None
        assert result.roads is not None
        assert result.bounds is not None
    
    def test_load_predefined_area_invalid_key(self):
        """Test loading invalid predefined area raises error"""
        service = MapLoaderService()
        
        with pytest.raises(ValueError):
            service.load_predefined_area("invalid_area_key")
    
    def test_load_by_bbox(self):
        """Test loading by bounding box"""
        service = MapLoaderService()
        
        result = service.load_by_bbox(
            north=23.2,
            south=23.1,
            east=72.7,
            west=72.6
        )
        
        assert isinstance(result, OSMLoadResult)
        assert result.bounds.north == 23.2
        assert result.bounds.south == 23.1
    
    def test_coordinate_converter_created(self):
        """Test coordinate converter is created after loading map"""
        service = MapLoaderService()
        
        assert service.converter is None
        
        service._generate_mock_data("test", "Test")
        
        assert service.converter is not None
    
    def test_global_service_instance(self):
        """Test global service instance"""
        service1 = get_map_loader_service()
        service2 = get_map_loader_service()
        
        assert service1 is service2  # Same instance


# ============================================
# Integration Tests
# ============================================

class TestServiceIntegration:
    """Integration tests for services working together"""
    
    @pytest.mark.asyncio
    async def test_load_map_then_get_traffic(self):
        """Test loading map then fetching traffic for its roads"""
        map_service = MapLoaderService()
        traffic_service = LiveTrafficService(api_key="")
        
        # Load mock map
        map_result = map_service.load_predefined_area("demo_area")
        
        # Get traffic for all roads
        roads = []
        for road in map_result.roads:
            roads.append({
                "id": road.id,
                "start_lat": road.start_lat,
                "start_lon": road.start_lon,
                "end_lat": road.end_lat,
                "end_lon": road.end_lon
            })
        
        traffic_data = await traffic_service.get_traffic_for_roads(roads)
        
        # Should have traffic data for all roads
        assert len(traffic_data) == len(map_result.roads)
        
        for road in map_result.roads:
            assert road.id in traffic_data
    
    def test_predefined_areas_bounds_valid(self):
        """Test all predefined areas have sensible bounds for Gandhinagar"""
        for key, area in PREDEFINED_AREAS.items():
            # Gandhinagar is roughly at 23.2N, 72.6E
            assert 22.5 < area.bounds.south < 24.0
            assert 22.5 < area.bounds.north < 24.0
            assert 72.0 < area.bounds.west < 73.0
            assert 72.0 < area.bounds.east < 73.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

