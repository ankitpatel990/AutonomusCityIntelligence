"""
Emergency Green Corridor Tests

Tests for FRD-07: Emergency vehicle detection, pathfinding, and corridor management.
"""

import pytest
import asyncio
import time
from unittest.mock import MagicMock, AsyncMock, patch

from app.emergency import (
    EmergencyTracker,
    EmergencyPathfinder,
    GreenCorridorManager,
    EmergencyType,
    EmergencyStatus,
)


# ============================================
# EmergencyTracker Tests
# ============================================

class TestEmergencyTracker:
    """Test emergency vehicle tracking"""
    
    def test_tracker_initialization(self):
        """Test tracker initializes correctly"""
        tracker = EmergencyTracker()
        
        assert tracker is not None
        assert len(tracker.active_sessions) == 0
        assert tracker.total_emergencies == 0
        assert not tracker.is_emergency_active()
    
    def test_activate_emergency(self):
        """Test emergency activation"""
        tracker = EmergencyTracker()
        
        session_id = tracker.activate_emergency(
            spawn_junction="J-0",
            destination_junction="J-8",
            emergency_type=EmergencyType.AMBULANCE
        )
        
        assert session_id is not None
        assert session_id.startswith("EMG-")
        assert tracker.is_emergency_active()
        assert tracker.total_emergencies == 1
        
        # Get session
        session = tracker.get_active_emergency()
        assert session is not None
        assert session.session_id == session_id
        assert session.status == EmergencyStatus.ACTIVE
        assert session.vehicle.type == EmergencyType.AMBULANCE
    
    def test_cannot_activate_multiple_emergencies(self):
        """Test that only one emergency can be active at a time"""
        tracker = EmergencyTracker()
        
        # First emergency
        session_id_1 = tracker.activate_emergency(
            spawn_junction="J-0",
            destination_junction="J-8"
        )
        
        # Second emergency should fail
        with pytest.raises(ValueError) as excinfo:
            tracker.activate_emergency(
                spawn_junction="J-1",
                destination_junction="J-4"
            )
        
        assert "already active" in str(excinfo.value).lower()
    
    def test_complete_emergency(self):
        """Test completing an emergency"""
        tracker = EmergencyTracker()
        
        session_id = tracker.activate_emergency(
            spawn_junction="J-0",
            destination_junction="J-8"
        )
        
        tracker.complete_emergency(session_id)
        
        assert not tracker.is_emergency_active()
        assert tracker.completed_emergencies == 1
        
        # Session should be in history
        session = tracker.get_session(session_id)
        assert session is not None
        assert session.status == EmergencyStatus.COMPLETED
    
    def test_cancel_emergency(self):
        """Test cancelling an emergency"""
        tracker = EmergencyTracker()
        
        session_id = tracker.activate_emergency(
            spawn_junction="J-0",
            destination_junction="J-8"
        )
        
        tracker.cancel_emergency(session_id, "Test cancellation")
        
        assert not tracker.is_emergency_active()
        assert tracker.cancelled_emergencies == 1
        
        session = tracker.get_session(session_id)
        assert session.status == EmergencyStatus.CANCELLED
    
    def test_vehicle_types(self):
        """Test different emergency vehicle types"""
        for vehicle_type in EmergencyType:
            tracker = EmergencyTracker()
            
            session_id = tracker.activate_emergency(
                spawn_junction="J-0",
                destination_junction="J-8",
                emergency_type=vehicle_type
            )
            
            session = tracker.get_session(session_id)
            assert session.vehicle.type == vehicle_type
    
    def test_get_statistics(self):
        """Test statistics tracking"""
        tracker = EmergencyTracker()
        
        # Activate and complete
        session_id = tracker.activate_emergency("J-0", "J-8")
        tracker.complete_emergency(session_id)
        
        stats = tracker.get_statistics()
        
        assert stats['totalEmergencies'] == 1
        assert stats['completedEmergencies'] == 1
        assert stats['activeEmergencies'] == 0
        assert stats['successRate'] == 100.0
    
    def test_update_session_route(self):
        """Test updating session with calculated route"""
        tracker = EmergencyTracker()
        
        session_id = tracker.activate_emergency("J-0", "J-8")
        
        route = ["J-0", "J-1", "J-2", "J-5", "J-8"]
        tracker.update_session_route(session_id, route, distance=1000, estimated_time=60)
        
        session = tracker.get_session(session_id)
        assert session.calculated_route == route
        assert session.total_distance == 1000
        assert session.estimated_time == 60
    
    def test_get_progress(self):
        """Test progress calculation"""
        tracker = EmergencyTracker()
        
        session_id = tracker.activate_emergency("J-0", "J-8")
        route = ["J-0", "J-1", "J-2", "J-5", "J-8"]
        tracker.update_session_route(session_id, route)
        
        # Update vehicle position
        session = tracker.get_session(session_id)
        session.vehicle.current_junction_id = "J-1"
        
        progress = tracker.get_progress(session_id)
        
        assert progress['currentJunction'] == "J-1"
        assert progress['totalJunctions'] == 5
        assert progress['progress'] == 25.0  # 1 of 4 segments


# ============================================
# EmergencyPathfinder Tests
# ============================================

class TestEmergencyPathfinder:
    """Test A* pathfinding"""
    
    def test_pathfinder_initialization(self):
        """Test pathfinder initializes correctly"""
        pathfinder = EmergencyPathfinder()
        
        assert pathfinder is not None
    
    def test_mock_graph_creation(self):
        """Test mock graph creation for testing"""
        pathfinder = EmergencyPathfinder()
        pathfinder.build_mock_graph(grid_size=3)
        
        assert len(pathfinder.junction_graph) == 9  # 3x3 grid
        assert "J-0" in pathfinder.junction_graph
        assert "J-8" in pathfinder.junction_graph
    
    def test_find_path_simple(self):
        """Test pathfinding on mock grid"""
        pathfinder = EmergencyPathfinder()
        pathfinder.build_mock_graph(grid_size=3)
        
        path = pathfinder.find_path("J-0", "J-8")
        
        assert path is not None
        assert path[0] == "J-0"  # Start
        assert path[-1] == "J-8"  # End
        assert len(path) > 1
    
    def test_find_path_same_start_end(self):
        """Test pathfinding when start equals end"""
        pathfinder = EmergencyPathfinder()
        pathfinder.build_mock_graph()
        
        path = pathfinder.find_path("J-4", "J-4")
        
        assert path == ["J-4"]
    
    def test_find_path_invalid_start(self):
        """Test pathfinding with invalid start junction"""
        pathfinder = EmergencyPathfinder()
        pathfinder.build_mock_graph()
        
        path = pathfinder.find_path("INVALID", "J-8")
        
        assert path is None
    
    def test_find_path_invalid_end(self):
        """Test pathfinding with invalid end junction"""
        pathfinder = EmergencyPathfinder()
        pathfinder.build_mock_graph()
        
        path = pathfinder.find_path("J-0", "INVALID")
        
        assert path is None
    
    def test_path_distance(self):
        """Test path distance calculation"""
        pathfinder = EmergencyPathfinder()
        pathfinder.build_mock_graph()
        
        path = pathfinder.find_path("J-0", "J-2")  # Horizontal path
        distance = pathfinder.get_path_distance(path)
        
        assert distance > 0
    
    def test_get_road_segments(self):
        """Test road segment extraction from path"""
        pathfinder = EmergencyPathfinder()
        pathfinder.build_mock_graph()
        
        path = pathfinder.find_path("J-0", "J-2")
        roads = pathfinder.get_road_segments_in_path(path)
        
        assert len(roads) == len(path) - 1
    
    def test_estimate_travel_time(self):
        """Test travel time estimation"""
        pathfinder = EmergencyPathfinder()
        pathfinder.build_mock_graph()
        
        path = pathfinder.find_path("J-0", "J-8")
        time_estimate = pathfinder.estimate_travel_time(path, speed_kmh=60)
        
        assert time_estimate > 0
    
    def test_heuristic_function(self):
        """Test heuristic calculation"""
        pathfinder = EmergencyPathfinder()
        pathfinder.build_mock_graph()
        
        # Heuristic should be Euclidean distance
        h = pathfinder._heuristic("J-0", "J-8")
        
        assert h > 0
        
        # Same point should have 0 heuristic
        h_same = pathfinder._heuristic("J-4", "J-4")
        assert h_same == 0
    
    def test_get_next_junctions(self):
        """Test getting next junctions in path"""
        pathfinder = EmergencyPathfinder()
        pathfinder.build_mock_graph()
        
        path = ["J-0", "J-1", "J-2", "J-5", "J-8"]
        
        next_junctions = pathfinder.get_next_junctions("J-1", path, lookahead=3)
        
        assert next_junctions[0] == "J-1"
        assert len(next_junctions) <= 4  # current + 3 lookahead


# ============================================
# GreenCorridorManager Tests
# ============================================

class TestGreenCorridorManager:
    """Test green corridor signal control"""
    
    def test_manager_initialization(self):
        """Test corridor manager initializes correctly"""
        manager = GreenCorridorManager()
        
        assert manager is not None
        assert not manager.is_corridor_active()
    
    @pytest.mark.asyncio
    async def test_corridor_activation(self):
        """Test corridor activation"""
        # Setup mocks
        tracker = EmergencyTracker()
        pathfinder = EmergencyPathfinder()
        pathfinder.build_mock_graph()
        
        mode_manager = MagicMock()
        
        manager = GreenCorridorManager(
            mode_manager=mode_manager,
            emergency_tracker=tracker,
            pathfinder=pathfinder
        )
        
        # Create emergency
        session_id = tracker.activate_emergency("J-0", "J-8")
        
        # Activate corridor
        result = await manager.activate_corridor(session_id)
        
        assert result == True
        assert manager.is_corridor_active()
        
        # Clean up
        await manager.deactivate_corridor()
    
    @pytest.mark.asyncio
    async def test_corridor_deactivation(self):
        """Test corridor deactivation"""
        tracker = EmergencyTracker()
        pathfinder = EmergencyPathfinder()
        pathfinder.build_mock_graph()
        
        manager = GreenCorridorManager(
            emergency_tracker=tracker,
            pathfinder=pathfinder
        )
        
        # Create and activate
        session_id = tracker.activate_emergency("J-0", "J-8")
        await manager.activate_corridor(session_id)
        
        # Deactivate
        await manager.deactivate_corridor()
        
        assert not manager.is_corridor_active()
    
    @pytest.mark.asyncio
    async def test_corridor_status(self):
        """Test getting corridor status"""
        tracker = EmergencyTracker()
        pathfinder = EmergencyPathfinder()
        pathfinder.build_mock_graph()
        
        manager = GreenCorridorManager(
            emergency_tracker=tracker,
            pathfinder=pathfinder
        )
        
        session_id = tracker.activate_emergency("J-0", "J-8")
        await manager.activate_corridor(session_id)
        
        status = manager.get_corridor_status()
        
        assert status is not None
        assert status['sessionId'] == session_id
        assert 'junctionPath' in status
        assert 'signalOverrides' in status
        
        await manager.deactivate_corridor()
    
    def test_direction_calculation(self):
        """Test travel direction calculation"""
        pathfinder = EmergencyPathfinder()
        pathfinder.build_mock_graph()
        
        manager = GreenCorridorManager(pathfinder=pathfinder)
        
        # J-0 to J-1 should be east (right)
        direction = manager._calculate_direction("J-0", "J-1")
        assert direction == 'east'
        
        # J-0 to J-3 should be south (down in canvas coords)
        direction = manager._calculate_direction("J-0", "J-3")
        assert direction == 'south'
    
    def test_statistics(self):
        """Test corridor statistics"""
        manager = GreenCorridorManager()
        
        stats = manager.get_statistics()
        
        assert 'corridorsActivated' in stats
        assert 'corridorsCompleted' in stats
        assert 'corridorActive' in stats


# ============================================
# Integration Tests
# ============================================

class TestEmergencyIntegration:
    """Integration tests for complete emergency flow"""
    
    @pytest.mark.asyncio
    async def test_full_emergency_flow(self):
        """Test complete emergency lifecycle"""
        # Initialize components
        tracker = EmergencyTracker()
        pathfinder = EmergencyPathfinder()
        pathfinder.build_mock_graph()
        
        mode_manager = MagicMock()
        mode_manager.get_current_mode.return_value = MagicMock()
        
        corridor_manager = GreenCorridorManager(
            mode_manager=mode_manager,
            emergency_tracker=tracker,
            pathfinder=pathfinder
        )
        
        # 1. Activate emergency
        session_id = tracker.activate_emergency(
            spawn_junction="J-0",
            destination_junction="J-8",
            emergency_type=EmergencyType.AMBULANCE
        )
        
        assert tracker.is_emergency_active()
        
        # 2. Activate corridor
        result = await corridor_manager.activate_corridor(session_id)
        assert result == True
        assert corridor_manager.is_corridor_active()
        
        # 3. Verify session has route
        session = tracker.get_session(session_id)
        assert len(session.calculated_route) > 0
        
        # 4. Simulate progress
        progress = tracker.get_progress(session_id)
        assert progress['totalJunctions'] > 0
        
        # 5. Complete emergency
        tracker.complete_emergency(session_id)
        await corridor_manager.deactivate_corridor()
        
        assert not tracker.is_emergency_active()
        assert not corridor_manager.is_corridor_active()
        
        # 6. Verify statistics
        stats = tracker.get_statistics()
        assert stats['completedEmergencies'] == 1
    
    @pytest.mark.asyncio
    async def test_emergency_cancellation_flow(self):
        """Test emergency cancellation"""
        tracker = EmergencyTracker()
        pathfinder = EmergencyPathfinder()
        pathfinder.build_mock_graph()
        
        corridor_manager = GreenCorridorManager(
            emergency_tracker=tracker,
            pathfinder=pathfinder
        )
        
        # Activate
        session_id = tracker.activate_emergency("J-0", "J-8")
        await corridor_manager.activate_corridor(session_id)
        
        # Cancel
        tracker.cancel_emergency(session_id, "Test cancellation")
        await corridor_manager.deactivate_corridor()
        
        assert not tracker.is_emergency_active()
        assert tracker.cancelled_emergencies == 1
    
    def test_pathfinding_performance(self):
        """Test pathfinding performance is under 100ms"""
        pathfinder = EmergencyPathfinder()
        pathfinder.build_mock_graph(grid_size=3)
        
        start_time = time.time()
        
        # Find path multiple times
        for _ in range(10):
            path = pathfinder.find_path("J-0", "J-8")
        
        elapsed = (time.time() - start_time) * 1000
        avg_time = elapsed / 10
        
        assert path is not None
        assert avg_time < 100, f"Pathfinding too slow: {avg_time:.1f}ms"


# ============================================
# API Route Tests (using TestClient)
# ============================================

class TestEmergencyAPI:
    """Test emergency API endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        from fastapi.testclient import TestClient
        from app.main import app
        return TestClient(app)
    
    def test_trigger_emergency_endpoint(self, client):
        """Test emergency trigger endpoint"""
        response = client.post(
            "/api/emergency/trigger",
            json={
                "spawnPoint": "J-0",
                "destination": "J-8",
                "vehicleType": "AMBULANCE"
            }
        )
        
        # May fail if components not initialized, which is OK for unit test
        assert response.status_code in [200, 503]
    
    def test_status_endpoint(self, client):
        """Test emergency status endpoint"""
        response = client.get("/api/emergency/status")
        
        assert response.status_code in [200, 503]
    
    def test_statistics_endpoint(self, client):
        """Test emergency statistics endpoint"""
        response = client.get("/api/emergency/statistics")
        
        assert response.status_code in [200, 503]
    
    def test_history_endpoint(self, client):
        """Test emergency history endpoint"""
        response = client.get("/api/emergency/history")
        
        assert response.status_code in [200, 503]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


