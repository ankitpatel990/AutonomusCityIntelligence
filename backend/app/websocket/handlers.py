"""
WebSocket Client Event Handlers

This module handles all client→server WebSocket events
as specified in FRD-01 Section 2.4.

All handlers are registered with the Socket.IO server in main.py.
"""

import time
from typing import Dict, Any, Optional

from .events import (
    ClientEvent,
    SimulationControlRequest,
    VehicleSpawnRequest,
    SignalOverrideRequest,
    TrafficAdjustRequest,
    EmergencyTriggerRequest,
    MapLoadRequestData,
    TrafficModeChangeRequest,
    TrafficOverrideSetRequest,
    SubscribeRequest,
)
from .emitter import WebSocketEmitter


class WebSocketHandlers:
    """
    Centralized WebSocket event handlers
    
    Handles all client→server events and delegates to appropriate services.
    """
    
    def __init__(self, sio, emitter: WebSocketEmitter):
        """
        Initialize handlers
        
        Args:
            sio: Socket.IO AsyncServer instance
            emitter: WebSocket emitter instance
        """
        self.sio = sio
        self.emitter = emitter
        
        # Track connected clients
        self._clients: Dict[str, Dict[str, Any]] = {}
        
        # Register all event handlers
        self._register_handlers()
    
    def _register_handlers(self):
        """Register all Socket.IO event handlers"""
        
        # Connection events
        self.sio.on("connect", self.handle_connect)
        self.sio.on("disconnect", self.handle_disconnect)
        
        # Simulation control
        self.sio.on(ClientEvent.SIMULATION_CONTROL.value, self.handle_simulation_control)
        
        # Vehicle actions
        self.sio.on(ClientEvent.VEHICLE_SPAWN.value, self.handle_vehicle_spawn)
        
        # Signal actions
        self.sio.on(ClientEvent.SIGNAL_OVERRIDE.value, self.handle_signal_override)
        
        # Traffic adjustments
        self.sio.on(ClientEvent.TRAFFIC_ADJUST.value, self.handle_traffic_adjust)
        
        # Emergency actions
        self.sio.on(ClientEvent.EMERGENCY_TRIGGER.value, self.handle_emergency_trigger)
        self.sio.on(ClientEvent.EMERGENCY_CLEAR.value, self.handle_emergency_clear)
        
        # Map actions
        self.sio.on(ClientEvent.MAP_LOAD_REQUEST.value, self.handle_map_load_request)
        
        # Traffic mode actions
        self.sio.on(ClientEvent.TRAFFIC_MODE_CHANGE.value, self.handle_traffic_mode_change)
        self.sio.on(ClientEvent.TRAFFIC_OVERRIDE_SET.value, self.handle_traffic_override_set)
        self.sio.on(ClientEvent.TRAFFIC_OVERRIDE_CLEAR.value, self.handle_traffic_override_clear)
        
        # Subscriptions
        self.sio.on(ClientEvent.SUBSCRIBE_UPDATES.value, self.handle_subscribe)
        self.sio.on(ClientEvent.UNSUBSCRIBE_UPDATES.value, self.handle_unsubscribe)
    
    # ============================================
    # Connection Handlers
    # ============================================
    
    async def handle_connect(self, sid: str, environ: Dict):
        """
        Handle client connection
        
        Args:
            sid: Session ID
            environ: Connection environment
        """
        client_info = {
            "sid": sid,
            "connected_at": time.time(),
            "remote_addr": environ.get("REMOTE_ADDR", "unknown"),
            "user_agent": environ.get("HTTP_USER_AGENT", "unknown"),
            "subscriptions": []
        }
        
        self._clients[sid] = client_info
        
        print(f"[WS] Client connected: {sid} from {client_info['remote_addr']}")
        
        # Send connection success
        await self.emitter.emit_connection_success(sid)
        
        # Optionally send current state
        # await self._send_initial_state(sid)
    
    async def handle_disconnect(self, sid: str):
        """
        Handle client disconnection
        
        Args:
            sid: Session ID
        """
        if sid in self._clients:
            client = self._clients.pop(sid)
            duration = time.time() - client["connected_at"]
            print(f"[WS] Client disconnected: {sid} (duration: {duration:.1f}s)")
        
        # Clean up subscriptions
        self.emitter.remove_subscription(sid)
    
    async def _send_initial_state(self, sid: str):
        """Send initial simulation state to newly connected client"""
        # TODO: Get actual state from simulation manager
        initial_state = {
            "mode": "NORMAL",
            "simulationTime": 0,
            "isPaused": False,
            "vehicleCount": 0,
            "junctionCount": 9,
            "roadCount": 12,
            "agentStatus": "STOPPED"
        }
        
        await self.sio.emit("simulation:state", initial_state, room=sid)
    
    # ============================================
    # Simulation Control Handlers
    # ============================================
    
    async def handle_simulation_control(self, sid: str, data: Dict):
        """
        Handle simulation control commands
        
        Args:
            sid: Session ID
            data: {action: 'PAUSE' | 'RESUME' | 'RESET' | 'START' | 'STOP'}
        """
        action = data.get("action", "").upper()
        
        print(f"[WS] Simulation control: {action} from {sid}")
        
        # TODO: Integrate with actual SimulationManager
        # from app.simulation.manager import simulation_manager
        
        response = {
            "status": "success",
            "action": action,
            "timestamp": time.time()
        }
        
        if action == "PAUSE":
            # simulation_manager.pause()
            response["message"] = "Simulation paused"
        elif action == "RESUME":
            # simulation_manager.resume()
            response["message"] = "Simulation resumed"
        elif action == "RESET":
            # simulation_manager.reset()
            response["message"] = "Simulation reset"
        elif action == "START":
            # simulation_manager.start()
            response["message"] = "Simulation started"
        elif action == "STOP":
            # simulation_manager.stop()
            response["message"] = "Simulation stopped"
        else:
            response["status"] = "error"
            response["message"] = f"Unknown action: {action}"
        
        # Send response to requester
        await self.sio.emit("simulation:control:response", response, room=sid)
        
        # Broadcast state change to all clients
        if response["status"] == "success":
            await self.emitter.emit_system_state_update({
                "mode": "NORMAL",
                "simulation_time": 0,
                "is_paused": action == "PAUSE",
                "vehicle_count": 0,
                "avg_density": 0,
                "fps": 60
            })
    
    # ============================================
    # Vehicle Handlers
    # ============================================
    
    async def handle_vehicle_spawn(self, sid: str, data: Dict):
        """
        Handle manual vehicle spawn request
        
        Args:
            sid: Session ID
            data: {type, spawnPoint, destination}
        """
        vehicle_type = data.get("type", "car")
        spawn_point = data.get("spawnPoint")
        destination = data.get("destination")
        
        print(f"[WS] Vehicle spawn: {vehicle_type} from {spawn_point} to {destination}")
        
        # TODO: Integrate with SimulationManager
        # vehicle = simulation_manager.spawn_vehicle(
        #     vehicle_type=vehicle_type,
        #     spawn_point=spawn_point,
        #     destination=destination
        # )
        
        # Mock response
        vehicle_id = f"v-manual-{int(time.time() * 1000) % 100000}"
        
        response = {
            "status": "success",
            "vehicleId": vehicle_id,
            "type": vehicle_type,
            "spawnPoint": spawn_point,
            "destination": destination,
            "timestamp": time.time()
        }
        
        # Send response to requester
        await self.sio.emit("vehicle:spawn:response", response, room=sid)
        
        # Broadcast vehicle spawned to all clients
        await self.emitter.emit_vehicle_spawned({
            "id": vehicle_id,
            "number_plate": f"GJ-{vehicle_id[-4:].upper()}",
            "type": vehicle_type,
            "position": {"x": 100, "y": 100},
            "destination": destination or "J-9"
        })
    
    # ============================================
    # Signal Handlers
    # ============================================
    
    async def handle_signal_override(self, sid: str, data: Dict):
        """
        Handle manual signal override
        
        Args:
            sid: Session ID
            data: {junctionId, direction, action, duration}
        """
        junction_id = data.get("junctionId")
        direction = data.get("direction")
        action = data.get("action")
        duration = data.get("duration")
        
        print(f"[WS] Signal override: {junction_id} {direction} -> {action}")
        
        # TODO: Integrate with TrafficController
        # result = traffic_controller.override_signal(
        #     junction_id=junction_id,
        #     direction=direction,
        #     action=action,
        #     duration=duration
        # )
        
        response = {
            "status": "success",
            "junctionId": junction_id,
            "direction": direction,
            "action": action,
            "duration": duration,
            "timestamp": time.time()
        }
        
        # Send response
        await self.sio.emit("signal:override:response", response, room=sid)
        
        # Broadcast signal change
        new_state = "GREEN" if action == "FORCE_GREEN" else "RED"
        await self.emitter.emit_signal_change(
            junction_id=junction_id,
            direction=direction.lower() if direction else "north",
            new_state=new_state,
            previous_state=None,
            duration=duration or 0
        )
        
        # Emit control active
        await self.emitter.emit_traffic_control_active({
            "id": f"ctrl-{int(time.time())}",
            "junction_id": junction_id,
            "direction": direction,
            "action": action,
            "duration": duration,
            "expires_at": time.time() + duration if duration else None
        })
    
    # ============================================
    # Traffic Adjust Handlers
    # ============================================
    
    async def handle_traffic_adjust(self, sid: str, data: Dict):
        """
        Handle traffic adjustment
        
        Args:
            sid: Session ID
            data: {targetId, targetType, action, parameters}
        """
        target_id = data.get("targetId")
        target_type = data.get("targetType")
        action = data.get("action")
        parameters = data.get("parameters", {})
        
        print(f"[WS] Traffic adjust: {target_type} {target_id} -> {action}")
        
        # TODO: Implement traffic adjustment logic
        
        response = {
            "status": "success",
            "targetId": target_id,
            "targetType": target_type,
            "action": action,
            "timestamp": time.time()
        }
        
        await self.sio.emit("traffic:adjust:response", response, room=sid)
    
    # ============================================
    # Emergency Handlers
    # ============================================
    
    async def handle_emergency_trigger(self, sid: str, data: Dict):
        """
        Handle emergency trigger
        
        Args:
            sid: Session ID
            data: {spawnPoint, destination, vehicleType}
        """
        spawn_point = data.get("spawnPoint")
        destination = data.get("destination")
        vehicle_type = data.get("vehicleType", "ambulance")
        
        print(f"[EMERGENCY] Trigger from {sid}: {spawn_point} -> {destination}")
        
        # TODO: Integrate with EmergencyManager
        # result = await emergency_manager.trigger_emergency(
        #     spawn_point=spawn_point,
        #     destination=destination
        # )
        
        # Mock response
        vehicle_id = f"ev-{int(time.time())}"
        corridor_path = [spawn_point, "J-2", "J-3", destination]
        estimated_time = len(corridor_path) * 30.0
        
        response = {
            "status": "success",
            "vehicleId": vehicle_id,
            "corridorPath": corridor_path,
            "estimatedTime": estimated_time,
            "timestamp": time.time()
        }
        
        # Send response
        await self.sio.emit("emergency:trigger:response", response, room=sid)
        
        # Broadcast emergency activated
        await self.emitter.emit_emergency_activated({
            "vehicle_id": vehicle_id,
            "corridor_path": corridor_path,
            "estimated_time": estimated_time,
            "destination": destination
        })
    
    async def handle_emergency_clear(self, sid: str, data: Dict):
        """
        Handle emergency clear
        
        Args:
            sid: Session ID
            data: {vehicleId} (optional)
        """
        vehicle_id = data.get("vehicleId")
        
        print(f"[EMERGENCY] Clear from {sid}")
        
        # TODO: Integrate with EmergencyManager
        # emergency_manager.clear(vehicle_id)
        
        response = {
            "status": "success",
            "message": "Emergency mode cleared",
            "timestamp": time.time()
        }
        
        await self.sio.emit("emergency:clear:response", response, room=sid)
        
        # Broadcast emergency deactivated
        if vehicle_id:
            await self.emitter.emit_emergency_deactivated(vehicle_id, "cancelled")
    
    # ============================================
    # Map Handlers (NEW v2.0)
    # ============================================
    
    async def handle_map_load_request(self, sid: str, data: Dict):
        """
        Handle map load request
        
        Args:
            sid: Session ID
            data: {method, parameters}
        """
        method = data.get("method")
        parameters = data.get("parameters", {})
        
        print(f"[WS] Map load request: {method}")
        
        # Notify loading started
        area_name = parameters.get("area") or parameters.get("name") or "Custom Area"
        await self.emitter.emit_map_loading(area_name)
        
        # TODO: Integrate with MapService
        # result = await map_service.load_area(method, parameters)
        
        # Mock response
        response = {
            "status": "success",
            "mapArea": {
                "id": f"map-{int(time.time())}",
                "name": area_name,
                "junctionCount": 12,
                "roadCount": 15
            },
            "loadTime": 1.5,
            "timestamp": time.time()
        }
        
        await self.sio.emit("map:load:response", response, room=sid)
        
        # Broadcast map loaded
        await self.emitter.emit_map_loaded({
            "map_area": response["mapArea"],
            "junction_count": 12,
            "road_count": 15,
            "load_time": 1.5
        })
    
    # ============================================
    # Traffic Mode Handlers (NEW v2.0)
    # ============================================
    
    async def handle_traffic_mode_change(self, sid: str, data: Dict):
        """
        Handle traffic data mode change
        
        Args:
            sid: Session ID
            data: {mode, provider}
        """
        new_mode = data.get("mode")
        provider = data.get("provider")
        
        print(f"[WS] Traffic mode change: {new_mode}")
        
        # TODO: Integrate with TrafficDataService
        # old_mode = traffic_data_service.get_mode()
        # traffic_data_service.set_mode(new_mode, provider)
        
        old_mode = "SIMULATION"  # Mock
        
        response = {
            "status": "success",
            "oldMode": old_mode,
            "newMode": new_mode,
            "provider": provider,
            "timestamp": time.time()
        }
        
        await self.sio.emit("traffic:mode:response", response, room=sid)
        
        # Broadcast mode change
        await self.emitter.emit_data_mode_changed(old_mode, new_mode)
    
    async def handle_traffic_override_set(self, sid: str, data: Dict):
        """
        Handle traffic override set
        
        Args:
            sid: Session ID
            data: {roadId, congestionLevel, duration}
        """
        road_id = data.get("roadId")
        congestion_level = data.get("congestionLevel")
        duration = data.get("duration")
        
        print(f"[WS] Traffic override: {road_id} -> {congestion_level}")
        
        # TODO: Integrate with TrafficDataService
        
        response = {
            "status": "success",
            "roadId": road_id,
            "congestionLevel": congestion_level,
            "duration": duration,
            "expiresAt": time.time() + duration if duration else None,
            "timestamp": time.time()
        }
        
        await self.sio.emit("traffic:override:response", response, room=sid)
    
    async def handle_traffic_override_clear(self, sid: str, data: Dict):
        """
        Handle traffic override clear
        
        Args:
            sid: Session ID
            data: {roadId} (optional)
        """
        road_id = data.get("roadId")
        
        print(f"[WS] Traffic override clear: {road_id or 'all'}")
        
        # TODO: Integrate with TrafficDataService
        
        response = {
            "status": "success",
            "roadId": road_id,
            "message": f"Override cleared for {road_id or 'all roads'}",
            "timestamp": time.time()
        }
        
        await self.sio.emit("traffic:override:clear:response", response, room=sid)
    
    # ============================================
    # Subscription Handlers
    # ============================================
    
    async def handle_subscribe(self, sid: str, data: Dict):
        """
        Handle subscription request
        
        Args:
            sid: Session ID
            data: {channels: ['vehicles', 'signals', 'density', ...]}
        """
        channels = data.get("channels", [])
        
        for channel in channels:
            self.emitter.add_subscription(sid, channel)
            # Join Socket.IO room for channel
            await self.sio.enter_room(sid, f"channel:{channel}")
        
        if sid in self._clients:
            self._clients[sid]["subscriptions"] = channels
        
        print(f"[WS] Client {sid} subscribed to: {channels}")
        
        await self.sio.emit("subscribe:response", {
            "status": "success",
            "channels": channels,
            "timestamp": time.time()
        }, room=sid)
    
    async def handle_unsubscribe(self, sid: str, data: Dict):
        """
        Handle unsubscribe request
        
        Args:
            sid: Session ID
            data: {channels: ['vehicles', ...]}
        """
        channels = data.get("channels", [])
        
        for channel in channels:
            self.emitter.remove_subscription(sid, channel)
            # Leave Socket.IO room
            await self.sio.leave_room(sid, f"channel:{channel}")
        
        print(f"[WS] Client {sid} unsubscribed from: {channels}")
        
        await self.sio.emit("unsubscribe:response", {
            "status": "success",
            "channels": channels,
            "timestamp": time.time()
        }, room=sid)
    
    # ============================================
    # Utility Methods
    # ============================================
    
    def get_connected_clients(self) -> Dict[str, Dict[str, Any]]:
        """Get all connected clients"""
        return self._clients.copy()
    
    def get_client_count(self) -> int:
        """Get number of connected clients"""
        return len(self._clients)
    
    def is_client_connected(self, sid: str) -> bool:
        """Check if client is connected"""
        return sid in self._clients


# Global handlers instance (initialized in main.py)
handlers: Optional[WebSocketHandlers] = None


def get_handlers() -> Optional[WebSocketHandlers]:
    """Get the global WebSocket handlers instance"""
    return handlers


def set_handlers(h: WebSocketHandlers):
    """Set the global WebSocket handlers instance"""
    global handlers
    handlers = h

