"""
WebSocket Tests

This module tests the WebSocket implementation including:
- Event definitions
- WebSocketEmitter methods
- WebSocketHandlers event handling
"""

import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch

from app.websocket.events import (
    ServerEvent,
    ClientEvent,
    ConnectionSuccessData,
    VehicleUpdateData,
    SignalChangeData,
    DensityUpdateData,
    EmergencyActivatedData,
    ViolationDetectedData,
    ChallanIssuedData,
)
from app.websocket.emitter import WebSocketEmitter
from app.websocket.handlers import WebSocketHandlers


# ============================================
# Event Tests
# ============================================

class TestServerEvents:
    """Test server event enum values"""
    
    def test_connection_events(self):
        assert ServerEvent.CONNECTION_SUCCESS.value == "connection:success"
    
    def test_vehicle_events(self):
        assert ServerEvent.VEHICLE_UPDATE.value == "vehicle:update"
        assert ServerEvent.VEHICLE_SPAWNED.value == "vehicle:spawned"
        assert ServerEvent.VEHICLE_REMOVED.value == "vehicle:removed"
    
    def test_signal_events(self):
        assert ServerEvent.SIGNAL_CHANGE.value == "signal:change"
    
    def test_density_events(self):
        assert ServerEvent.DENSITY_UPDATE.value == "density:update"
    
    def test_emergency_events(self):
        assert ServerEvent.EMERGENCY_ACTIVATED.value == "emergency:activated"
        assert ServerEvent.EMERGENCY_DEACTIVATED.value == "emergency:deactivated"
    
    def test_safety_events(self):
        assert ServerEvent.FAILSAFE_TRIGGERED.value == "failsafe:triggered"
    
    def test_violation_events(self):
        assert ServerEvent.VIOLATION_DETECTED.value == "violation:detected"
        assert ServerEvent.CHALLAN_ISSUED.value == "challan:issued"
    
    def test_live_traffic_events(self):
        assert ServerEvent.LIVE_TRAFFIC_UPDATED.value == "live:traffic:updated"
        assert ServerEvent.LIVE_TRAFFIC_ERROR.value == "live:traffic:error"
    
    def test_map_events(self):
        assert ServerEvent.MAP_LOADED.value == "map:loaded"


class TestClientEvents:
    """Test client event enum values"""
    
    def test_simulation_events(self):
        assert ClientEvent.SIMULATION_CONTROL.value == "simulation:control"
    
    def test_vehicle_events(self):
        assert ClientEvent.VEHICLE_SPAWN.value == "vehicle:spawn"
    
    def test_signal_events(self):
        assert ClientEvent.SIGNAL_OVERRIDE.value == "signal:override"
    
    def test_emergency_events(self):
        assert ClientEvent.EMERGENCY_TRIGGER.value == "emergency:trigger"
        assert ClientEvent.EMERGENCY_CLEAR.value == "emergency:clear"
    
    def test_map_events(self):
        assert ClientEvent.MAP_LOAD_REQUEST.value == "map:load:request"
    
    def test_subscription_events(self):
        assert ClientEvent.SUBSCRIBE_UPDATES.value == "subscribe:updates"
        assert ClientEvent.UNSUBSCRIBE_UPDATES.value == "unsubscribe:updates"


# ============================================
# Event Data Model Tests
# ============================================

class TestEventDataModels:
    """Test event data model validation"""
    
    def test_connection_success_data(self):
        data = ConnectionSuccessData(
            message="Connected",
            timestamp=time.time(),
            server_version="1.0.0"
        )
        assert data.message == "Connected"
        assert data.server_version == "1.0.0"
    
    def test_vehicle_update_data(self):
        data = VehicleUpdateData(
            vehicleId="v-123",
            position={"x": 100, "y": 200},
            speed=30.5,
            heading=45.0,
            timestamp=time.time()
        )
        assert data.vehicleId == "v-123"
        assert data.position["x"] == 100
        assert data.speed == 30.5
    
    def test_vehicle_update_with_gps(self):
        data = VehicleUpdateData(
            vehicleId="v-456",
            position={"x": 100, "y": 200},
            speed=25.0,
            heading=90.0,
            timestamp=time.time(),
            lat=23.2156,
            lon=72.6369
        )
        assert data.lat == 23.2156
        assert data.lon == 72.6369
    
    def test_signal_change_data(self):
        data = SignalChangeData(
            junctionId="J-1",
            direction="north",
            newState="GREEN",
            previousState="RED",
            duration=30.0,
            timestamp=time.time()
        )
        assert data.junctionId == "J-1"
        assert data.newState == "GREEN"
        assert data.duration == 30.0
    
    def test_density_update_data(self):
        data = DensityUpdateData(
            roadId="R-J1-J2",
            densityScore=65.5,
            classification="MEDIUM",
            vehicleCount=8,
            timestamp=time.time(),
            color="#f59e0b"
        )
        assert data.roadId == "R-J1-J2"
        assert data.classification == "MEDIUM"
        assert data.color == "#f59e0b"
    
    def test_emergency_activated_data(self):
        data = EmergencyActivatedData(
            vehicleId="ev-001",
            corridorPath=["J-1", "J-2", "J-3", "J-9"],
            estimatedTime=120.0,
            destination="J-9",
            activatedAt=time.time()
        )
        assert len(data.corridorPath) == 4
        assert data.estimatedTime == 120.0
    
    def test_violation_detected_data(self):
        data = ViolationDetectedData(
            id="vio-001",
            vehicleId="v-123",
            numberPlate="GJ18AB1234",
            violationType="RED_LIGHT",
            severity="HIGH",
            location="J-5",
            timestamp=time.time(),
            evidence={"camera_id": "cam-01", "signal_state": "RED"}
        )
        assert data.violationType == "RED_LIGHT"
        assert data.severity == "HIGH"
        assert "camera_id" in data.evidence
    
    def test_challan_issued_data(self):
        data = ChallanIssuedData(
            challanId="ch-001",
            numberPlate="GJ18AB1234",
            ownerName="John Doe",
            violationType="RED_LIGHT",
            fineAmount=1000.0,
            location="J-5",
            timestamp=time.time()
        )
        assert data.challanId == "ch-001"
        assert data.fineAmount == 1000.0


# ============================================
# WebSocketEmitter Tests
# ============================================

class TestWebSocketEmitter:
    """Test WebSocket emitter functionality"""
    
    @pytest.fixture
    def mock_sio(self):
        """Create a mock Socket.IO server"""
        sio = MagicMock()
        sio.emit = AsyncMock()
        return sio
    
    @pytest.fixture
    def emitter(self, mock_sio):
        """Create an emitter with mock Socket.IO"""
        return WebSocketEmitter(mock_sio)
    
    @pytest.mark.asyncio
    async def test_emit_connection_success(self, emitter, mock_sio):
        """Test connection success emission"""
        await emitter.emit_connection_success("test-sid")
        
        mock_sio.emit.assert_called_once()
        call_args = mock_sio.emit.call_args
        assert call_args[0][0] == "connection:success"
        assert "message" in call_args[0][1]
        assert call_args[1]["room"] == "test-sid"
    
    @pytest.mark.asyncio
    async def test_emit_vehicle_update(self, emitter, mock_sio):
        """Test vehicle update emission"""
        vehicle_data = {
            "id": "v-123",
            "position": {"x": 100, "y": 200},
            "speed": 30.5,
            "heading": 45.0,
            "last_update": time.time()
        }
        
        await emitter.emit_vehicle_update(vehicle_data)
        
        mock_sio.emit.assert_called_once()
        call_args = mock_sio.emit.call_args
        assert call_args[0][0] == "vehicle:update"
        assert call_args[0][1]["vehicleId"] == "v-123"
    
    @pytest.mark.asyncio
    async def test_emit_signal_change(self, emitter, mock_sio):
        """Test signal change emission"""
        await emitter.emit_signal_change(
            junction_id="J-1",
            direction="north",
            new_state="GREEN",
            previous_state="RED",
            duration=30.0
        )
        
        mock_sio.emit.assert_called_once()
        call_args = mock_sio.emit.call_args
        assert call_args[0][0] == "signal:change"
        assert call_args[0][1]["junctionId"] == "J-1"
        assert call_args[0][1]["newState"] == "GREEN"
    
    @pytest.mark.asyncio
    async def test_emit_density_update(self, emitter, mock_sio):
        """Test density update emission"""
        await emitter.emit_density_update("R-J1-J2", {
            "density_score": 65.5,
            "classification": "MEDIUM",
            "vehicle_count": 8
        })
        
        mock_sio.emit.assert_called_once()
        call_args = mock_sio.emit.call_args
        assert call_args[0][0] == "density:update"
        assert call_args[0][1]["roadId"] == "R-J1-J2"
        assert call_args[0][1]["classification"] == "MEDIUM"
    
    @pytest.mark.asyncio
    async def test_emit_emergency_activated(self, emitter, mock_sio):
        """Test emergency activation emission"""
        await emitter.emit_emergency_activated({
            "vehicle_id": "ev-001",
            "corridor_path": ["J-1", "J-2", "J-9"],
            "estimated_time": 90.0,
            "destination": "J-9"
        })
        
        mock_sio.emit.assert_called_once()
        call_args = mock_sio.emit.call_args
        assert call_args[0][0] == "emergency:activated"
        assert call_args[0][1]["vehicleId"] == "ev-001"
    
    @pytest.mark.asyncio
    async def test_emit_violation_detected(self, emitter, mock_sio):
        """Test violation detection emission"""
        await emitter.emit_violation_detected({
            "id": "vio-001",
            "vehicle_id": "v-123",
            "number_plate": "GJ18AB1234",
            "violation_type": "SPEEDING",
            "severity": "MEDIUM",
            "location": "R-J1-J2",
            "evidence": {"speed": 85, "limit": 60}
        })
        
        mock_sio.emit.assert_called_once()
        call_args = mock_sio.emit.call_args
        assert call_args[0][0] == "violation:detected"
        assert call_args[0][1]["violationType"] == "SPEEDING"
    
    @pytest.mark.asyncio
    async def test_emit_failsafe_triggered(self, emitter, mock_sio):
        """Test failsafe trigger emission"""
        await emitter.emit_failsafe_triggered(
            reason="Agent timeout exceeded",
            affected_junctions=["J-1", "J-2", "J-3"],
            previous_mode="NORMAL"
        )
        
        mock_sio.emit.assert_called_once()
        call_args = mock_sio.emit.call_args
        assert call_args[0][0] == "failsafe:triggered"
        assert call_args[0][1]["reason"] == "Agent timeout exceeded"
        assert len(call_args[0][1]["affectedJunctions"]) == 3
    
    def test_subscription_management(self, emitter):
        """Test subscription add/remove"""
        emitter.add_subscription("sid-1", "vehicles")
        emitter.add_subscription("sid-1", "signals")
        emitter.add_subscription("sid-2", "vehicles")
        
        assert "sid-1" in emitter.get_subscribers("vehicles")
        assert "sid-1" in emitter.get_subscribers("signals")
        assert "sid-2" in emitter.get_subscribers("vehicles")
        
        emitter.remove_subscription("sid-1", "vehicles")
        assert "sid-1" not in emitter.get_subscribers("vehicles")
        assert "sid-1" in emitter.get_subscribers("signals")
        
        emitter.remove_subscription("sid-1")  # Remove all
        assert "sid-1" not in emitter.get_subscribers("signals")
    
    def test_get_stats(self, emitter):
        """Test statistics retrieval"""
        stats = emitter.get_stats()
        
        assert "totalEmits" in stats
        assert "errorCount" in stats
        assert "pendingVehicleUpdates" in stats
        assert "subscriptionChannels" in stats


# ============================================
# WebSocketHandlers Tests
# ============================================

class TestWebSocketHandlers:
    """Test WebSocket handlers functionality"""
    
    @pytest.fixture
    def mock_sio(self):
        """Create a mock Socket.IO server"""
        sio = MagicMock()
        sio.emit = AsyncMock()
        sio.on = MagicMock()
        sio.enter_room = AsyncMock()
        sio.leave_room = AsyncMock()
        return sio
    
    @pytest.fixture
    def mock_emitter(self, mock_sio):
        """Create a mock emitter"""
        emitter = MagicMock(spec=WebSocketEmitter)
        emitter.emit_connection_success = AsyncMock()
        emitter.emit_system_state_update = AsyncMock()
        emitter.emit_vehicle_spawned = AsyncMock()
        emitter.emit_signal_change = AsyncMock()
        emitter.emit_traffic_control_active = AsyncMock()
        emitter.emit_emergency_activated = AsyncMock()
        emitter.emit_emergency_deactivated = AsyncMock()
        emitter.emit_map_loaded = AsyncMock()
        emitter.emit_map_loading = AsyncMock()
        emitter.emit_data_mode_changed = AsyncMock()
        emitter.add_subscription = MagicMock()
        emitter.remove_subscription = MagicMock()
        return emitter
    
    @pytest.fixture
    def handlers(self, mock_sio, mock_emitter):
        """Create handlers with mocks"""
        return WebSocketHandlers(mock_sio, mock_emitter)
    
    @pytest.mark.asyncio
    async def test_handle_connect(self, handlers, mock_emitter):
        """Test connection handler"""
        environ = {
            "REMOTE_ADDR": "127.0.0.1",
            "HTTP_USER_AGENT": "TestClient/1.0"
        }
        
        await handlers.handle_connect("test-sid", environ)
        
        assert handlers.is_client_connected("test-sid")
        assert handlers.get_client_count() == 1
        mock_emitter.emit_connection_success.assert_called_once_with("test-sid")
    
    @pytest.mark.asyncio
    async def test_handle_disconnect(self, handlers, mock_emitter):
        """Test disconnection handler"""
        # First connect
        await handlers.handle_connect("test-sid", {})
        assert handlers.is_client_connected("test-sid")
        
        # Then disconnect
        await handlers.handle_disconnect("test-sid")
        assert not handlers.is_client_connected("test-sid")
        mock_emitter.remove_subscription.assert_called_with("test-sid")
    
    @pytest.mark.asyncio
    async def test_handle_simulation_control(self, handlers, mock_sio, mock_emitter):
        """Test simulation control handler"""
        await handlers.handle_simulation_control("test-sid", {"action": "PAUSE"})
        
        # Should emit response to client
        mock_sio.emit.assert_called()
        call_args = mock_sio.emit.call_args_list[0]
        assert call_args[0][0] == "simulation:control:response"
        assert call_args[0][1]["action"] == "PAUSE"
    
    @pytest.mark.asyncio
    async def test_handle_vehicle_spawn(self, handlers, mock_sio, mock_emitter):
        """Test vehicle spawn handler"""
        await handlers.handle_vehicle_spawn("test-sid", {
            "type": "car",
            "spawnPoint": "J-1",
            "destination": "J-9"
        })
        
        # Should emit response and broadcast spawn
        mock_sio.emit.assert_called()
        mock_emitter.emit_vehicle_spawned.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_signal_override(self, handlers, mock_sio, mock_emitter):
        """Test signal override handler"""
        await handlers.handle_signal_override("test-sid", {
            "junctionId": "J-1",
            "direction": "N",
            "action": "FORCE_GREEN",
            "duration": 30
        })
        
        mock_sio.emit.assert_called()
        mock_emitter.emit_signal_change.assert_called_once()
        mock_emitter.emit_traffic_control_active.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_emergency_trigger(self, handlers, mock_sio, mock_emitter):
        """Test emergency trigger handler"""
        await handlers.handle_emergency_trigger("test-sid", {
            "spawnPoint": "J-1",
            "destination": "J-9"
        })
        
        mock_sio.emit.assert_called()
        mock_emitter.emit_emergency_activated.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_subscribe(self, handlers, mock_sio, mock_emitter):
        """Test subscription handler"""
        await handlers.handle_connect("test-sid", {})
        
        await handlers.handle_subscribe("test-sid", {
            "channels": ["vehicles", "signals", "density"]
        })
        
        # Should join rooms for each channel
        assert mock_sio.enter_room.call_count == 3
        mock_emitter.add_subscription.assert_called()
    
    @pytest.mark.asyncio
    async def test_handle_unsubscribe(self, handlers, mock_sio, mock_emitter):
        """Test unsubscribe handler"""
        await handlers.handle_unsubscribe("test-sid", {
            "channels": ["vehicles"]
        })
        
        mock_sio.leave_room.assert_called_once()
        mock_emitter.remove_subscription.assert_called()
    
    def test_get_connected_clients(self, handlers):
        """Test getting connected clients"""
        clients = handlers.get_connected_clients()
        assert isinstance(clients, dict)
    
    def test_get_client_count(self, handlers):
        """Test getting client count"""
        count = handlers.get_client_count()
        assert count == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

