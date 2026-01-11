"""
Vehicle Inference Engine (FRD-08)

Infers probable vehicle locations using graph-based analysis of detection history.
Core algorithm for post-incident vehicle tracking.

Algorithm:
1. Query detection records for the target vehicle
2. Find last known location (most recent detection)
3. Calculate time elapsed since last detection
4. Use BFS on road network to find reachable junctions
5. Assign probability based on distance and connectivity
6. Return probable locations with confidence scores
"""

import time
from collections import deque
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple, Any
import networkx as nx

from app.database.database import SessionLocal
from app.database.models import DetectionRecord
from app.incident.incident_manager import (
    IncidentInferenceResult,
    ProbableLocation,
    DetectionHistoryItem
)


@dataclass
class JunctionInfo:
    """Junction information from map"""
    id: str
    name: str
    lat: float
    lon: float


class VehicleInferenceEngine:
    """
    Infer vehicle location using graph-based analysis (FRD-08)
    
    Uses road network graph and detection history to:
    - Find last known location
    - Calculate reachable area based on elapsed time
    - Generate probable locations with confidence scores
    
    Usage:
        engine = VehicleInferenceEngine(map_service)
        result = await engine.process_incident(incident_id, plate, time)
    """
    
    def __init__(
        self,
        map_service=None,
        avg_city_speed: float = 30.0,  # km/h
        max_search_radius: float = 10.0,  # km
        detection_time_window: int = 3600  # 1 hour
    ):
        """
        Initialize inference engine
        
        Args:
            map_service: MapLoaderService for junction/road data
            avg_city_speed: Average city speed (km/h)
            max_search_radius: Maximum search radius (km)
            detection_time_window: Time window for detection query (seconds)
        """
        self.map_service = map_service
        self.avg_city_speed = avg_city_speed
        self.max_search_radius = max_search_radius
        self.detection_time_window = detection_time_window
        
        # Road network graph (built from map service)
        self._road_graph: Optional[nx.DiGraph] = None
        self._junction_cache: Dict[str, JunctionInfo] = {}
        
        # Statistics
        self.total_inferences = 0
        self.avg_inference_time_ms = 0
        
        print("[OK] Vehicle Inference Engine initialized")
    
    def set_map_service(self, map_service):
        """Set map service after initialization"""
        self.map_service = map_service
        self._build_road_graph()
    
    def _build_road_graph(self):
        """Build road network graph from map service"""
        if not self.map_service:
            print("[INFERENCE] No map service - using empty graph")
            self._road_graph = nx.DiGraph()
            return
        
        try:
            # Get junctions and roads from map service
            junctions = self.map_service.get_junctions()
            roads = self.map_service.get_roads()
            
            if not junctions:
                print("[INFERENCE] No junctions found in map")
                self._road_graph = nx.DiGraph()
                return
            
            self._road_graph = nx.DiGraph()
            
            # Add junction nodes
            for junction in junctions:
                junction_id = junction.get('id') or junction.get('junction_id')
                self._road_graph.add_node(junction_id)
                
                # Cache junction info
                self._junction_cache[junction_id] = JunctionInfo(
                    id=junction_id,
                    name=junction.get('name', f'Junction {junction_id}'),
                    lat=junction.get('lat', 0),
                    lon=junction.get('lon', 0)
                )
            
            # Add road edges
            if roads:
                for road in roads:
                    from_junction = road.get('from_junction') or road.get('fromJunction')
                    to_junction = road.get('to_junction') or road.get('toJunction')
                    
                    if from_junction and to_junction:
                        # Add edge with weight (distance in km if available)
                        weight = road.get('length_km', 0.5)  # Default 500m
                        self._road_graph.add_edge(from_junction, to_junction, weight=weight)
                        
                        # Add reverse edge if bidirectional
                        if road.get('bidirectional', True):
                            self._road_graph.add_edge(to_junction, from_junction, weight=weight)
            
            print(f"[INFERENCE] Road graph built: {self._road_graph.number_of_nodes()} nodes, "
                  f"{self._road_graph.number_of_edges()} edges")
            
        except Exception as e:
            print(f"[INFERENCE] Error building road graph: {e}")
            self._road_graph = nx.DiGraph()
    
    async def process_incident(
        self,
        incident_id: str,
        number_plate: str,
        incident_time: float,
        incident_location: Optional[Tuple[float, float]] = None
    ) -> Optional[IncidentInferenceResult]:
        """
        Process incident and generate location inference
        
        Args:
            incident_id: Unique incident ID
            number_plate: Vehicle number plate
            incident_time: When incident occurred
            incident_location: Known incident location (lat, lon)
        
        Returns:
            IncidentInferenceResult with probable locations
        """
        start_time = time.time()
        
        print(f"[INFERENCE] Processing incident {incident_id}")
        print(f"   Plate: {number_plate}")
        print(f"   Incident time: {time.ctime(incident_time)}")
        
        # 1. Query detection history
        detections = await self._query_detections(number_plate, incident_time)
        
        if not detections:
            print(f"[INFERENCE] No detections found for {number_plate}")
            
            # Return result with no data
            inference_time_ms = (time.time() - start_time) * 1000
            self._update_stats(inference_time_ms)
            
            return IncidentInferenceResult(
                incident_id=incident_id,
                number_plate=number_plate,
                last_known_junction=None,
                last_known_junction_name=None,
                last_seen_time=None,
                last_seen_lat=None,
                last_seen_lon=None,
                time_elapsed=0,
                probable_locations=[],
                search_radius=0,
                search_center_lat=incident_location[0] if incident_location else None,
                search_center_lon=incident_location[1] if incident_location else None,
                detection_history=[],
                detection_count=0,
                overall_confidence=0,
                inference_time_ms=inference_time_ms,
                generated_at=time.time()
            )
        
        print(f"[INFERENCE] Found {len(detections)} detections")
        
        # 2. Get last known location
        last_detection = detections[-1]  # Most recent
        time_elapsed = time.time() - last_detection.timestamp
        
        # 3. Build detection history
        detection_history = self._build_detection_history(detections)
        
        # 4. Calculate probable locations using BFS
        probable_locations = self._calculate_probable_locations(
            last_detection.junction_id,
            time_elapsed
        )
        
        # 5. Calculate search radius
        search_radius = self._calculate_search_radius(time_elapsed)
        
        # 6. Calculate overall confidence
        overall_confidence = self._calculate_confidence(
            detection_count=len(detections),
            time_elapsed=time_elapsed,
            last_detection_age=time.time() - last_detection.timestamp
        )
        
        # Get last junction info
        last_junction_info = self._junction_cache.get(last_detection.junction_id)
        
        inference_time_ms = (time.time() - start_time) * 1000
        self._update_stats(inference_time_ms)
        
        result = IncidentInferenceResult(
            incident_id=incident_id,
            number_plate=number_plate,
            last_known_junction=last_detection.junction_id,
            last_known_junction_name=last_junction_info.name if last_junction_info else None,
            last_seen_time=last_detection.timestamp,
            last_seen_lat=last_junction_info.lat if last_junction_info else last_detection.position_y,
            last_seen_lon=last_junction_info.lon if last_junction_info else last_detection.position_x,
            time_elapsed=time_elapsed,
            probable_locations=probable_locations,
            search_radius=search_radius,
            search_center_lat=last_junction_info.lat if last_junction_info else None,
            search_center_lon=last_junction_info.lon if last_junction_info else None,
            detection_history=detection_history,
            detection_count=len(detections),
            overall_confidence=overall_confidence,
            inference_time_ms=inference_time_ms,
            generated_at=time.time()
        )
        
        print(f"[INFERENCE] Complete: {len(probable_locations)} probable locations")
        print(f"   Last seen: {last_detection.junction_id} at {time.ctime(last_detection.timestamp)}")
        print(f"   Time elapsed: {time_elapsed/60:.1f} minutes")
        print(f"   Confidence: {overall_confidence:.1f}%")
        
        return result
    
    async def _query_detections(
        self,
        number_plate: str,
        incident_time: float
    ) -> List[DetectionRecord]:
        """Query detection records for vehicle"""
        db = SessionLocal()
        
        try:
            # Query detections from 1 hour before incident to now
            start_time = incident_time - self.detection_time_window
            end_time = time.time()
            
            detections = db.query(DetectionRecord)\
                .filter(DetectionRecord.number_plate == number_plate)\
                .filter(DetectionRecord.timestamp >= start_time)\
                .filter(DetectionRecord.timestamp <= end_time)\
                .order_by(DetectionRecord.timestamp.asc())\
                .all()
            
            return list(detections)
            
        except Exception as e:
            print(f"[INFERENCE] Detection query error: {e}")
            return []
        finally:
            db.close()
    
    def _build_detection_history(
        self,
        detections: List[DetectionRecord]
    ) -> List[DetectionHistoryItem]:
        """Build detection history from records"""
        history = []
        
        for det in detections:
            junction_info = self._junction_cache.get(det.junction_id)
            
            history.append(DetectionHistoryItem(
                junction_id=det.junction_id,
                junction_name=junction_info.name if junction_info else None,
                timestamp=det.timestamp,
                direction=det.direction or 'N',
                lat=junction_info.lat if junction_info else det.position_y,
                lon=junction_info.lon if junction_info else det.position_x
            ))
        
        return history
    
    def _calculate_probable_locations(
        self,
        last_junction: str,
        time_elapsed: float
    ) -> List[ProbableLocation]:
        """
        Calculate probable current locations using BFS
        
        Algorithm:
        1. Start from last known junction
        2. Find all reachable junctions within time window
        3. Calculate probability based on distance
        """
        if not self._road_graph or not last_junction:
            return []
        
        if last_junction not in self._road_graph:
            # Junction not in graph - return just the last known
            junction_info = self._junction_cache.get(last_junction)
            if junction_info:
                return [ProbableLocation(
                    junction_id=last_junction,
                    junction_name=junction_info.name,
                    lat=junction_info.lat,
                    lon=junction_info.lon,
                    confidence=100.0,
                    distance_from_last=0,
                    estimated_travel_time=0
                )]
            return []
        
        # Calculate max reachable distance based on time
        max_distance_km = (self.avg_city_speed * time_elapsed) / 3600
        max_distance_km = min(max_distance_km, self.max_search_radius)
        
        # Estimate max junction hops (assuming avg 0.5km between junctions)
        avg_junction_distance = 0.5  # km
        max_hops = max(1, int(max_distance_km / avg_junction_distance))
        
        # BFS to find reachable junctions
        reachable = self._bfs_reachable_junctions(last_junction, max_hops)
        
        # Calculate probability for each reachable junction
        probable_locations = []
        
        for junction_id, distance in reachable.items():
            junction_info = self._junction_cache.get(junction_id)
            
            if not junction_info:
                continue
            
            # Probability inversely proportional to distance
            # Also factor in time - closer in time = higher probability
            base_confidence = 100 / (1 + distance * 0.5)
            
            # Reduce confidence for older detections
            time_factor = max(0.3, 1 - (time_elapsed / 3600))  # Decay over an hour
            confidence = base_confidence * time_factor
            
            # Clamp confidence
            confidence = min(100, max(5, confidence))
            
            # Estimated travel time (simple calculation)
            travel_time = (distance * avg_junction_distance / self.avg_city_speed) * 3600
            
            probable_locations.append(ProbableLocation(
                junction_id=junction_id,
                junction_name=junction_info.name,
                lat=junction_info.lat,
                lon=junction_info.lon,
                confidence=round(confidence, 1),
                distance_from_last=distance,
                estimated_travel_time=round(travel_time, 0)
            ))
        
        # Sort by confidence (highest first)
        probable_locations.sort(key=lambda x: x.confidence, reverse=True)
        
        # Return top 10
        return probable_locations[:10]
    
    def _bfs_reachable_junctions(
        self,
        start: str,
        max_hops: int
    ) -> Dict[str, int]:
        """
        BFS to find all junctions reachable within max_hops
        
        Returns:
            Dict of junction_id -> distance (hops)
        """
        visited = {start: 0}
        queue = deque([(start, 0)])
        
        while queue:
            current, dist = queue.popleft()
            
            if dist >= max_hops:
                continue
            
            try:
                neighbors = self._road_graph.neighbors(current)
                
                for neighbor in neighbors:
                    if neighbor not in visited:
                        visited[neighbor] = dist + 1
                        queue.append((neighbor, dist + 1))
            except Exception:
                continue
        
        return visited
    
    def _calculate_search_radius(self, time_elapsed: float) -> float:
        """Calculate search radius in km based on elapsed time"""
        radius = (self.avg_city_speed * time_elapsed) / 3600
        return min(radius, self.max_search_radius)
    
    def _calculate_confidence(
        self,
        detection_count: int,
        time_elapsed: float,
        last_detection_age: float
    ) -> float:
        """
        Calculate overall confidence score
        
        Factors:
        - More detections = higher confidence
        - Less time elapsed = higher confidence
        - More recent detection = higher confidence
        """
        # Base confidence from detection count
        detection_confidence = min(100, detection_count * 15)
        
        # Time decay factor
        time_decay = max(0.2, 1 - (time_elapsed / (self.detection_time_window * 2)))
        
        # Recency factor
        recency_factor = max(0.3, 1 - (last_detection_age / 1800))  # 30 min decay
        
        # Combined confidence
        confidence = detection_confidence * time_decay * recency_factor
        
        return round(min(100, max(0, confidence)), 1)
    
    def _update_stats(self, inference_time_ms: float):
        """Update running statistics"""
        self.total_inferences += 1
        
        # Running average
        self.avg_inference_time_ms = (
            (self.avg_inference_time_ms * (self.total_inferences - 1) + inference_time_ms)
            / self.total_inferences
        )
    
    def get_statistics(self) -> dict:
        """Get inference engine statistics"""
        return {
            'totalInferences': self.total_inferences,
            'avgInferenceTimeMs': round(self.avg_inference_time_ms, 2),
            'avgCitySpeed': self.avg_city_speed,
            'maxSearchRadius': self.max_search_radius,
            'detectionTimeWindow': self.detection_time_window,
            'graphNodes': self._road_graph.number_of_nodes() if self._road_graph else 0,
            'graphEdges': self._road_graph.number_of_edges() if self._road_graph else 0,
            'cachedJunctions': len(self._junction_cache)
        }


# ============================================
# Global Instance Management
# ============================================

_inference_engine: Optional[VehicleInferenceEngine] = None


def init_inference_engine(
    map_service=None,
    config: dict = None
) -> VehicleInferenceEngine:
    """Initialize global inference engine"""
    global _inference_engine
    
    config = config or {}
    
    _inference_engine = VehicleInferenceEngine(
        map_service=map_service,
        avg_city_speed=config.get('avgCitySpeed', 30.0),
        max_search_radius=config.get('maxSearchRadius', 10.0),
        detection_time_window=config.get('detectionTimeWindow', 3600)
    )
    
    return _inference_engine


def get_inference_engine() -> Optional[VehicleInferenceEngine]:
    """Get global inference engine"""
    return _inference_engine


def set_inference_engine(engine: VehicleInferenceEngine):
    """Set global inference engine"""
    global _inference_engine
    _inference_engine = engine

