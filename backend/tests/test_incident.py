"""
Tests for Post-Incident Vehicle Tracking System (FRD-08)

Tests:
- Detection history logging
- Incident creation and management
- Vehicle inference engine
- API endpoints
"""

import pytest
import time
import asyncio
from unittest.mock import Mock, AsyncMock, patch

# Import incident components
from app.incident.detection_logger import (
    DetectionHistoryLogger,
    VehicleDetectionEvent,
    init_detection_logger,
    get_detection_logger
)
from app.incident.incident_manager import (
    IncidentManager,
    IncidentType,
    IncidentStatus,
    init_incident_manager,
    get_incident_manager
)
from app.incident.inference_engine import (
    VehicleInferenceEngine,
    init_inference_engine,
    get_inference_engine
)


# ============================================
# Detection Logger Tests
# ============================================

class TestDetectionLogger:
    """Tests for DetectionHistoryLogger"""
    
    def test_logger_initialization(self):
        """Test logger initializes correctly"""
        logger = DetectionHistoryLogger(
            buffer_size=50,
            flush_interval=10.0,
            retention_hours=12
        )
        
        assert logger.buffer_size == 50
        assert logger.flush_interval == 10.0
        assert logger.retention_hours == 12
        assert logger.total_detections == 0
    
    def test_log_detection_sync(self):
        """Test synchronous detection logging"""
        logger = DetectionHistoryLogger(buffer_size=100)
        
        logger.log_detection(
            vehicle_id="V-001",
            number_plate="GJ01AB1234",
            junction_id="J-1",
            direction="N",
            position_x=100.0,
            position_y=200.0,
            speed=30.0,
            vehicle_type="CAR"
        )
        
        assert logger.total_detections == 1
        assert len(logger._buffer) == 1
    
    def test_log_multiple_detections(self):
        """Test logging multiple detections"""
        logger = DetectionHistoryLogger(buffer_size=100)
        
        for i in range(10):
            logger.log_detection(
                vehicle_id=f"V-{i:03d}",
                number_plate=f"GJ01AB{i:04d}",
                junction_id=f"J-{i}",
                direction="N",
                position_x=100.0 + i,
                position_y=200.0 + i,
                speed=30.0,
                vehicle_type="CAR"
            )
        
        assert logger.total_detections == 10
        assert len(logger._buffer) == 10
    
    def test_get_statistics(self):
        """Test statistics reporting"""
        logger = DetectionHistoryLogger(buffer_size=100)
        
        for i in range(5):
            logger.log_detection(
                vehicle_id=f"V-{i}",
                number_plate=f"GJ01AB{i:04d}",
                junction_id="J-1",
                direction="N",
                position_x=100.0,
                position_y=200.0,
                speed=30.0,
                vehicle_type="CAR"
            )
        
        stats = logger.get_statistics()
        
        assert stats['totalDetections'] == 5
        assert stats['bufferSize'] == 5
        assert 'retentionHours' in stats


# ============================================
# Incident Manager Tests
# ============================================

class TestIncidentManager:
    """Tests for IncidentManager"""
    
    def test_manager_initialization(self):
        """Test manager initializes correctly"""
        manager = IncidentManager()
        
        assert manager.total_incidents == 0
        assert manager.total_resolved == 0
        assert len(manager._active_incidents) == 0
    
    @pytest.mark.asyncio
    async def test_create_incident(self):
        """Test incident creation"""
        manager = IncidentManager()
        
        incident_id = await manager.create_incident(
            number_plate="GJ01AB1234",
            incident_time=time.time() - 3600,
            incident_type="HIT_AND_RUN",
            description="Test incident"
        )
        
        assert incident_id.startswith('inc-')
        assert manager.total_incidents == 1
    
    @pytest.mark.asyncio
    async def test_get_incident(self):
        """Test incident retrieval"""
        manager = IncidentManager()
        
        incident_id = await manager.create_incident(
            number_plate="GJ01XY9999",
            incident_time=time.time(),
            incident_type="THEFT"
        )
        
        incident = await manager.get_incident(incident_id)
        
        assert incident is not None
        assert incident.number_plate == "GJ01XY9999"
        assert incident.incident_type == IncidentType.THEFT
    
    @pytest.mark.asyncio
    async def test_resolve_incident(self):
        """Test incident resolution"""
        manager = IncidentManager()
        
        # Create incident without inference engine (will skip processing)
        incident_id = await manager.create_incident(
            number_plate="GJ01CD5678",
            incident_time=time.time(),
            incident_type="SUSPICIOUS"
        )
        
        # Wait a bit for async processing
        await asyncio.sleep(0.1)
        
        success = await manager.resolve_incident(
            incident_id=incident_id,
            resolution_notes="Vehicle found and owner contacted"
        )
        
        assert success is True
        assert manager.total_resolved == 1
        
        incident = await manager.get_incident(incident_id)
        assert incident.status == IncidentStatus.RESOLVED
    
    def test_incident_types(self):
        """Test all incident types are valid"""
        assert IncidentType.HIT_AND_RUN.value == "HIT_AND_RUN"
        assert IncidentType.THEFT.value == "THEFT"
        assert IncidentType.SUSPICIOUS.value == "SUSPICIOUS"
        assert IncidentType.ACCIDENT.value == "ACCIDENT"
        assert IncidentType.OTHER.value == "OTHER"
    
    def test_get_statistics(self):
        """Test statistics reporting"""
        manager = IncidentManager()
        
        stats = manager.get_statistics()
        
        assert stats['totalIncidents'] == 0
        assert stats['totalResolved'] == 0
        assert stats['activeIncidents'] == 0


# ============================================
# Inference Engine Tests
# ============================================

class TestInferenceEngine:
    """Tests for VehicleInferenceEngine"""
    
    def test_engine_initialization(self):
        """Test engine initializes correctly"""
        engine = VehicleInferenceEngine(
            avg_city_speed=30.0,
            max_search_radius=10.0,
            detection_time_window=3600
        )
        
        assert engine.avg_city_speed == 30.0
        assert engine.max_search_radius == 10.0
        assert engine.detection_time_window == 3600
        assert engine.total_inferences == 0
    
    def test_search_radius_calculation(self):
        """Test search radius calculation"""
        engine = VehicleInferenceEngine(
            avg_city_speed=30.0,
            max_search_radius=10.0
        )
        
        # 1 hour elapsed = 30 km radius (but capped at 10)
        radius = engine._calculate_search_radius(3600)
        assert radius == 10.0
        
        # 10 minutes elapsed = 5 km radius
        radius = engine._calculate_search_radius(600)
        assert radius == 5.0
        
        # 5 minutes elapsed = 2.5 km radius
        radius = engine._calculate_search_radius(300)
        assert radius == 2.5
    
    def test_confidence_calculation(self):
        """Test confidence score calculation"""
        engine = VehicleInferenceEngine()
        
        # Many detections, recent = high confidence
        conf1 = engine._calculate_confidence(
            detection_count=10,
            time_elapsed=300,  # 5 minutes
            last_detection_age=60  # 1 minute ago
        )
        
        # Few detections, old = low confidence
        conf2 = engine._calculate_confidence(
            detection_count=2,
            time_elapsed=3600,  # 1 hour
            last_detection_age=1800  # 30 minutes ago
        )
        
        assert conf1 > conf2
        assert 0 <= conf1 <= 100
        assert 0 <= conf2 <= 100
    
    def test_get_statistics(self):
        """Test statistics reporting"""
        engine = VehicleInferenceEngine()
        
        stats = engine.get_statistics()
        
        assert stats['totalInferences'] == 0
        assert stats['avgInferenceTimeMs'] == 0
        assert 'avgCitySpeed' in stats
        assert 'maxSearchRadius' in stats


# ============================================
# Integration Tests
# ============================================

class TestIncidentIntegration:
    """Integration tests for the full incident system"""
    
    @pytest.mark.asyncio
    async def test_full_incident_workflow(self):
        """Test complete incident workflow without DB"""
        # Initialize components
        engine = VehicleInferenceEngine()
        manager = IncidentManager(inference_engine=engine)
        
        # Create incident
        incident_id = await manager.create_incident(
            number_plate="GJ01TEST999",
            incident_time=time.time() - 1800,  # 30 min ago
            incident_type="HIT_AND_RUN",
            location_name="Test Location",
            description="Integration test incident"
        )
        
        assert incident_id is not None
        
        # Wait for async processing
        await asyncio.sleep(0.2)
        
        # Get incident
        incident = await manager.get_incident(incident_id)
        assert incident is not None
        assert incident.number_plate == "GJ01TEST999"
        
        # Resolve
        success = await manager.resolve_incident(
            incident_id=incident_id,
            resolution_notes="Test complete"
        )
        assert success is True
    
    def test_global_instance_management(self):
        """Test global instance management functions"""
        # Detection logger
        logger = init_detection_logger({'bufferSize': 50})
        assert get_detection_logger() is logger
        
        # Inference engine
        engine = init_inference_engine(config={'avgCitySpeed': 25.0})
        assert get_inference_engine() is engine
        
        # Incident manager
        manager = init_incident_manager(inference_engine=engine)
        assert get_incident_manager() is manager


# ============================================
# Performance Tests
# ============================================

class TestPerformance:
    """Performance tests for incident system"""
    
    def test_detection_logging_performance(self):
        """Test detection logging can handle high volume"""
        logger = DetectionHistoryLogger(buffer_size=1000)
        
        start = time.time()
        
        # Log 1000 detections
        for i in range(1000):
            logger.log_detection(
                vehicle_id=f"V-{i:05d}",
                number_plate=f"GJ01{i:06d}",
                junction_id=f"J-{i % 10}",
                direction="N",
                position_x=float(i),
                position_y=float(i),
                speed=30.0,
                vehicle_type="CAR"
            )
        
        elapsed = time.time() - start
        
        # Should complete in under 1 second
        assert elapsed < 1.0
        assert logger.total_detections == 1000
    
    @pytest.mark.asyncio
    async def test_inference_performance(self):
        """Test inference completes within time limit"""
        engine = VehicleInferenceEngine()
        
        start = time.time()
        
        # Process incident (will find no detections)
        result = await engine.process_incident(
            incident_id="perf-test",
            number_plate="GJ01PERF999",
            incident_time=time.time()
        )
        
        elapsed = time.time() - start
        
        # Should complete in under 500ms
        assert elapsed < 0.5
        assert result is not None


# ============================================
# Run tests
# ============================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

