"""
Simulation Manager

Core traffic simulation engine that manages vehicle movement,
traffic signals, and simulation timing.
"""

import threading
import time
from typing import Dict, List, Optional, Any
from enum import Enum
import random
import math

from app.models.vehicle import Vehicle, Position, VehicleSpawnRequest
from app.services.map_loader_service import get_map_loader_service


class SimulationState(Enum):
    """Simulation states"""
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"


class SimulationManager:
    """
    Main simulation manager for traffic flow

    Handles vehicle spawning, movement, traffic signals, and timing.
    """

    def __init__(self):
        # Simulation state
        self.state = SimulationState.STOPPED
        self.start_time = 0.0
        self.current_time = 0.0
        self.time_multiplier = 1
        self.last_update = time.time()

        # Vehicles
        self.vehicles: Dict[str, Vehicle] = {}
        self.vehicles_spawned = 0
        self.vehicles_reached = 0

        # Junction and road data (loaded from map_loader_service)
        self.junctions: Dict[str, Any] = {}
        self.roads: Dict[str, Any] = {}
        self.junction_positions: Dict[str, Position] = {}
        self.road_connections: Dict[str, List[str]] = {}  # junction_id -> connected_junctions

        # Simulation thread
        self.simulation_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()

        # Initialize map data
        self._load_map_data()

    def _load_map_data(self):
        """Load junction and road data from map loader service"""
        try:
            loader = get_map_loader_service()
            # Use the hardcoded grid data
            junctions_data = loader.load_major_circles_only()

            # Convert to our internal format
            for j in junctions_data:
                self.junctions[j.id] = j
                self.junction_positions[j.id] = Position(x=j.x, y=j.y)
                self.road_connections[j.id] = []

            # Load roads and build connections
            from app.api.system_routes import HARDCODED_ROADS
            for road in HARDCODED_ROADS:
                self.roads[road["id"]] = road
                start_id = road["startJunction"]
                end_id = road["endJunction"]

                if start_id not in self.road_connections:
                    self.road_connections[start_id] = []
                if end_id not in self.road_connections:
                    self.road_connections[end_id] = []

                if end_id not in self.road_connections[start_id]:
                    self.road_connections[start_id].append(end_id)
                if start_id not in self.road_connections[end_id]:
                    self.road_connections[end_id].append(start_id)

            print(f"[SimulationManager] Loaded {len(self.junctions)} junctions and {len(self.roads)} roads")

        except Exception as e:
            print(f"[SimulationManager] Error loading map data: {e}")
            # Fallback to empty data
            pass

    def start(self):
        """Start the simulation"""
        if self.state == SimulationState.RUNNING:
            return

        self.state = SimulationState.RUNNING
        self.start_time = time.time()
        self.current_time = 0.0
        self.last_update = time.time()
        self.stop_event.clear()

        # Start simulation thread
        self.simulation_thread = threading.Thread(target=self._simulation_loop, daemon=True)
        self.simulation_thread.start()

        print("[SimulationManager] Simulation started")

    def stop(self):
        """Stop the simulation"""
        if self.state == SimulationState.STOPPED:
            return

        self.state = SimulationState.STOPPED
        self.stop_event.set()

        if self.simulation_thread:
            self.simulation_thread.join(timeout=1.0)

        print("[SimulationManager] Simulation stopped")

    def pause(self):
        """Pause the simulation"""
        if self.state == SimulationState.RUNNING:
            self.state = SimulationState.PAUSED
            print("[SimulationManager] Simulation paused")

    def resume(self):
        """Resume the simulation"""
        if self.state == SimulationState.PAUSED:
            self.state = SimulationState.RUNNING
            self.last_update = time.time()
            print("[SimulationManager] Simulation resumed")

    def reset(self):
        """Reset simulation to initial state"""
        self.stop()
        self.vehicles.clear()
        self.vehicles_spawned = 0
        self.vehicles_reached = 0
        self.current_time = 0.0
        print("[SimulationManager] Simulation reset")

    def set_speed(self, multiplier: int):
        """Set simulation speed multiplier"""
        self.time_multiplier = multiplier
        print(f"[SimulationManager] Speed set to {multiplier}x")

    def get_status(self) -> Dict[str, Any]:
        """Get simulation status"""
        return {
            "running": self.state == SimulationState.RUNNING,
            "paused": self.state == SimulationState.PAUSED,
            "currentTime": self.current_time,
            "timeMultiplier": self.time_multiplier,
            "totalVehicles": len(self.vehicles),
            "vehiclesSpawned": self.vehicles_spawned,
            "vehiclesReached": self.vehicles_reached,
            "startTime": self.start_time
        }

    def spawn_vehicle(self, vehicle_type: str = "car", start_junction: str = None, end_junction: str = None) -> Vehicle:
        """Spawn a new vehicle"""
        if not start_junction:
            # Random start junction
            junction_ids = list(self.junctions.keys())
            if not junction_ids:
                raise ValueError("No junctions available")
            start_junction = random.choice(junction_ids)

        if not end_junction:
            # Random end junction different from start
            possible_ends = [j for j in self.junctions.keys() if j != start_junction]
            if not possible_ends:
                raise ValueError("No destination junctions available")
            end_junction = random.choice(possible_ends)

        # Calculate path
        path = self._calculate_path(start_junction, end_junction)
        if not path:
            raise ValueError(f"No path found from {start_junction} to {end_junction}")

        # Create vehicle at start junction
        start_pos = self.junction_positions.get(start_junction, Position(x=0, y=0))
        start_junction_obj = self.junctions.get(start_junction)

        vehicle = Vehicle(
            number_plate=self._generate_number_plate(),
            type=vehicle_type,
            position=start_pos,
            current_junction=start_junction,
            destination=end_junction,
            path=path,
            path_index=0,
            is_emergency=(vehicle_type == "ambulance"),
            lat=start_junction_obj.lat if start_junction_obj else None,
            lon=start_junction_obj.lon if start_junction_obj else None
        )

        self.vehicles[vehicle.id] = vehicle
        self.vehicles_spawned += 1

        print(f"[SimulationManager] Spawned {vehicle_type} {vehicle.id} from {start_junction} to {end_junction}")

        return vehicle

    def _calculate_path(self, start_junction: str, end_junction: str) -> List[str]:
        """Calculate path between junctions using BFS"""
        if start_junction not in self.road_connections or end_junction not in self.road_connections:
            return []

        # Simple BFS for pathfinding
        from collections import deque

        queue = deque([(start_junction, [start_junction])])
        visited = set([start_junction])

        while queue:
            current, path = queue.popleft()

            if current == end_junction:
                return path

            for neighbor in self.road_connections.get(current, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))

        return []  # No path found

    def _generate_number_plate(self) -> str:
        """Generate a random Gujarat number plate"""
        states = ["GJ"]
        districts = ["01", "18", "05", "06", "27"]
        letters = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=2))
        numbers = "".join(random.choices("0123456789", k=4))

        return f"{random.choice(states)}{random.choice(districts)}{letters}{numbers}"

    def _simulation_loop(self):
        """Main simulation loop"""
        while not self.stop_event.is_set():
            if self.state == SimulationState.RUNNING:
                current_time = time.time()
                delta_time = (current_time - self.last_update) * self.time_multiplier
                self.current_time += delta_time
                self.last_update = current_time

                # Update all vehicles
                self._update_vehicles(delta_time)

                # Spawn new vehicles occasionally
                if random.random() < 0.02:  # 2% chance per update
                    try:
                        self.spawn_vehicle()
                    except Exception as e:
                        pass  # Silently ignore spawn failures

            time.sleep(0.1)  # 10 FPS update rate

    def _update_vehicles(self, delta_time: float):
        """Update all vehicles in the simulation"""
        vehicles_to_remove = []

        for vehicle_id, vehicle in self.vehicles.items():
            try:
                self._update_vehicle(vehicle, delta_time)

                # Check if vehicle reached destination
                if vehicle.current_junction == vehicle.destination:
                    vehicles_to_remove.append(vehicle_id)
                    self.vehicles_reached += 1

            except Exception as e:
                print(f"[SimulationManager] Error updating vehicle {vehicle_id}: {e}")
                vehicles_to_remove.append(vehicle_id)

        # Remove vehicles that reached destination
        for vehicle_id in vehicles_to_remove:
            if vehicle_id in self.vehicles:
                vehicle = self.vehicles[vehicle_id]
                print(f"[SimulationManager] Vehicle {vehicle.id} reached destination {vehicle.destination}")
                del self.vehicles[vehicle_id]

    def _update_vehicle(self, vehicle: Vehicle, delta_time: float):
        """Update a single vehicle's position and state"""
        # If vehicle is at a junction, decide next action
        if vehicle.current_junction:
            self._handle_junction_logic(vehicle, delta_time)
        else:
            # Vehicle is on a road, move towards next junction
            self._handle_road_movement(vehicle, delta_time)

    def _handle_junction_logic(self, vehicle: Vehicle, delta_time: float):
        """Handle vehicle behavior when at a junction"""
        current_idx = vehicle.path_index

        # Check if we've reached the destination
        if current_idx >= len(vehicle.path) - 1:
            vehicle.current_junction = vehicle.destination
            return

        next_junction = vehicle.path[current_idx + 1]

        # Check if we can proceed (traffic signal logic would go here)
        if self._can_proceed_through_junction(vehicle, next_junction):
            # Move to the road towards next junction
            vehicle.current_junction = None
            vehicle.current_road = self._get_road_between_junctions(vehicle.path[current_idx], next_junction)
            vehicle.path_index = current_idx + 1

            # Set initial direction towards next junction
            next_pos = self.junction_positions.get(next_junction, vehicle.position)
            dx = next_pos.x - vehicle.position.x
            dy = next_pos.y - vehicle.position.y
            vehicle.heading = math.degrees(math.atan2(dy, dx)) % 360
        else:
            # Wait at junction
            vehicle.increment_waiting_time(delta_time)
            vehicle.speed = 0.0

    def _handle_road_movement(self, vehicle: Vehicle, delta_time: float):
        """Handle vehicle movement when on a road"""
        if not vehicle.current_road or vehicle.path_index >= len(vehicle.path):
            return

        next_junction = vehicle.path[vehicle.path_index]
        target_pos = self.junction_positions.get(next_junction)

        if not target_pos:
            return

        # Calculate direction and distance to target
        dx = target_pos.x - vehicle.position.x
        dy = target_pos.y - vehicle.position.y
        distance = math.sqrt(dx*dx + dy*dy)

        # If close enough to junction, snap to it
        if distance < 5.0:  # 5 pixel threshold
            vehicle.position.x = target_pos.x
            vehicle.position.y = target_pos.y
            vehicle.current_junction = next_junction
            vehicle.current_road = None
            vehicle.speed = 0.0
            return

        # Move towards target
        max_speed = 50.0  # km/h
        speed_pixels_per_second = max_speed * 1000 / 3600 * 10  # Rough conversion to pixels/second

        move_distance = min(speed_pixels_per_second * delta_time, distance)

        # Normalize direction
        if distance > 0:
            dx /= distance
            dy /= distance

            # Update position
            vehicle.position.x += dx * move_distance
            vehicle.position.y += dy * move_distance
            vehicle.speed = max_speed
            vehicle.heading = math.degrees(math.atan2(dy, dx)) % 360

    def _can_proceed_through_junction(self, vehicle: Vehicle, next_junction: str) -> bool:
        """Check if vehicle can proceed through junction (traffic signals)"""
        # For now, simple random logic - vehicles can proceed 70% of the time
        # In a real implementation, this would check traffic signals
        return random.random() < 0.7

    def _get_road_between_junctions(self, j1: str, j2: str) -> Optional[str]:
        """Get road ID between two junctions"""
        for road_id, road in self.roads.items():
            if (road["startJunction"] == j1 and road["endJunction"] == j2) or \
               (road["startJunction"] == j2 and road["endJunction"] == j1):
                return road_id
        return None

    def get_vehicles(self, vehicle_type: str = None, junction: str = None) -> List[Vehicle]:
        """Get vehicles, optionally filtered"""
        vehicles = list(self.vehicles.values())

        if vehicle_type:
            vehicles = [v for v in vehicles if v.type == vehicle_type]

        if junction:
            vehicles = [v for v in vehicles if v.current_junction == junction]

        return vehicles

    def get_vehicle(self, vehicle_id: str) -> Optional[Vehicle]:
        """Get specific vehicle by ID"""
        return self.vehicles.get(vehicle_id)

    def get_roads(self) -> List[Dict[str, Any]]:
        """Get all roads"""
        return list(self.roads.values())


# Global simulation manager instance
_simulation_manager: Optional[SimulationManager] = None


def get_simulation_manager() -> SimulationManager:
    """Get the global simulation manager instance"""
    global _simulation_manager
    if _simulation_manager is None:
        _simulation_manager = SimulationManager()
    return _simulation_manager


def init_simulation_manager():
    """Initialize the simulation manager (for explicit initialization)"""
    global _simulation_manager
    if _simulation_manager is None:
        _simulation_manager = SimulationManager()
    return _simulation_manager