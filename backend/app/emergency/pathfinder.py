"""
Emergency Pathfinder - A* Algorithm

Implements FRD-07 FR-07.2: Path calculation for emergency vehicles.
Uses A* pathfinding on the road network graph.
"""

from typing import List, Dict, Tuple, Optional, Any
import heapq
from dataclasses import dataclass, field
import time


@dataclass(order=True)
class PathNode:
    """
    Node in A* pathfinding
    
    Represents a junction being explored.
    """
    f_cost: float
    junction_id: str = field(compare=False)
    g_cost: float = field(compare=False)  # Cost from start
    h_cost: float = field(compare=False)  # Heuristic cost to goal
    parent_id: Optional[str] = field(default=None, compare=False)


class EmergencyPathfinder:
    """
    Calculate optimal path for emergency vehicle
    
    Uses A* pathfinding on road network graph.
    
    Features:
    - A* algorithm with Euclidean heuristic
    - Considers road length/weight
    - Returns junction path and road segments
    - Performance target: < 100ms
    
    Usage:
        pathfinder = EmergencyPathfinder(map_loader)
        path = pathfinder.find_path("J-0", "J-8")
        roads = pathfinder.get_road_segments_in_path(path)
    """
    
    def __init__(self, map_loader=None):
        """
        Initialize pathfinder
        
        Args:
            map_loader: MapLoaderService instance with junctions and roads
        """
        self.map_loader = map_loader
        
        # Graph structures
        self.junction_graph: Dict[str, Dict[str, float]] = {}  # junction_id -> {neighbor_id: weight}
        self.junction_positions: Dict[str, Tuple[float, float]] = {}  # junction_id -> (x, y)
        self.road_lookup: Dict[Tuple[str, str], str] = {}  # (j1, j2) -> road_id
        
        # Build graph if map loader provided
        if map_loader:
            self._build_graph_from_map_loader()
        
        print("[OK] Emergency Pathfinder initialized")
        if self.junction_graph:
            print(f"   Graph nodes: {len(self.junction_graph)}")
            print(f"   Graph edges: {sum(len(v) for v in self.junction_graph.values()) // 2}")
    
    def set_map_loader(self, map_loader):
        """Set map loader and rebuild graph"""
        self.map_loader = map_loader
        self._build_graph_from_map_loader()
    
    def _build_graph_from_map_loader(self):
        """Build graph from MapLoaderService data"""
        if not self.map_loader:
            return
        
        start_time = time.time()
        
        # Reset graphs
        self.junction_graph = {}
        self.junction_positions = {}
        self.road_lookup = {}
        
        # Get junctions and roads from map loader
        junctions = self.map_loader.junctions
        roads = self.map_loader.roads
        
        # Initialize junction nodes
        for junction in junctions:
            self.junction_graph[junction.id] = {}
            self.junction_positions[junction.id] = (junction.x, junction.y)
        
        # Add edges from roads
        for road in roads:
            start_id = road.start_junction_id
            end_id = road.end_junction_id
            weight = road.length if road.length > 0 else 100  # Default weight if no length
            
            # Add bidirectional edges (unless oneway)
            if start_id in self.junction_graph:
                self.junction_graph[start_id][end_id] = weight
                self.road_lookup[(start_id, end_id)] = road.id
            
            if not road.oneway and end_id in self.junction_graph:
                self.junction_graph[end_id][start_id] = weight
                self.road_lookup[(end_id, start_id)] = road.id
        
        elapsed = (time.time() - start_time) * 1000
        print(f"   Graph built in {elapsed:.1f}ms")
    
    def build_graph_from_data(
        self,
        junctions: List[Any],
        roads: List[Any]
    ):
        """
        Build graph from junction and road data
        
        Used when map loader is not available.
        
        Args:
            junctions: List of junction objects with id, x, y
            roads: List of road objects with start/end junction, length
        """
        self.junction_graph = {}
        self.junction_positions = {}
        self.road_lookup = {}
        
        # Initialize junctions
        for junction in junctions:
            jid = junction.id if hasattr(junction, 'id') else junction.get('id')
            x = junction.x if hasattr(junction, 'x') else junction.get('x', 0)
            y = junction.y if hasattr(junction, 'y') else junction.get('y', 0)
            
            self.junction_graph[jid] = {}
            self.junction_positions[jid] = (x, y)
        
        # Add road edges
        for road in roads:
            start_id = road.start_junction_id if hasattr(road, 'start_junction_id') else road.get('start_junction_id')
            end_id = road.end_junction_id if hasattr(road, 'end_junction_id') else road.get('end_junction_id')
            length = road.length if hasattr(road, 'length') else road.get('length', 100)
            road_id = road.id if hasattr(road, 'id') else road.get('id')
            oneway = road.oneway if hasattr(road, 'oneway') else road.get('oneway', False)
            
            # Add bidirectional edges
            if start_id in self.junction_graph:
                self.junction_graph[start_id][end_id] = length
                self.road_lookup[(start_id, end_id)] = road_id
            
            if not oneway and end_id in self.junction_graph:
                self.junction_graph[end_id][start_id] = length
                self.road_lookup[(end_id, start_id)] = road_id
    
    def build_mock_graph(self, grid_size: int = 3):
        """
        Build mock 3x3 grid graph for testing
        
        Creates a simple grid with junctions J-0 to J-8.
        """
        self.junction_graph = {}
        self.junction_positions = {}
        self.road_lookup = {}
        
        # Create grid positions
        cell_size = 300
        for row in range(grid_size):
            for col in range(grid_size):
                idx = row * grid_size + col
                jid = f"J-{idx}"
                x = 100 + col * cell_size
                y = 100 + row * cell_size
                
                self.junction_graph[jid] = {}
                self.junction_positions[jid] = (x, y)
        
        # Add edges (horizontal)
        road_idx = 0
        for row in range(grid_size):
            for col in range(grid_size - 1):
                j1 = f"J-{row * grid_size + col}"
                j2 = f"J-{row * grid_size + col + 1}"
                
                self.junction_graph[j1][j2] = cell_size
                self.junction_graph[j2][j1] = cell_size
                self.road_lookup[(j1, j2)] = f"R-{road_idx}"
                self.road_lookup[(j2, j1)] = f"R-{road_idx}"
                road_idx += 1
        
        # Add edges (vertical)
        for row in range(grid_size - 1):
            for col in range(grid_size):
                j1 = f"J-{row * grid_size + col}"
                j2 = f"J-{(row + 1) * grid_size + col}"
                
                self.junction_graph[j1][j2] = cell_size
                self.junction_graph[j2][j1] = cell_size
                self.road_lookup[(j1, j2)] = f"R-{road_idx}"
                self.road_lookup[(j2, j1)] = f"R-{road_idx}"
                road_idx += 1
        
        print(f"   Mock graph built: {len(self.junction_graph)} junctions")
    
    def find_path(
        self,
        start_junction_id: str,
        end_junction_id: str
    ) -> Optional[List[str]]:
        """
        Find shortest path between two junctions using A*
        
        Args:
            start_junction_id: Starting junction ID
            end_junction_id: Destination junction ID
        
        Returns:
            List of junction IDs in path, or None if no path found
        """
        start_time = time.time()
        
        # Build mock graph if empty
        if not self.junction_graph:
            print("[WARN] No graph loaded, building mock graph")
            self.build_mock_graph()
        
        # Validate junctions
        if start_junction_id not in self.junction_graph:
            print(f"[ERROR] Start junction not found: {start_junction_id}")
            return None
        
        if end_junction_id not in self.junction_graph:
            print(f"[ERROR] End junction not found: {end_junction_id}")
            return None
        
        # Same start and end
        if start_junction_id == end_junction_id:
            return [start_junction_id]
        
        # A* algorithm
        open_set: List[PathNode] = []
        closed_set: set = set()
        g_costs: Dict[str, float] = {start_junction_id: 0}
        parents: Dict[str, str] = {}
        
        # Start node
        h_start = self._heuristic(start_junction_id, end_junction_id)
        start_node = PathNode(
            f_cost=h_start,
            junction_id=start_junction_id,
            g_cost=0,
            h_cost=h_start
        )
        heapq.heappush(open_set, start_node)
        
        iterations = 0
        max_iterations = 10000
        
        while open_set and iterations < max_iterations:
            iterations += 1
            
            # Get node with lowest f_cost
            current = heapq.heappop(open_set)
            
            # Goal reached
            if current.junction_id == end_junction_id:
                path = self._reconstruct_path(parents, end_junction_id, start_junction_id)
                elapsed = (time.time() - start_time) * 1000
                print(f"[OK] Path found: {len(path)} junctions, {iterations} iterations, {elapsed:.1f}ms")
                return path
            
            # Skip if already processed
            if current.junction_id in closed_set:
                continue
            
            closed_set.add(current.junction_id)
            
            # Explore neighbors
            neighbors = self.junction_graph.get(current.junction_id, {})
            
            for neighbor_id, edge_weight in neighbors.items():
                if neighbor_id in closed_set:
                    continue
                
                # Calculate g_cost
                tentative_g = current.g_cost + edge_weight
                
                # Skip if not better than existing path
                if neighbor_id in g_costs and tentative_g >= g_costs[neighbor_id]:
                    continue
                
                # Update best path to neighbor
                g_costs[neighbor_id] = tentative_g
                parents[neighbor_id] = current.junction_id
                
                # Add to open set
                h_cost = self._heuristic(neighbor_id, end_junction_id)
                neighbor_node = PathNode(
                    f_cost=tentative_g + h_cost,
                    junction_id=neighbor_id,
                    g_cost=tentative_g,
                    h_cost=h_cost
                )
                heapq.heappush(open_set, neighbor_node)
        
        # No path found
        elapsed = (time.time() - start_time) * 1000
        print(f"[ERROR] No path found: {start_junction_id} -> {end_junction_id} ({iterations} iterations, {elapsed:.1f}ms)")
        return None
    
    def _heuristic(self, junction_id: str, goal_id: str) -> float:
        """
        Heuristic function for A* (Euclidean distance)
        
        Args:
            junction_id: Current junction
            goal_id: Goal junction
        
        Returns:
            Estimated distance to goal
        """
        if junction_id not in self.junction_positions or goal_id not in self.junction_positions:
            return 0.0
        
        x1, y1 = self.junction_positions[junction_id]
        x2, y2 = self.junction_positions[goal_id]
        
        return ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
    
    def _reconstruct_path(
        self,
        parents: Dict[str, str],
        end_id: str,
        start_id: str
    ) -> List[str]:
        """Reconstruct path from goal to start using parent links"""
        path = []
        current = end_id
        
        while current:
            path.append(current)
            if current == start_id:
                break
            current = parents.get(current)
        
        # Reverse to get start -> goal
        path.reverse()
        return path
    
    def get_path_distance(self, junction_path: List[str]) -> float:
        """
        Calculate total distance of a path
        
        Args:
            junction_path: List of junction IDs
        
        Returns:
            Total distance in same units as edge weights
        """
        if not junction_path or len(junction_path) < 2:
            return 0.0
        
        total_distance = 0.0
        
        for i in range(len(junction_path) - 1):
            j1 = junction_path[i]
            j2 = junction_path[i + 1]
            
            edge_weight = self.junction_graph.get(j1, {}).get(j2, 0)
            total_distance += edge_weight
        
        return total_distance
    
    def get_road_segments_in_path(self, junction_path: List[str]) -> List[str]:
        """
        Get road segment IDs for junction path
        
        Args:
            junction_path: List of junction IDs
        
        Returns:
            List of road segment IDs
        """
        if not junction_path or len(junction_path) < 2:
            return []
        
        road_ids = []
        
        for i in range(len(junction_path) - 1):
            j1 = junction_path[i]
            j2 = junction_path[i + 1]
            
            road_id = self.road_lookup.get((j1, j2))
            if road_id:
                road_ids.append(road_id)
        
        return road_ids
    
    def estimate_travel_time(
        self,
        junction_path: List[str],
        speed_kmh: float = 60.0
    ) -> float:
        """
        Estimate travel time for a path
        
        Args:
            junction_path: List of junction IDs
            speed_kmh: Average speed in km/h
        
        Returns:
            Estimated travel time in seconds
        """
        distance = self.get_path_distance(junction_path)
        
        # Convert distance to km (assuming meters)
        distance_km = distance / 1000
        
        # Calculate time
        hours = distance_km / speed_kmh if speed_kmh > 0 else 0
        seconds = hours * 3600
        
        # Add junction delay (2 seconds per junction even with green)
        junction_delay = len(junction_path) * 2
        
        return seconds + junction_delay
    
    def get_next_junctions(
        self,
        current_junction: str,
        path: List[str],
        lookahead: int = 5
    ) -> List[str]:
        """
        Get next N junctions in path from current position
        
        Args:
            current_junction: Current junction ID
            path: Complete path
            lookahead: Number of junctions to return
        
        Returns:
            List of upcoming junction IDs
        """
        if current_junction not in path:
            return path[:lookahead]
        
        try:
            current_idx = path.index(current_junction)
            return path[current_idx:current_idx + lookahead + 1]
        except (ValueError, IndexError):
            return []


# Global pathfinder instance
_emergency_pathfinder: Optional[EmergencyPathfinder] = None


def get_emergency_pathfinder() -> Optional[EmergencyPathfinder]:
    """Get global emergency pathfinder instance"""
    return _emergency_pathfinder


def init_emergency_pathfinder(map_loader=None) -> EmergencyPathfinder:
    """Initialize global emergency pathfinder"""
    global _emergency_pathfinder
    _emergency_pathfinder = EmergencyPathfinder(map_loader=map_loader)
    return _emergency_pathfinder


