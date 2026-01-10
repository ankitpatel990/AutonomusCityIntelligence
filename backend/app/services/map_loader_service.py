"""
Map Loader Service

Loads real city geography from OpenStreetMap using OSMnx.
Implements FRD-01 v2.0 Real Map System requirements.

Features:
- Load map by place name (e.g., "GIFT City, Gandhinagar")
- Load map by bounding box (north, south, east, west)
- Load map by point and radius
- Load predefined areas (Gandhinagar sectors)
- GPS to Canvas coordinate conversion
- Junction and road extraction from OSM data
- Map data caching
"""

import os
import json
import time
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from pydantic import BaseModel, Field

# OSMnx may not be installed in all environments
try:
    import osmnx as ox
    import networkx as nx
    OSMNX_AVAILABLE = True
except ImportError:
    OSMNX_AVAILABLE = False
    print("[MapLoader] WARNING: osmnx not installed. Map loading will use mock data.")

from app.models import (
    MapBounds,
    GPSCoordinate,
    CanvasCoordinate,
    CoordinateConverter,
    MapArea,
    MapAreaMetadata,
    GANDHINAGAR_BOUNDS,
)
from app.models.junction import (
    Junction,
    Position,
    JunctionSignals,
    ConnectedRoads,
    JunctionMetrics,
    create_default_signals,
)
from app.models.road import (
    RoadSegment,
    RoadGeometry,
    RoadTraffic,
)


class RealJunction(BaseModel):
    """Real OSM junction with GPS coordinates"""
    id: str
    osm_id: int
    
    # GPS coordinates
    lat: float
    lon: float
    
    # Canvas coordinates (set by converter)
    x: float = 0
    y: float = 0
    
    # Metadata from OSM
    name: Optional[str] = None
    landmark: Optional[str] = None
    street_count: int = 0
    
    # Traffic signals
    signals: Optional[JunctionSignals] = None
    connected_roads: List[str] = Field(default_factory=list)
    metrics: JunctionMetrics = Field(default_factory=JunctionMetrics)
    last_signal_change: float = Field(default_factory=time.time)
    mode: str = "NORMAL"


class RealRoad(BaseModel):
    """Real OSM road segment with GPS coordinates"""
    id: str
    osm_id: str
    
    # Junction connections
    start_junction_id: str
    end_junction_id: str
    
    # GPS coordinates
    start_lat: float
    start_lon: float
    end_lat: float
    end_lon: float
    
    # Canvas coordinates (set by converter)
    start_x: float = 0
    start_y: float = 0
    end_x: float = 0
    end_y: float = 0
    
    # OSM metadata
    name: str = "Unnamed Road"
    length: float = 0  # meters
    max_speed: float = 50  # km/h
    lanes: int = 2
    road_type: Optional[str] = None
    oneway: bool = False
    
    # Traffic state
    traffic: RoadTraffic = Field(default_factory=lambda: RoadTraffic(capacity=30))
    last_update: float = Field(default_factory=time.time)


class OSMLoadResult(BaseModel):
    """Result of loading map from OpenStreetMap"""
    map_area: MapArea
    junctions: List[RealJunction]
    roads: List[RealRoad]
    bounds: MapBounds
    load_time: float
    from_cache: bool = False


class PredefinedArea(BaseModel):
    """A predefined map area configuration"""
    key: str
    name: str
    description: str
    bounds: MapBounds
    place_name: Optional[str] = None
    estimated_junctions: int = 0
    estimated_roads: int = 0


# Predefined Gandhinagar areas
PREDEFINED_AREAS: Dict[str, PredefinedArea] = {
    "gift_city": PredefinedArea(
        key="gift_city",
        name="GIFT City",
        description="Gujarat International Finance Tec-City",
        bounds=MapBounds(north=23.175, south=23.155, east=72.695, west=72.670),
        place_name="GIFT City, Gandhinagar, Gujarat, India",
        estimated_junctions=30,
        estimated_roads=50
    ),
    "sector_1_5": PredefinedArea(
        key="sector_1_5",
        name="Sector 1-5",
        description="Central Gandhinagar - Government Area",
        bounds=MapBounds(north=23.250, south=23.200, east=72.660, west=72.600),
        place_name="Sector 5, Gandhinagar, Gujarat, India",
        estimated_junctions=40,
        estimated_roads=70
    ),
    "infocity": PredefinedArea(
        key="infocity",
        name="Infocity Area",
        description="IT Hub near GIFT City",
        bounds=MapBounds(north=23.190, south=23.170, east=72.680, west=72.660),
        place_name="Infocity, Gandhinagar, Gujarat, India",
        estimated_junctions=20,
        estimated_roads=35
    ),
    "capital_complex": PredefinedArea(
        key="capital_complex",
        name="Capital Complex",
        description="Gujarat State Government Complex",
        bounds=MapBounds(north=23.230, south=23.215, east=72.645, west=72.625),
        place_name="Sachivalay, Gandhinagar, Gujarat, India",
        estimated_junctions=15,
        estimated_roads=25
    ),
    "demo_area": PredefinedArea(
        key="demo_area",
        name="Demo Area",
        description="Small area for demo/testing",
        bounds=MapBounds(north=23.180, south=23.165, east=72.688, west=72.675),
        place_name=None,  # Use bounds only
        estimated_junctions=10,
        estimated_roads=15
    )
}


class MapLoaderService:
    """
    Load OpenStreetMap data for real city geography
    
    Usage:
        loader = MapLoaderService(canvas_width=1200, canvas_height=800)
        
        # Load by predefined area
        result = loader.load_predefined_area("gift_city")
        
        # Load by bounding box
        result = loader.load_by_bbox(north=23.2, south=23.1, east=72.7, west=72.6)
        
        # Load by place name
        result = loader.load_by_place_name("GIFT City, Gandhinagar, India")
    """
    
    def __init__(
        self,
        canvas_width: int = 1200,
        canvas_height: int = 800,
        cache_dir: Optional[str] = None
    ):
        """
        Initialize the Map Loader Service
        
        Args:
            canvas_width: Width of the visualization canvas
            canvas_height: Height of the visualization canvas
            cache_dir: Directory to cache map data
        """
        self.canvas_width = canvas_width
        self.canvas_height = canvas_height
        
        # Setup cache directory
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            self.cache_dir = Path(__file__).parent.parent.parent / "data" / "map_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Current loaded map state
        self.graph: Optional[Any] = None
        self.current_bounds: Optional[MapBounds] = None
        self.converter: Optional[CoordinateConverter] = None
        
        # Extracted entities
        self.junctions: List[RealJunction] = []
        self.roads: List[RealRoad] = []
        
        # Configure OSMnx if available
        if OSMNX_AVAILABLE:
            ox.settings.use_cache = True
            ox.settings.cache_folder = str(self.cache_dir)
    
    def get_predefined_areas(self) -> Dict[str, PredefinedArea]:
        """Get all predefined map areas"""
        return PREDEFINED_AREAS
    
    def load_predefined_area(self, area_key: str) -> OSMLoadResult:
        """
        Load a predefined map area
        
        Args:
            area_key: Key of the predefined area (e.g., "gift_city")
            
        Returns:
            OSMLoadResult with loaded map data
        """
        if area_key not in PREDEFINED_AREAS:
            raise ValueError(f"Unknown predefined area: {area_key}. "
                           f"Available: {list(PREDEFINED_AREAS.keys())}")
        
        area = PREDEFINED_AREAS[area_key]
        
        # Check cache first
        cached = self._load_from_cache(area_key)
        if cached:
            return cached
        
        # Load from OSM
        if area.place_name:
            return self.load_by_place_name(
                area.place_name,
                area_id=area_key,
                area_name=area.name
            )
        else:
            return self.load_by_bbox(
                north=area.bounds.north,
                south=area.bounds.south,
                east=area.bounds.east,
                west=area.bounds.west,
                area_id=area_key,
                area_name=area.name
            )
    
    def load_by_place_name(
        self,
        place_name: str,
        area_id: Optional[str] = None,
        area_name: Optional[str] = None
    ) -> OSMLoadResult:
        """
        Load map by place name (geocoding)
        
        Args:
            place_name: Place name to search (e.g., "GIFT City, Gandhinagar")
            area_id: Optional ID for the area
            area_name: Optional display name for the area
            
        Returns:
            OSMLoadResult with loaded map data
        """
        start_time = time.time()
        
        if not OSMNX_AVAILABLE:
            return self._generate_mock_data(
                area_id=area_id or "mock_place",
                area_name=area_name or place_name,
                load_time=time.time() - start_time
            )
        
        print(f"[MapLoader] Loading map for: {place_name}")
        
        try:
            # Download street network from OSM
            self.graph = ox.graph_from_place(
                place_name,
                network_type='drive',
                simplify=True
            )
            
            # Extract bounds from graph
            nodes_gdf, edges_gdf = ox.graph_to_gdfs(self.graph)
            self.current_bounds = MapBounds(
                north=nodes_gdf.geometry.y.max(),
                south=nodes_gdf.geometry.y.min(),
                east=nodes_gdf.geometry.x.max(),
                west=nodes_gdf.geometry.x.min()
            )
            
            # Create coordinate converter
            self.converter = CoordinateConverter(
                canvas_width=self.canvas_width,
                canvas_height=self.canvas_height,
                map_bounds=self.current_bounds
            )
            
            # Extract junctions and roads
            self._extract_junctions()
            self._extract_roads()
            
            load_time = time.time() - start_time
            print(f"[MapLoader] Loaded {len(self.junctions)} junctions, "
                  f"{len(self.roads)} roads in {load_time:.2f}s")
            
            result = OSMLoadResult(
                map_area=MapArea(
                    id=area_id or f"place_{hash(place_name)}",
                    name=area_name or place_name,
                    type="CUSTOM",
                    bounds=self.current_bounds,
                    junction_count=len(self.junctions),
                    road_count=len(self.roads),
                    cached=False
                ),
                junctions=self.junctions,
                roads=self.roads,
                bounds=self.current_bounds,
                load_time=load_time
            )
            
            # Cache the result
            if area_id:
                self._save_to_cache(area_id, result)
            
            return result
            
        except Exception as e:
            print(f"[MapLoader] Error loading place: {e}")
            return self._generate_mock_data(
                area_id=area_id or "error_fallback",
                area_name=area_name or place_name,
                load_time=time.time() - start_time
            )
    
    def load_by_bbox(
        self,
        north: float,
        south: float,
        east: float,
        west: float,
        area_id: Optional[str] = None,
        area_name: Optional[str] = None
    ) -> OSMLoadResult:
        """
        Load map by bounding box coordinates
        
        Args:
            north, south, east, west: Bounding box coordinates
            area_id: Optional ID for the area
            area_name: Optional display name
            
        Returns:
            OSMLoadResult with loaded map data
        """
        start_time = time.time()
        
        if not OSMNX_AVAILABLE:
            return self._generate_mock_data(
                area_id=area_id or "mock_bbox",
                area_name=area_name or f"Area ({north:.3f}, {west:.3f})",
                bounds=MapBounds(north=north, south=south, east=east, west=west),
                load_time=time.time() - start_time
            )
        
        print(f"[MapLoader] Loading map for bbox: N={north}, S={south}, E={east}, W={west}")
        
        try:
            # Download street network from OSM
            self.graph = ox.graph_from_bbox(
                north=north,
                south=south,
                east=east,
                west=west,
                network_type='drive',
                simplify=True
            )
            
            self.current_bounds = MapBounds(north=north, south=south, east=east, west=west)
            
            # Create coordinate converter
            self.converter = CoordinateConverter(
                canvas_width=self.canvas_width,
                canvas_height=self.canvas_height,
                map_bounds=self.current_bounds
            )
            
            # Extract junctions and roads
            self._extract_junctions()
            self._extract_roads()
            
            load_time = time.time() - start_time
            print(f"[MapLoader] Loaded {len(self.junctions)} junctions, "
                  f"{len(self.roads)} roads in {load_time:.2f}s")
            
            result = OSMLoadResult(
                map_area=MapArea(
                    id=area_id or f"bbox_{hash((north, south, east, west))}",
                    name=area_name or f"Custom Area",
                    type="CUSTOM",
                    bounds=self.current_bounds,
                    junction_count=len(self.junctions),
                    road_count=len(self.roads),
                    cached=False
                ),
                junctions=self.junctions,
                roads=self.roads,
                bounds=self.current_bounds,
                load_time=load_time
            )
            
            if area_id:
                self._save_to_cache(area_id, result)
            
            return result
            
        except Exception as e:
            print(f"[MapLoader] Error loading bbox: {e}")
            return self._generate_mock_data(
                area_id=area_id or "error_fallback",
                area_name=area_name or "Custom Area",
                bounds=MapBounds(north=north, south=south, east=east, west=west),
                load_time=time.time() - start_time
            )
    
    def load_by_radius(
        self,
        center_lat: float,
        center_lon: float,
        radius_meters: int = 1000,
        area_id: Optional[str] = None,
        area_name: Optional[str] = None
    ) -> OSMLoadResult:
        """
        Load map by center point and radius
        
        Args:
            center_lat: Center latitude
            center_lon: Center longitude
            radius_meters: Radius in meters
            area_id: Optional ID
            area_name: Optional display name
            
        Returns:
            OSMLoadResult with loaded map data
        """
        start_time = time.time()
        
        if not OSMNX_AVAILABLE:
            return self._generate_mock_data(
                area_id=area_id or "mock_radius",
                area_name=area_name or f"Area around ({center_lat:.4f}, {center_lon:.4f})",
                load_time=time.time() - start_time
            )
        
        print(f"[MapLoader] Loading map for point ({center_lat}, {center_lon}), "
              f"radius={radius_meters}m")
        
        try:
            # Download street network from OSM
            self.graph = ox.graph_from_point(
                (center_lat, center_lon),
                dist=radius_meters,
                network_type='drive',
                simplify=True
            )
            
            # Extract bounds from graph
            nodes_gdf, edges_gdf = ox.graph_to_gdfs(self.graph)
            self.current_bounds = MapBounds(
                north=nodes_gdf.geometry.y.max(),
                south=nodes_gdf.geometry.y.min(),
                east=nodes_gdf.geometry.x.max(),
                west=nodes_gdf.geometry.x.min()
            )
            
            self.converter = CoordinateConverter(
                canvas_width=self.canvas_width,
                canvas_height=self.canvas_height,
                map_bounds=self.current_bounds
            )
            
            self._extract_junctions()
            self._extract_roads()
            
            load_time = time.time() - start_time
            
            result = OSMLoadResult(
                map_area=MapArea(
                    id=area_id or f"radius_{hash((center_lat, center_lon, radius_meters))}",
                    name=area_name or f"Area ({center_lat:.4f}, {center_lon:.4f})",
                    type="CUSTOM",
                    bounds=self.current_bounds,
                    junction_count=len(self.junctions),
                    road_count=len(self.roads),
                    cached=False
                ),
                junctions=self.junctions,
                roads=self.roads,
                bounds=self.current_bounds,
                load_time=load_time
            )
            
            return result
            
        except Exception as e:
            print(f"[MapLoader] Error loading radius: {e}")
            return self._generate_mock_data(
                area_id=area_id or "error_fallback",
                area_name=area_name or "Custom Area",
                load_time=time.time() - start_time
            )
    
    def _extract_junctions(self):
        """Extract junction data from the loaded graph"""
        self.junctions = []
        
        if not self.graph or not self.converter:
            return
        
        # Create node to junction ID mapping
        self._node_to_junction: Dict[int, str] = {}
        
        idx = 0
        for node_id, node_data in self.graph.nodes(data=True):
            lat = node_data.get('y', 0)
            lon = node_data.get('x', 0)
            
            # Convert to canvas coordinates
            canvas = self.converter.gps_to_canvas(lat, lon)
            
            junction_id = f"J-{idx}"
            self._node_to_junction[node_id] = junction_id
            
            # Get street count (number of edges connected)
            street_count = self.graph.degree(node_id)
            
            # Create junction
            junction = RealJunction(
                id=junction_id,
                osm_id=int(node_id),
                lat=lat,
                lon=lon,
                x=canvas.x,
                y=canvas.y,
                street_count=street_count,
                signals=create_default_signals('north'),  # Default signals
                last_signal_change=time.time()
            )
            
            self.junctions.append(junction)
            idx += 1
    
    def _extract_roads(self):
        """Extract road data from the loaded graph"""
        self.roads = []
        
        if not self.graph or not self.converter or not hasattr(self, '_node_to_junction'):
            return
        
        idx = 0
        for u, v, edge_data in self.graph.edges(data=True):
            # Get junction IDs
            start_junction = self._node_to_junction.get(u)
            end_junction = self._node_to_junction.get(v)
            
            if not start_junction or not end_junction:
                continue
            
            # Get node coordinates
            u_node = self.graph.nodes[u]
            v_node = self.graph.nodes[v]
            
            start_lat = u_node.get('y', 0)
            start_lon = u_node.get('x', 0)
            end_lat = v_node.get('y', 0)
            end_lon = v_node.get('x', 0)
            
            # Convert to canvas coordinates
            start_canvas = self.converter.gps_to_canvas(start_lat, start_lon)
            end_canvas = self.converter.gps_to_canvas(end_lat, end_lon)
            
            # Extract road metadata from OSM
            road_name = edge_data.get('name', 'Unnamed Road')
            if isinstance(road_name, list):
                road_name = road_name[0] if road_name else 'Unnamed Road'
            
            length = edge_data.get('length', 100)
            
            # Parse lanes (could be string or int)
            lanes = edge_data.get('lanes', 2)
            if isinstance(lanes, str):
                try:
                    lanes = int(lanes.split(';')[0])
                except:
                    lanes = 2
            elif isinstance(lanes, list):
                lanes = int(lanes[0]) if lanes else 2
            
            # Parse max speed
            max_speed = edge_data.get('maxspeed', 50)
            if isinstance(max_speed, str):
                try:
                    max_speed = float(max_speed.replace(' km/h', '').replace(' mph', ''))
                except:
                    max_speed = 50
            elif isinstance(max_speed, list):
                max_speed = 50
            
            road_type = edge_data.get('highway', 'road')
            if isinstance(road_type, list):
                road_type = road_type[0] if road_type else 'road'
            
            oneway = edge_data.get('oneway', False)
            if isinstance(oneway, str):
                oneway = oneway.lower() in ('yes', 'true', '1')
            
            # Create road
            road_id = f"R-{idx}"
            road = RealRoad(
                id=road_id,
                osm_id=str(edge_data.get('osmid', idx)),
                start_junction_id=start_junction,
                end_junction_id=end_junction,
                start_lat=start_lat,
                start_lon=start_lon,
                end_lat=end_lat,
                end_lon=end_lon,
                start_x=start_canvas.x,
                start_y=start_canvas.y,
                end_x=end_canvas.x,
                end_y=end_canvas.y,
                name=road_name,
                length=length,
                max_speed=max_speed,
                lanes=lanes,
                road_type=road_type,
                oneway=oneway,
                last_update=time.time()
            )
            
            self.roads.append(road)
            
            # Add road to junction's connected_roads
            for junction in self.junctions:
                if junction.id == start_junction:
                    junction.connected_roads.append(road_id)
                elif junction.id == end_junction:
                    junction.connected_roads.append(road_id)
            
            idx += 1
    
    def _save_to_cache(self, area_id: str, result: OSMLoadResult):
        """Save map data to cache"""
        cache_file = self.cache_dir / f"{area_id}.json"
        
        try:
            cache_data = {
                "area_id": area_id,
                "cached_at": time.time(),
                "map_area": result.map_area.model_dump(),
                "bounds": result.bounds.model_dump(),
                "junctions": [j.model_dump() for j in result.junctions],
                "roads": [r.model_dump() for r in result.roads],
                "load_time": result.load_time
            }
            
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f)
            
            print(f"[MapLoader] Cached map data to {cache_file}")
            
        except Exception as e:
            print(f"[MapLoader] Error caching map: {e}")
    
    def _load_from_cache(self, area_id: str) -> Optional[OSMLoadResult]:
        """Load map data from cache if available"""
        cache_file = self.cache_dir / f"{area_id}.json"
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
            
            # Check cache age (24 hours)
            if time.time() - cache_data.get('cached_at', 0) > 86400:
                print(f"[MapLoader] Cache expired for {area_id}")
                return None
            
            # Reconstruct result
            junctions = [RealJunction(**j) for j in cache_data.get('junctions', [])]
            roads = [RealRoad(**r) for r in cache_data.get('roads', [])]
            bounds = MapBounds(**cache_data.get('bounds', {}))
            
            # Update internal state
            self.junctions = junctions
            self.roads = roads
            self.current_bounds = bounds
            self.converter = CoordinateConverter(
                canvas_width=self.canvas_width,
                canvas_height=self.canvas_height,
                map_bounds=bounds
            )
            
            map_area = MapArea(**cache_data.get('map_area', {}))
            map_area.cached = True
            
            print(f"[MapLoader] Loaded from cache: {len(junctions)} junctions, "
                  f"{len(roads)} roads")
            
            return OSMLoadResult(
                map_area=map_area,
                junctions=junctions,
                roads=roads,
                bounds=bounds,
                load_time=cache_data.get('load_time', 0),
                from_cache=True
            )
            
        except Exception as e:
            print(f"[MapLoader] Error loading from cache: {e}")
            return None
    
    def _generate_mock_data(
        self,
        area_id: str,
        area_name: str,
        bounds: Optional[MapBounds] = None,
        load_time: float = 0.1
    ) -> OSMLoadResult:
        """
        Generate mock map data when OSMnx is not available or fails
        
        Creates a simple 3x3 grid of junctions and connecting roads.
        """
        if bounds is None:
            bounds = GANDHINAGAR_BOUNDS
        
        self.current_bounds = bounds
        self.converter = CoordinateConverter(
            canvas_width=self.canvas_width,
            canvas_height=self.canvas_height,
            map_bounds=bounds
        )
        
        # Create 3x3 grid of junctions
        self.junctions = []
        grid_size = 3
        
        lat_step = (bounds.north - bounds.south) / (grid_size + 1)
        lon_step = (bounds.east - bounds.west) / (grid_size + 1)
        
        junction_grid = {}  # (row, col) -> junction_id
        
        for row in range(grid_size):
            for col in range(grid_size):
                idx = row * grid_size + col
                junction_id = f"J-{idx}"
                
                lat = bounds.south + (row + 1) * lat_step
                lon = bounds.west + (col + 1) * lon_step
                
                canvas = self.converter.gps_to_canvas(lat, lon)
                
                # Determine which direction gets green light
                green_dir = ['north', 'east', 'south', 'west'][idx % 4]
                
                junction = RealJunction(
                    id=junction_id,
                    osm_id=1000 + idx,
                    lat=lat,
                    lon=lon,
                    x=canvas.x,
                    y=canvas.y,
                    name=f"Junction {idx + 1}",
                    street_count=4,
                    signals=create_default_signals(green_dir),
                    last_signal_change=time.time()
                )
                
                self.junctions.append(junction)
                junction_grid[(row, col)] = junction_id
        
        # Create connecting roads
        self.roads = []
        road_idx = 0
        
        # Horizontal roads
        for row in range(grid_size):
            for col in range(grid_size - 1):
                start_j = junction_grid[(row, col)]
                end_j = junction_grid[(row, col + 1)]
                
                start_junction = next(j for j in self.junctions if j.id == start_j)
                end_junction = next(j for j in self.junctions if j.id == end_j)
                
                road = RealRoad(
                    id=f"R-{road_idx}",
                    osm_id=f"mock_{road_idx}",
                    start_junction_id=start_j,
                    end_junction_id=end_j,
                    start_lat=start_junction.lat,
                    start_lon=start_junction.lon,
                    end_lat=end_junction.lat,
                    end_lon=end_junction.lon,
                    start_x=start_junction.x,
                    start_y=start_junction.y,
                    end_x=end_junction.x,
                    end_y=end_junction.y,
                    name=f"Road {road_idx + 1}",
                    length=100 * lon_step * 111000,  # Approximate meters
                    max_speed=50,
                    lanes=2
                )
                
                self.roads.append(road)
                start_junction.connected_roads.append(road.id)
                end_junction.connected_roads.append(road.id)
                road_idx += 1
        
        # Vertical roads
        for row in range(grid_size - 1):
            for col in range(grid_size):
                start_j = junction_grid[(row, col)]
                end_j = junction_grid[(row + 1, col)]
                
                start_junction = next(j for j in self.junctions if j.id == start_j)
                end_junction = next(j for j in self.junctions if j.id == end_j)
                
                road = RealRoad(
                    id=f"R-{road_idx}",
                    osm_id=f"mock_{road_idx}",
                    start_junction_id=start_j,
                    end_junction_id=end_j,
                    start_lat=start_junction.lat,
                    start_lon=start_junction.lon,
                    end_lat=end_junction.lat,
                    end_lon=end_junction.lon,
                    start_x=start_junction.x,
                    start_y=start_junction.y,
                    end_x=end_junction.x,
                    end_y=end_junction.y,
                    name=f"Road {road_idx + 1}",
                    length=100 * lat_step * 111000,
                    max_speed=50,
                    lanes=2
                )
                
                self.roads.append(road)
                start_junction.connected_roads.append(road.id)
                end_junction.connected_roads.append(road.id)
                road_idx += 1
        
        return OSMLoadResult(
            map_area=MapArea(
                id=area_id,
                name=area_name,
                type="CUSTOM",
                bounds=bounds,
                junction_count=len(self.junctions),
                road_count=len(self.roads),
                cached=False,
                metadata=MapAreaMetadata(description="Mock data - OSMnx not available")
            ),
            junctions=self.junctions,
            roads=self.roads,
            bounds=bounds,
            load_time=load_time,
            from_cache=False
        )


# Global service instance
_map_loader_service: Optional[MapLoaderService] = None


def get_map_loader_service() -> MapLoaderService:
    """Get the global MapLoaderService instance"""
    global _map_loader_service
    if _map_loader_service is None:
        _map_loader_service = MapLoaderService()
    return _map_loader_service

