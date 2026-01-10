"""
WebSocket Event Emitter

This module provides the WebSocketEmitter class for sending real-time
updates to connected clients. All server→client events are handled here.

Features:
- Centralized event emission
- Event batching for performance
- Room-based targeting
- Throttling support
- Error handling

Performance targets (FRD-01 Section 2.4):
- Event delivery latency: < 50ms
- Vehicle updates: 10 Hz (100ms intervals)
- Density updates: 1 Hz (1 second intervals)
- Prediction updates: 0.2 Hz (5 second intervals)
"""

import asyncio
import time
from typing import Dict, Any, List, Optional, Set
from collections import defaultdict

from .events import (
    ServerEvent,
    VehicleUpdateData,
    VehicleSpawnedData,
    VehicleRemovedData,
    SignalChangeData,
    DensityUpdateData,
    PredictionUpdateData,
    AgentDecisionData,
    AgentStatusUpdateData,
    EmergencyActivatedData,
    EmergencyDeactivatedData,
    EmergencyProgressData,
    FailsafeTriggeredData,
    ViolationDetectedData,
    ChallanIssuedData,
    ChallanPaidData,
    TrafficControlActiveData,
    TrafficControlRemovedData,
    LiveTrafficUpdatedData,
    LiveTrafficErrorData,
    MapLoadedData,
    DataModeChangedData,
    SystemStateUpdateData,
)


class WebSocketEmitter:
    """
    Centralized WebSocket event emitter
    
    Handles all server→client event emissions with:
    - Automatic batching for vehicle updates
    - Throttling for high-frequency events
    - Room management for targeted updates
    - Error handling and logging
    """
    
    def __init__(self, sio):
        """
        Initialize the WebSocket emitter
        
        Args:
            sio: Socket.IO AsyncServer instance
        """
        self.sio = sio
        
        # Throttling state
        self._last_vehicle_batch = 0
        self._vehicle_update_interval = 0.1  # 10 Hz
        self._pending_vehicle_updates: Dict[str, Dict[str, Any]] = {}
        
        self._last_density_update = 0
        self._density_update_interval = 1.0  # 1 Hz
        self._pending_density_updates: Dict[str, Dict[str, Any]] = {}
        
        # Subscription tracking
        self._subscriptions: Dict[str, Set[str]] = defaultdict(set)  # channel -> {sid, ...}
        
        # Statistics
        self._emit_count = 0
        self._error_count = 0
        self._last_emit_time = 0
    
    # ============================================
    # Connection Events
    # ============================================
    
    async def emit_connection_success(self, sid: str):
        """Emit connection success to specific client"""
        await self.sio.emit(
            ServerEvent.CONNECTION_SUCCESS.value,
            {
                "message": "Connected to Traffic Intelligence System",
                "timestamp": time.time(),
                "serverVersion": "1.0.0"
            },
            room=sid
        )
        self._emit_count += 1
    
    # ============================================
    # Vehicle Events
    # ============================================
    
    async def emit_vehicle_update(self, vehicle_data: Dict[str, Any], room: str = None):
        """
        Emit vehicle position update
        
        Updates are batched and throttled to 10 Hz for performance.
        
        Args:
            vehicle_data: Vehicle update data containing id, position, speed
            room: Optional room to emit to (default: broadcast)
        """
        data = {
            "vehicleId": vehicle_data.get("id"),
            "position": vehicle_data.get("position", {}),
            "speed": vehicle_data.get("speed", 0),
            "heading": vehicle_data.get("heading", 0),
            "timestamp": vehicle_data.get("last_update", time.time()),
        }
        
        # Add GPS coordinates if available
        if "lat" in vehicle_data:
            data["lat"] = vehicle_data["lat"]
        if "lon" in vehicle_data:
            data["lon"] = vehicle_data["lon"]
        
        await self._emit(ServerEvent.VEHICLE_UPDATE.value, data, room)
    
    async def emit_vehicle_batch_update(self, vehicles: List[Dict[str, Any]]):
        """
        Emit batch vehicle updates (throttled to 10 Hz)
        
        Args:
            vehicles: List of vehicle data dictionaries
        """
        now = time.time()
        
        # Throttle to 10 Hz
        if now - self._last_vehicle_batch < self._vehicle_update_interval:
            # Store pending updates
            for v in vehicles:
                self._pending_vehicle_updates[v.get("id")] = v
            return
        
        # Include any pending updates
        for v in vehicles:
            self._pending_vehicle_updates[v.get("id")] = v
        
        # Emit all pending updates
        updates = [
            {
                "vehicleId": v.get("id"),
                "position": v.get("position", {}),
                "speed": v.get("speed", 0),
                "heading": v.get("heading", 0),
                "timestamp": v.get("last_update", now),
            }
            for v in self._pending_vehicle_updates.values()
        ]
        
        await self._emit("vehicles:batch_update", {"vehicles": updates, "count": len(updates)})
        
        self._pending_vehicle_updates.clear()
        self._last_vehicle_batch = now
    
    async def emit_vehicle_spawned(self, vehicle_data: Dict[str, Any]):
        """Emit vehicle spawned event"""
        data = VehicleSpawnedData(
            vehicleId=vehicle_data.get("id"),
            numberPlate=vehicle_data.get("number_plate", ""),
            type=vehicle_data.get("type", "car"),
            position=vehicle_data.get("position", {}),
            destination=vehicle_data.get("destination", ""),
            timestamp=time.time()
        )
        await self._emit(ServerEvent.VEHICLE_SPAWNED.value, data.model_dump())
    
    async def emit_vehicle_removed(self, vehicle_id: str, reason: str = "reached_destination"):
        """Emit vehicle removed event"""
        data = VehicleRemovedData(
            vehicleId=vehicle_id,
            reason=reason,
            timestamp=time.time()
        )
        await self._emit(ServerEvent.VEHICLE_REMOVED.value, data.model_dump())
    
    # ============================================
    # Signal Events
    # ============================================
    
    async def emit_signal_change(
        self,
        junction_id: str,
        direction: str,
        new_state: str,
        previous_state: str = None,
        duration: float = 0.0
    ):
        """
        Emit signal state change
        
        Args:
            junction_id: Junction ID
            direction: Signal direction (north/east/south/west)
            new_state: New signal state (RED/YELLOW/GREEN)
            previous_state: Previous state (optional)
            duration: Duration for this state
        """
        data = SignalChangeData(
            junctionId=junction_id,
            direction=direction,
            newState=new_state,
            previousState=previous_state,
            duration=duration,
            timestamp=time.time()
        )
        await self._emit(ServerEvent.SIGNAL_CHANGE.value, data.model_dump())
    
    # ============================================
    # Density Events
    # ============================================
    
    async def emit_density_update(self, road_id: str, density_data: Dict[str, Any]):
        """
        Emit density update for a road
        
        Args:
            road_id: Road segment ID
            density_data: Density metrics
        """
        # Determine color based on classification
        classification = density_data.get("classification", "LOW")
        color_map = {"LOW": "#22c55e", "MEDIUM": "#f59e0b", "HIGH": "#ef4444"}
        
        data = DensityUpdateData(
            roadId=road_id,
            densityScore=density_data.get("density_score", 0),
            classification=classification,
            vehicleCount=density_data.get("vehicle_count", 0),
            timestamp=time.time(),
            color=color_map.get(classification, "#22c55e")
        )
        await self._emit(ServerEvent.DENSITY_UPDATE.value, data.model_dump())
    
    async def emit_density_batch_update(self, roads: Dict[str, Dict[str, Any]]):
        """
        Emit batch density updates (throttled to 1 Hz)
        
        Args:
            roads: Dictionary of road_id -> density_data
        """
        now = time.time()
        
        # Throttle to 1 Hz
        if now - self._last_density_update < self._density_update_interval:
            self._pending_density_updates.update(roads)
            return
        
        # Include pending updates
        self._pending_density_updates.update(roads)
        
        updates = []
        for road_id, data in self._pending_density_updates.items():
            classification = data.get("classification", "LOW")
            color_map = {"LOW": "#22c55e", "MEDIUM": "#f59e0b", "HIGH": "#ef4444"}
            
            updates.append({
                "roadId": road_id,
                "densityScore": data.get("density_score", 0),
                "classification": classification,
                "vehicleCount": data.get("vehicle_count", 0),
                "color": color_map.get(classification, "#22c55e")
            })
        
        await self._emit("density:batch_update", {
            "roads": updates,
            "count": len(updates),
            "timestamp": now
        })
        
        self._pending_density_updates.clear()
        self._last_density_update = now
    
    # ============================================
    # Prediction Events
    # ============================================
    
    async def emit_prediction_update(self, predictions: List[Dict[str, Any]]):
        """
        Emit prediction updates (every 5 seconds)
        
        Args:
            predictions: List of congestion predictions
        """
        data = PredictionUpdateData(
            predictions=predictions,
            generatedAt=time.time(),
            nextUpdate=time.time() + 5.0,
            modelVersion="1.0.0"
        )
        await self._emit(ServerEvent.PREDICTION_UPDATE.value, data.model_dump())
    
    # ============================================
    # Agent Events
    # ============================================
    
    async def emit_agent_decision(self, decision_data: Dict[str, Any]):
        """
        Emit agent decision
        
        Args:
            decision_data: Agent decision details
        """
        data = AgentDecisionData(
            timestamp=decision_data.get("timestamp", time.time()),
            decisions=decision_data.get("decisions", []),
            latency=decision_data.get("latency", 0),
            strategy=decision_data.get("strategy", "RL"),
            mode=decision_data.get("mode", "NORMAL")
        )
        await self._emit(ServerEvent.AGENT_DECISION.value, data.model_dump())
    
    async def emit_agent_status_update(
        self,
        status: str,
        strategy: str = "RL",
        uptime: float = 0,
        decisions: int = 0,
        avg_latency: float = 0
    ):
        """Emit agent status update"""
        data = AgentStatusUpdateData(
            status=status,
            strategy=strategy,
            uptime=uptime,
            decisions=decisions,
            avgLatency=avg_latency
        )
        await self._emit(ServerEvent.AGENT_STATUS_UPDATE.value, data.model_dump())
    
    # ============================================
    # Emergency Events
    # ============================================
    
    async def emit_emergency_activated(self, emergency_data: Dict[str, Any]):
        """
        Emit emergency mode activation
        
        Args:
            emergency_data: Emergency vehicle and corridor info
        """
        data = EmergencyActivatedData(
            vehicleId=emergency_data.get("vehicle_id"),
            corridorPath=emergency_data.get("corridor_path", []),
            estimatedTime=emergency_data.get("estimated_time", 0),
            destination=emergency_data.get("destination", ""),
            activatedAt=time.time()
        )
        await self._emit(ServerEvent.EMERGENCY_ACTIVATED.value, data.model_dump())
    
    async def emit_emergency_deactivated(self, vehicle_id: str, reason: str = "reached_destination"):
        """Emit emergency mode deactivation"""
        data = EmergencyDeactivatedData(
            vehicleId=vehicle_id,
            completionTime=time.time(),
            reason=reason
        )
        await self._emit(ServerEvent.EMERGENCY_DEACTIVATED.value, data.model_dump())
    
    async def emit_emergency_progress(self, vehicle_id: str, current_junction: str, progress: float, eta: float):
        """Emit emergency corridor progress"""
        data = EmergencyProgressData(
            vehicleId=vehicle_id,
            currentJunction=current_junction,
            progress=progress,
            estimatedArrival=eta
        )
        await self._emit(ServerEvent.EMERGENCY_PROGRESS.value, data.model_dump())
    
    # ============================================
    # Safety Events
    # ============================================
    
    async def emit_failsafe_triggered(
        self,
        reason: str,
        affected_junctions: List[str],
        previous_mode: str = "NORMAL"
    ):
        """
        Emit fail-safe activation
        
        Args:
            reason: Reason for fail-safe activation
            affected_junctions: List of affected junction IDs
            previous_mode: Mode before fail-safe
        """
        data = FailsafeTriggeredData(
            reason=reason,
            timestamp=time.time(),
            affectedJunctions=affected_junctions,
            previousMode=previous_mode,
            newMode="FAIL_SAFE",
            signalState="ALL_RED"
        )
        await self._emit(ServerEvent.FAILSAFE_TRIGGERED.value, data.model_dump())
    
    async def emit_failsafe_cleared(self):
        """Emit fail-safe cleared event"""
        await self._emit(ServerEvent.FAILSAFE_CLEARED.value, {
            "timestamp": time.time(),
            "message": "Fail-safe mode cleared, resuming normal operation"
        })
    
    # ============================================
    # Violation & Challan Events
    # ============================================
    
    async def emit_violation_detected(self, violation_data: Dict[str, Any]):
        """
        Emit traffic violation detection
        
        Args:
            violation_data: Violation details
        """
        data = ViolationDetectedData(
            id=violation_data.get("id"),
            vehicleId=violation_data.get("vehicle_id"),
            numberPlate=violation_data.get("number_plate"),
            violationType=violation_data.get("violation_type"),
            severity=violation_data.get("severity", "MEDIUM"),
            location=violation_data.get("location"),
            timestamp=time.time(),
            evidence=violation_data.get("evidence", {})
        )
        await self._emit(ServerEvent.VIOLATION_DETECTED.value, data.model_dump())
    
    async def emit_challan_issued(self, challan_data: Dict[str, Any]):
        """
        Emit challan issued
        
        Args:
            challan_data: Challan details
        """
        data = ChallanIssuedData(
            challanId=challan_data.get("challan_id"),
            numberPlate=challan_data.get("number_plate"),
            ownerName=challan_data.get("owner_name"),
            violationType=challan_data.get("violation_type"),
            fineAmount=challan_data.get("fine_amount"),
            location=challan_data.get("location"),
            timestamp=time.time()
        )
        await self._emit(ServerEvent.CHALLAN_ISSUED.value, data.model_dump())
    
    async def emit_challan_paid(self, payment_data: Dict[str, Any]):
        """
        Emit challan payment
        
        Args:
            payment_data: Payment details
        """
        data = ChallanPaidData(
            challanId=payment_data.get("challan_id"),
            transactionId=payment_data.get("transaction_id"),
            amount=payment_data.get("amount"),
            newBalance=payment_data.get("new_balance"),
            timestamp=time.time()
        )
        await self._emit(ServerEvent.CHALLAN_PAID.value, data.model_dump())
    
    # ============================================
    # Traffic Control Events
    # ============================================
    
    async def emit_traffic_control_active(self, control_data: Dict[str, Any]):
        """Emit manual control activated"""
        data = TrafficControlActiveData(
            controlId=control_data.get("id"),
            junctionId=control_data.get("junction_id"),
            direction=control_data.get("direction"),
            action=control_data.get("action"),
            duration=control_data.get("duration"),
            expiresAt=control_data.get("expires_at"),
            createdAt=time.time()
        )
        await self._emit(ServerEvent.TRAFFIC_CONTROL_ACTIVE.value, data.model_dump())
    
    async def emit_traffic_control_removed(self, control_id: str, reason: str = "expired"):
        """Emit manual control removed"""
        data = TrafficControlRemovedData(
            controlId=control_id,
            reason=reason
        )
        await self._emit(ServerEvent.TRAFFIC_CONTROL_REMOVED.value, data.model_dump())
    
    # ============================================
    # Live Traffic Events (NEW v2.0)
    # ============================================
    
    async def emit_live_traffic_updated(
        self,
        roads: Dict[str, Dict[str, Any]],
        provider: str = "tomtom"
    ):
        """
        Emit live traffic data update
        
        Args:
            roads: Dictionary of road_id -> live traffic data
            provider: API provider name
        """
        from datetime import datetime
        
        data = LiveTrafficUpdatedData(
            roads=roads,
            timestamp=datetime.utcnow().isoformat(),
            provider=provider,
            updatedCount=len(roads)
        )
        await self._emit(ServerEvent.LIVE_TRAFFIC_UPDATED.value, data.model_dump())
    
    async def emit_live_traffic_error(
        self,
        error: str,
        provider: str,
        fallback_mode: str = "SIMULATION"
    ):
        """Emit live traffic API error"""
        from datetime import datetime
        
        data = LiveTrafficErrorData(
            error=error,
            provider=provider,
            timestamp=datetime.utcnow().isoformat(),
            fallbackMode=fallback_mode
        )
        await self._emit(ServerEvent.LIVE_TRAFFIC_ERROR.value, data.model_dump())
    
    # ============================================
    # Map Events (NEW v2.0)
    # ============================================
    
    async def emit_map_loaded(self, map_data: Dict[str, Any]):
        """
        Emit map loaded event
        
        Args:
            map_data: Loaded map area info
        """
        data = MapLoadedData(
            mapArea=map_data.get("map_area", {}),
            junctionCount=map_data.get("junction_count", 0),
            roadCount=map_data.get("road_count", 0),
            loadTime=map_data.get("load_time", 0)
        )
        await self._emit(ServerEvent.MAP_LOADED.value, data.model_dump())
    
    async def emit_map_loading(self, area_name: str):
        """Emit map loading started"""
        await self._emit(ServerEvent.MAP_LOADING.value, {
            "areaName": area_name,
            "message": f"Loading map: {area_name}...",
            "timestamp": time.time()
        })
    
    async def emit_map_error(self, error: str, area_name: str = None):
        """Emit map loading error"""
        await self._emit(ServerEvent.MAP_ERROR.value, {
            "error": error,
            "areaName": area_name,
            "timestamp": time.time()
        })
    
    # ============================================
    # Data Mode Events (NEW v2.0)
    # ============================================
    
    async def emit_data_mode_changed(self, old_mode: str, new_mode: str):
        """
        Emit data mode change
        
        Args:
            old_mode: Previous mode
            new_mode: New mode
        """
        from datetime import datetime
        
        data = DataModeChangedData(
            oldMode=old_mode,
            newMode=new_mode,
            timestamp=datetime.utcnow().isoformat()
        )
        await self._emit(ServerEvent.DATA_MODE_CHANGED.value, data.model_dump())
    
    # ============================================
    # System State Events
    # ============================================
    
    async def emit_system_state_update(self, state_data: Dict[str, Any]):
        """
        Emit system state update
        
        Args:
            state_data: Current system state
        """
        data = SystemStateUpdateData(
            mode=state_data.get("mode", "NORMAL"),
            simulationTime=state_data.get("simulation_time", 0),
            isPaused=state_data.get("is_paused", False),
            vehicleCount=state_data.get("vehicle_count", 0),
            avgDensity=state_data.get("avg_density", 0),
            fps=state_data.get("fps", 60),
            timestamp=time.time()
        )
        await self._emit(ServerEvent.SYSTEM_STATE_UPDATE.value, data.model_dump())
    
    async def emit_simulation_state(self, state: Dict[str, Any]):
        """Emit complete simulation state snapshot"""
        await self._emit(ServerEvent.SIMULATION_STATE.value, {
            **state,
            "timestamp": time.time()
        })
    
    # ============================================
    # Subscription Management
    # ============================================
    
    def add_subscription(self, sid: str, channel: str):
        """Add client subscription to a channel"""
        self._subscriptions[channel].add(sid)
    
    def remove_subscription(self, sid: str, channel: str = None):
        """Remove client subscription(s)"""
        if channel:
            self._subscriptions[channel].discard(sid)
        else:
            # Remove from all channels
            for ch in self._subscriptions:
                self._subscriptions[ch].discard(sid)
    
    def get_subscribers(self, channel: str) -> Set[str]:
        """Get subscribers for a channel"""
        return self._subscriptions.get(channel, set())
    
    # ============================================
    # Internal Methods
    # ============================================
    
    async def _emit(self, event: str, data: Any, room: str = None):
        """
        Internal emit with error handling and statistics
        
        Args:
            event: Event name
            data: Event data
            room: Optional room to emit to
        """
        try:
            if room:
                await self.sio.emit(event, data, room=room)
            else:
                await self.sio.emit(event, data)
            
            self._emit_count += 1
            self._last_emit_time = time.time()
            
        except Exception as e:
            self._error_count += 1
            print(f"[WS ERROR] Failed to emit {event}: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get emitter statistics"""
        return {
            "totalEmits": self._emit_count,
            "errorCount": self._error_count,
            "lastEmitTime": self._last_emit_time,
            "pendingVehicleUpdates": len(self._pending_vehicle_updates),
            "pendingDensityUpdates": len(self._pending_density_updates),
            "subscriptionChannels": len(self._subscriptions),
            "totalSubscribers": sum(len(s) for s in self._subscriptions.values())
        }


# Global emitter instance (initialized in main.py)
emitter: Optional[WebSocketEmitter] = None


def get_emitter() -> Optional[WebSocketEmitter]:
    """Get the global WebSocket emitter instance"""
    return emitter


def set_emitter(e: WebSocketEmitter):
    """Set the global WebSocket emitter instance"""
    global emitter
    emitter = e

