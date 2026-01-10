"""
Unit Tests for Pydantic Models

Tests all data models for proper validation and serialization.
"""

import pytest
import time
import json
from pydantic import ValidationError

from app.models import (
    # Core models
    Position,
    Vehicle,
    Junction,
    RoadSegment,
    
    # Junction/Signal models
    SignalColor,
    SignalState,
    JunctionSignals,
    ConnectedRoads,
    JunctionMetrics,
    create_default_signals,
    
    # Road models
    RoadGeometry,
    RoadTraffic,
    
    # Live Traffic models
    LiveTrafficData,
    TrafficIncident,
    
    # Coordinate models
    MapBounds,
    GPSCoordinate,
    CanvasCoordinate,
    CoordinateConverter,
    GANDHINAGAR_BOUNDS,
    
    # Traffic Control models
    TrafficDataMode,
    TrafficDataSource,
    ManualTrafficOverride,
    MapArea,
    
    # Detection models
    DetectionRecord,
    
    # Violation models
    TrafficViolation,
    ViolationEvidence,
    
    # Challan models
    VehicleOwner,
    Challan,
    ChallanTransaction,
    
    # Emergency models
    EmergencyVehicle,
    EmergencyCorridor,
    
    # Incident models
    Incident,
    RouteInference,
    
    # Prediction models
    CongestionPrediction,
    PredictionAlert,
    
    # System State models
    SystemState,
    SimulationState,
    AgentState,
    PerformanceMetrics,
)


class TestPositionModel:
    """Tests for Position model"""
    
    def test_create_position(self):
        pos = Position(x=100.0, y=200.0)
        assert pos.x == 100.0
        assert pos.y == 200.0
    
    def test_position_json(self):
        pos = Position(x=100.0, y=200.0)
        json_str = pos.model_dump_json()
        data = json.loads(json_str)
        assert data['x'] == 100.0
        assert data['y'] == 200.0


class TestVehicleModel:
    """Tests for Vehicle model"""
    
    def test_create_vehicle(self):
        vehicle = Vehicle(
            number_plate="GJ18AB1234",
            type="car",
            position=Position(x=100, y=200),
            destination="J-9"
        )
        assert vehicle.number_plate == "GJ18AB1234"
        assert vehicle.type == "car"
        assert vehicle.id.startswith("v-")
        assert vehicle.is_emergency is False
        assert vehicle.speed == 0.0
    
    def test_vehicle_id_generation(self):
        v1 = Vehicle(number_plate="TEST1", type="car", position=Position(x=0, y=0), destination="J-1")
        v2 = Vehicle(number_plate="TEST2", type="car", position=Position(x=0, y=0), destination="J-1")
        assert v1.id != v2.id
    
    def test_vehicle_type_validation(self):
        with pytest.raises(ValidationError):
            Vehicle(
                number_plate="TEST",
                type="truck",  # Invalid type
                position=Position(x=0, y=0),
                destination="J-1"
            )
    
    def test_emergency_vehicle(self):
        vehicle = Vehicle(
            number_plate="GJ18AMB001",
            type="ambulance",
            position=Position(x=0, y=0),
            destination="J-9",
            is_emergency=True
        )
        assert vehicle.is_emergency is True
        assert vehicle.type == "ambulance"
    
    def test_vehicle_json_serialization(self):
        vehicle = Vehicle(
            number_plate="TEST123",
            type="bike",
            position=Position(x=50, y=100),
            destination="J-5"
        )
        data = vehicle.model_dump()
        assert 'id' in data
        assert data['number_plate'] == "TEST123"
        assert data['position']['x'] == 50


class TestSignalModels:
    """Tests for Signal and Junction models"""
    
    def test_signal_color_enum(self):
        assert SignalColor.RED.value == "RED"
        assert SignalColor.GREEN.value == "GREEN"
        assert SignalColor.YELLOW.value == "YELLOW"
    
    def test_signal_state(self):
        state = SignalState(
            current=SignalColor.GREEN,
            duration=30.0,
            last_change=time.time(),
            time_since_green=0.0
        )
        assert state.current == SignalColor.GREEN
        assert state.duration == 30.0
    
    def test_junction_signals(self):
        signals = create_default_signals('north')
        assert signals.north.current == SignalColor.GREEN
        assert signals.east.current == SignalColor.RED
        assert signals.south.current == SignalColor.RED
        assert signals.west.current == SignalColor.RED
    
    def test_junction_get_green_direction(self):
        signals = create_default_signals('east')
        assert signals.get_green_direction() == 'east'
    
    def test_junction(self):
        junction = Junction(
            id="J-1",
            position=Position(x=200, y=200),
            signals=create_default_signals('north'),
            connected_roads=ConnectedRoads(north="R-1", east="R-2"),
            last_signal_change=time.time()
        )
        assert junction.id == "J-1"
        assert junction.mode == 'NORMAL'


class TestRoadModels:
    """Tests for Road models"""
    
    def test_road_geometry(self):
        geo = RoadGeometry(
            start_pos=Position(x=0, y=0),
            end_pos=Position(x=100, y=0),
            length=100.0,
            lanes=2
        )
        dx, dy = geo.get_direction_vector()
        assert dx == 1.0
        assert dy == 0.0
    
    def test_road_traffic(self):
        traffic = RoadTraffic(capacity=20)
        assert traffic.vehicle_count == 0
        assert traffic.congestion_ratio == 0
        
        traffic.current_vehicles = ["v1", "v2", "v3"]
        assert traffic.vehicle_count == 3
        assert traffic.congestion_ratio == 0.15
    
    def test_road_segment(self):
        road = RoadSegment(
            id="R-1-2",
            start_junction="J-1",
            end_junction="J-2",
            geometry=RoadGeometry(
                start_pos=Position(x=0, y=0),
                end_pos=Position(x=200, y=0),
                length=200.0,
                lanes=2
            ),
            last_update=time.time()
        )
        assert road.id == "R-1-2"
        
        road.add_vehicle("v-1")
        assert "v-1" in road.traffic.current_vehicles
        
        road.remove_vehicle("v-1")
        assert "v-1" not in road.traffic.current_vehicles


class TestLiveTrafficModels:
    """Tests for Live Traffic API models"""
    
    def test_live_traffic_data(self):
        data = LiveTrafficData(
            road_id="R-1-2",
            current_speed=25.0,
            free_flow_speed=50.0,
            congestion_level="MEDIUM",
            confidence=85.0,
            timestamp="2026-01-10T10:00:00Z",
            source="API",
            provider="tomtom"
        )
        assert data.road_id == "R-1-2"
        assert data.speed_ratio == 0.5
    
    def test_congestion_level_calculation(self):
        assert LiveTrafficData.calculate_congestion_level(45, 50) == 'LOW'
        assert LiveTrafficData.calculate_congestion_level(30, 50) == 'MEDIUM'
        assert LiveTrafficData.calculate_congestion_level(15, 50) == 'HIGH'
        assert LiveTrafficData.calculate_congestion_level(5, 50) == 'JAM'


class TestCoordinateModels:
    """Tests for Coordinate conversion models"""
    
    def test_map_bounds(self):
        bounds = MapBounds(north=23.25, south=23.20, east=72.68, west=72.60)
        assert bounds.lat_range == pytest.approx(0.05)
        assert bounds.lon_range == pytest.approx(0.08)
    
    def test_coordinate_converter(self):
        bounds = MapBounds(north=23.25, south=23.20, east=72.68, west=72.60)
        converter = CoordinateConverter(
            canvas_width=1200,
            canvas_height=800,
            map_bounds=bounds,
            padding=20
        )
        
        # Test center point
        center_lat = 23.225
        center_lon = 72.64
        canvas = converter.gps_to_canvas(center_lat, center_lon)
        
        # Should be roughly in the middle
        assert 500 < canvas.x < 700
        assert 350 < canvas.y < 450
        
        # Test round-trip conversion
        gps_back = converter.canvas_to_gps(canvas.x, canvas.y)
        assert gps_back.lat == pytest.approx(center_lat, abs=0.001)
        assert gps_back.lon == pytest.approx(center_lon, abs=0.001)


class TestViolationModels:
    """Tests for Violation and Challan models"""
    
    def test_traffic_violation(self):
        violation = TrafficViolation(
            vehicle_id="v-123",
            number_plate="GJ18AB1234",
            violation_type="RED_LIGHT",
            location="J-5",
            evidence=ViolationEvidence(signal_state="RED")
        )
        assert violation.violation_type == "RED_LIGHT"
        assert violation.processed is False
    
    def test_challan(self):
        challan = Challan(
            violation_id="vio-123",
            number_plate="GJ18AB1234",
            owner_name="John Doe",
            violation_type="RED_LIGHT",
            fine_amount=1000.0,
            location="J-5",
            violation_timestamp=time.time()
        )
        assert challan.challan_id.startswith("CH-")
        assert challan.status == "ISSUED"
        assert challan.fine_amount == 1000.0


class TestEmergencyModels:
    """Tests for Emergency models"""
    
    def test_emergency_vehicle(self):
        vehicle = EmergencyVehicle(
            type="ambulance",
            number_plate="GJ18AMB001",
            position=Position(x=100, y=200),
            origin="J-1",
            destination="J-9",
            route=["J-1", "J-2", "J-5", "J-8", "J-9"]
        )
        assert vehicle.type == "ambulance"
        assert len(vehicle.route) == 5
    
    def test_emergency_corridor(self):
        corridor = EmergencyCorridor(
            vehicle_id="emv-123",
            path=["J-1", "J-2", "J-5"],
            affected_junctions=["J-2", "J-5"],
            signal_overrides={"J-2": "east", "J-5": "south"}
        )
        assert corridor.status == "ACTIVE"
        assert len(corridor.affected_junctions) == 2


class TestSystemStateModels:
    """Tests for System State models"""
    
    def test_system_state(self):
        state = SystemState()
        assert state.mode == "NORMAL"
        assert state.agent.status == "STOPPED"
        assert state.simulation.is_running is False
    
    def test_system_state_json(self):
        state = SystemState(
            mode="EMERGENCY",
            active_emergency=True,
            emergency_vehicle_id="emv-123"
        )
        data = state.model_dump()
        assert data['mode'] == "EMERGENCY"
        assert data['active_emergency'] is True


class TestPredictionModels:
    """Tests for Prediction models"""
    
    def test_congestion_prediction(self):
        prediction = CongestionPrediction(
            location_id="R-1-2",
            location_type="ROAD",
            current_density=45.0,
            current_classification="MEDIUM",
            predicted_density=75.0,
            predicted_classification="HIGH",
            confidence=80.0,
            prediction_horizon=5
        )
        assert prediction.predicted_density > prediction.current_density
        assert prediction.confidence == 80.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

