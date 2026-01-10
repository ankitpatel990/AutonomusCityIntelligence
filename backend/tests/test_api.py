"""
API Endpoint Tests

This module tests all REST API endpoints defined in FRD-01.
Tests cover:
- System state endpoints
- Agent control endpoints
- Simulation control endpoints
- Traffic control endpoints
- Emergency endpoints
- Incident endpoints
- Challan/Violation endpoints
- Prediction endpoints
"""

import pytest
from fastapi.testclient import TestClient
import time

from app.main import app

client = TestClient(app)


# ============================================
# Root & Health Endpoints
# ============================================

class TestRootEndpoints:
    """Test root and health endpoints"""
    
    def test_root_endpoint(self):
        """Test GET /"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "status" in data
        assert data["status"] == "operational"
    
    def test_health_check(self):
        """Test GET /health"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data


# ============================================
# System State Endpoints
# ============================================

class TestSystemEndpoints:
    """Test system state endpoints (FRD-01 Section 2.3)"""
    
    def test_get_system_state(self):
        """Test GET /api/state"""
        response = client.get("/api/state")
        assert response.status_code == 200
        data = response.json()
        assert "mode" in data
        assert "simulation" in data
        assert "agent" in data
        assert "performance" in data
        assert "dataSource" in data
    
    def test_get_vehicles(self):
        """Test GET /api/vehicles"""
        response = client.get("/api/vehicles")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_get_vehicles_filtered(self):
        """Test GET /api/vehicles with filters"""
        response = client.get("/api/vehicles?type=car")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_get_junctions(self):
        """Test GET /api/junctions"""
        response = client.get("/api/junctions")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_get_roads(self):
        """Test GET /api/roads"""
        response = client.get("/api/roads")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_get_density(self):
        """Test GET /api/density"""
        response = client.get("/api/density")
        assert response.status_code == 200
        data = response.json()
        assert "citywide" in data
        assert "perJunction" in data
        assert "perRoad" in data
    
    def test_get_road_densities(self):
        """Test GET /api/density/roads"""
        response = client.get("/api/density/roads")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_get_junction_densities(self):
        """Test GET /api/density/junctions"""
        response = client.get("/api/density/junctions")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


# ============================================
# Agent Control Endpoints
# ============================================

class TestAgentEndpoints:
    """Test agent control endpoints (FRD-01 Section 2.3)"""
    
    def test_start_agent(self):
        """Test POST /api/agent/start"""
        response = client.post("/api/agent/start", json={"strategy": "RL"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "started"
        assert "timestamp" in data
    
    def test_start_agent_rule_based(self):
        """Test POST /api/agent/start with RULE_BASED strategy"""
        response = client.post("/api/agent/start", json={"strategy": "RULE_BASED"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "started"
    
    def test_stop_agent(self):
        """Test POST /api/agent/stop"""
        response = client.post("/api/agent/stop")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "stopped"
    
    def test_pause_agent(self):
        """Test POST /api/agent/pause"""
        response = client.post("/api/agent/pause")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "paused"
    
    def test_resume_agent(self):
        """Test POST /api/agent/resume"""
        response = client.post("/api/agent/resume")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "resumed"
    
    def test_get_agent_status(self):
        """Test GET /api/agent/status"""
        response = client.get("/api/agent/status")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "strategy" in data
        assert "uptime" in data
        assert "decisions" in data
        assert "avgLatency" in data
    
    def test_get_agent_logs(self):
        """Test GET /api/agent/logs"""
        response = client.get("/api/agent/logs")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_get_agent_logs_with_params(self):
        """Test GET /api/agent/logs with pagination"""
        response = client.get("/api/agent/logs?limit=10&offset=0")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


# ============================================
# Simulation Control Endpoints
# ============================================

class TestSimulationEndpoints:
    """Test simulation control endpoints"""
    
    def test_start_simulation(self):
        """Test POST /api/simulation/start"""
        response = client.post("/api/simulation/start")
        assert response.status_code == 200
        assert response.json()["status"] == "started"
    
    def test_stop_simulation(self):
        """Test POST /api/simulation/stop"""
        response = client.post("/api/simulation/stop")
        assert response.status_code == 200
        assert response.json()["status"] == "stopped"
    
    def test_pause_simulation(self):
        """Test POST /api/simulation/pause"""
        response = client.post("/api/simulation/pause")
        assert response.status_code == 200
        assert response.json()["status"] == "paused"
    
    def test_resume_simulation(self):
        """Test POST /api/simulation/resume"""
        response = client.post("/api/simulation/resume")
        assert response.status_code == 200
        assert response.json()["status"] == "resumed"
    
    def test_reset_simulation(self):
        """Test POST /api/simulation/reset"""
        response = client.post("/api/simulation/reset")
        assert response.status_code == 200
        assert response.json()["status"] == "reset"
    
    def test_set_simulation_speed(self):
        """Test POST /api/simulation/speed"""
        response = client.post("/api/simulation/speed", json={"multiplier": 5})
        assert response.status_code == 200
        data = response.json()
        assert data["multiplier"] == 5
    
    def test_get_simulation_status(self):
        """Test GET /api/simulation/status"""
        response = client.get("/api/simulation/status")
        assert response.status_code == 200
        data = response.json()
        assert "running" in data
        assert "paused" in data
        assert "currentTime" in data


# ============================================
# Traffic Control Endpoints
# ============================================

class TestTrafficEndpoints:
    """Test traffic control endpoints"""
    
    def test_create_junction_override(self):
        """Test POST /api/traffic/junction/override"""
        response = client.post("/api/traffic/junction/override", json={
            "junctionId": "J-1",
            "direction": "N",
            "action": "FORCE_GREEN",
            "duration": 30
        })
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["junctionId"] == "J-1"
    
    def test_get_active_controls(self):
        """Test GET /api/traffic/controls"""
        response = client.get("/api/traffic/controls")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_set_traffic_mode(self):
        """Test POST /api/traffic/control/mode"""
        response = client.post("/api/traffic/control/mode", json={
            "mode": "SIMULATION"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "SIMULATION"
    
    def test_get_traffic_control_status(self):
        """Test GET /api/traffic/control/status"""
        response = client.get("/api/traffic/control/status")
        assert response.status_code == 200
        data = response.json()
        assert "mode" in data
        assert "activeOverrides" in data


# ============================================
# Map Endpoints
# ============================================

class TestMapEndpoints:
    """Test map loading endpoints"""
    
    def test_get_predefined_areas(self):
        """Test GET /api/map/predefined"""
        response = client.get("/api/map/predefined")
        assert response.status_code == 200
        data = response.json()
        assert "areas" in data
        assert "gift_city" in data["areas"]
    
    def test_get_current_map(self):
        """Test GET /api/map/current"""
        response = client.get("/api/map/current")
        assert response.status_code == 200
    
    def test_load_map_predefined(self):
        """Test POST /api/map/load with predefined area"""
        response = client.post("/api/map/load", json={
            "method": "predefined",
            "area": "gift_city"
        })
        assert response.status_code == 200
        data = response.json()
        assert "mapArea" in data
        assert "junctions" in data
        assert "roads" in data
    
    def test_load_map_validation(self):
        """Test POST /api/map/load with missing params"""
        response = client.post("/api/map/load", json={
            "method": "bbox"
            # Missing required bbox params
        })
        assert response.status_code == 400


# ============================================
# Emergency Endpoints
# ============================================

class TestEmergencyEndpoints:
    """Test emergency endpoints"""
    
    def test_trigger_emergency(self):
        """Test POST /api/emergency/trigger"""
        response = client.post("/api/emergency/trigger", json={
            "spawnPoint": "J-1",
            "destination": "J-9"
        })
        assert response.status_code == 200
        data = response.json()
        assert "vehicleId" in data
        assert "corridorPath" in data
        assert "estimatedTime" in data
    
    def test_get_emergency_status(self):
        """Test GET /api/emergency/status"""
        response = client.get("/api/emergency/status")
        assert response.status_code == 200
        data = response.json()
        assert "active" in data
    
    def test_clear_emergency(self):
        """Test POST /api/emergency/clear"""
        response = client.post("/api/emergency/clear")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cleared"


# ============================================
# Incident Endpoints
# ============================================

class TestIncidentEndpoints:
    """Test incident endpoints"""
    
    def test_report_incident(self):
        """Test POST /api/incident/report"""
        response = client.post("/api/incident/report", json={
            "numberPlate": "GJ18AB1234",
            "incidentTime": time.time(),
            "incidentType": "HIT_AND_RUN"
        })
        assert response.status_code == 200
        data = response.json()
        assert "incidentId" in data
        assert data["status"] == "PROCESSING"
    
    def test_get_incident(self):
        """Test GET /api/incident/{id}"""
        response = client.get("/api/incident/inc-12345")
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
    
    def test_get_inference_results(self):
        """Test GET /api/incident/{id}/inference"""
        response = client.get("/api/incident/inc-12345/inference")
        assert response.status_code == 200
        data = response.json()
        assert "incidentId" in data
        assert "detectionHistory" in data


# ============================================
# Challan & Violation Endpoints
# ============================================

class TestChallanEndpoints:
    """Test challan and violation endpoints"""
    
    def test_get_violations(self):
        """Test GET /api/violations"""
        response = client.get("/api/violations")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_get_recent_violations(self):
        """Test GET /api/violations/recent"""
        response = client.get("/api/violations/recent")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_get_challans(self):
        """Test GET /api/challans"""
        response = client.get("/api/challans")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_get_challan_stats(self):
        """Test GET /api/challans/stats"""
        response = client.get("/api/challans/stats")
        assert response.status_code == 200
        data = response.json()
        assert "totalViolations" in data
        assert "totalRevenue" in data
        assert "complianceRate" in data
    
    def test_get_owners(self):
        """Test GET /api/owners"""
        response = client.get("/api/owners")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_get_revenue_stats(self):
        """Test GET /api/revenue/stats"""
        response = client.get("/api/revenue/stats")
        assert response.status_code == 200
        data = response.json()
        assert "totalRevenue" in data
        assert "revenueToday" in data


# ============================================
# Prediction Endpoints
# ============================================

class TestPredictionEndpoints:
    """Test prediction endpoints"""
    
    def test_get_predictions(self):
        """Test GET /api/predictions"""
        response = client.get("/api/predictions")
        assert response.status_code == 200
        data = response.json()
        assert "predictions" in data
        assert "generatedAt" in data
    
    def test_get_junction_prediction(self):
        """Test GET /api/predictions/junction/{id}"""
        response = client.get("/api/predictions/junction/J-1")
        assert response.status_code == 200
        data = response.json()
        assert data["locationId"] == "J-1"
        assert data["locationType"] == "JUNCTION"
    
    def test_get_road_prediction(self):
        """Test GET /api/predictions/road/{id}"""
        response = client.get("/api/predictions/road/R-1")
        assert response.status_code == 200
        data = response.json()
        assert data["locationId"] == "R-1"
        assert data["locationType"] == "ROAD"
    
    def test_get_prediction_alerts(self):
        """Test GET /api/predictions/alerts"""
        response = client.get("/api/predictions/alerts")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


# ============================================
# Performance Tests
# ============================================

class TestAPIPerformance:
    """Test API response time requirements"""
    
    def test_state_response_time(self):
        """Test GET /api/state response time < 100ms"""
        start = time.time()
        response = client.get("/api/state")
        duration = (time.time() - start) * 1000
        
        assert response.status_code == 200
        assert duration < 100, f"Response time {duration:.2f}ms exceeds 100ms"
    
    def test_vehicles_response_time(self):
        """Test GET /api/vehicles response time < 100ms"""
        start = time.time()
        response = client.get("/api/vehicles")
        duration = (time.time() - start) * 1000
        
        assert response.status_code == 200
        assert duration < 100, f"Response time {duration:.2f}ms exceeds 100ms"
    
    def test_junctions_response_time(self):
        """Test GET /api/junctions response time < 100ms"""
        start = time.time()
        response = client.get("/api/junctions")
        duration = (time.time() - start) * 1000
        
        assert response.status_code == 200
        assert duration < 100, f"Response time {duration:.2f}ms exceeds 100ms"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
