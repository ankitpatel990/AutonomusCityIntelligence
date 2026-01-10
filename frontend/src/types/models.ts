/**
 * Core Data Models for Traffic Intelligence System
 * 
 * These TypeScript interfaces mirror the Pydantic models on the backend
 * to ensure type safety across the full stack.
 */

// ============================================
// Position & Geometry
// ============================================

export interface Position {
  x: number;
  y: number;
}

export interface GPSCoordinate {
  lat: number;
  lon: number;
}

export interface CanvasCoordinate {
  x: number;
  y: number;
}

export interface MapBounds {
  north: number;
  south: number;
  east: number;
  west: number;
}

// ============================================
// Vehicle Types
// ============================================

export type VehicleType = 'car' | 'bike' | 'ambulance';

export interface Vehicle {
  id: string;
  numberPlate: string;
  type: VehicleType;
  
  // Position & Movement
  position: Position;
  speed: number;
  acceleration: number;
  heading: number;
  
  // Route
  currentRoad: string | null;
  currentJunction: string | null;
  destination: string;
  path: string[];
  pathIndex: number;
  
  // State
  isEmergency: boolean;
  isViolating: boolean;
  waitingTime: number;
  
  // Timestamps
  spawnTime: number;
  lastUpdate: number;
  
  // GPS (for real map mode)
  lat?: number;
  lon?: number;
  source?: 'SIMULATION' | 'LIVE_TRAFFIC_API';
}

// ============================================
// Signal & Junction Types
// ============================================

export type SignalColor = 'RED' | 'YELLOW' | 'GREEN';

export interface SignalState {
  current: SignalColor;
  duration: number;
  lastChange: number;
  timeSinceGreen: number;
}

export interface JunctionSignals {
  north: SignalState;
  east: SignalState;
  south: SignalState;
  west: SignalState;
}

export interface JunctionMetrics {
  vehicleCount: number;
  avgWaitTime: number;
  density: number;
}

export interface Junction {
  id: string;
  position: Position;
  signals: JunctionSignals;
  connectedRoads: {
    north: string | null;
    east: string | null;
    south: string | null;
    west: string | null;
  };
  metrics: JunctionMetrics;
  lastSignalChange: number;
}

// ============================================
// Road Types
// ============================================

export type DensityLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'JAM';

export interface RoadTraffic {
  currentVehicles: string[];
  capacity: number;
  density: DensityLevel;
  densityScore: number;
  speedLimit: number;
}

export interface RoadSegment {
  id: string;
  startJunction: string;
  endJunction: string;
  geometry: {
    startPos: Position;
    endPos: Position;
    length: number;
    lanes: number;
  };
  traffic: RoadTraffic;
  lastUpdate: number;
}

// ============================================
// Live Traffic Types (NEW v2.0)
// ============================================

export interface TrafficIncident {
  type: string;
  description: string;
  severity: string;
}

export interface LiveTrafficData {
  roadId: string;
  currentSpeed: number;
  freeFlowSpeed: number;
  congestionLevel: DensityLevel;
  confidence: number;
  timestamp: string;
  expiresAt: number | null;
  source: 'API' | 'SIMULATION' | 'MANUAL' | 'ADJUSTED';
  provider?: 'tomtom' | 'google' | 'here';
  incidents?: TrafficIncident[];
  roadClosure?: boolean;
}

// ============================================
// Real Map Types (NEW v2.0)
// ============================================

export interface RealJunction {
  id: string;
  osmId: number;
  lat: number;
  lon: number;
  x: number;
  y: number;
  name?: string;
  landmark?: string;
  address?: string;
  signals: JunctionSignals;
  connectedRoads: string[];
  metrics: JunctionMetrics;
  lastSignalChange: number;
}

export interface RealRoad {
  id: string;
  osmId: string;
  startJunctionId: string;
  endJunctionId: string;
  startLat: number;
  startLon: number;
  endLat: number;
  endLon: number;
  startX: number;
  startY: number;
  endX: number;
  endY: number;
  name: string;
  length: number;
  maxSpeed: number;
  lanes: number;
  roadType?: string;
  traffic: RoadTraffic;
  liveTraffic?: LiveTrafficData;
  lastUpdate: number;
}

// ============================================
// Traffic Control Types (NEW v2.0)
// ============================================

export type TrafficDataMode = 'LIVE_API' | 'MANUAL' | 'HYBRID' | 'SIMULATION';

export interface TrafficDataSource {
  mode: TrafficDataMode;
  apiProvider?: 'tomtom' | 'google' | 'here';
  apiKeyConfigured: boolean;
  lastApiUpdate?: string;
  activeOverrides: number;
  globalMultiplier: number;
  cacheHitRate?: number;
}

export interface ManualTrafficOverride {
  roadId: string;
  congestionLevel: DensityLevel;
  duration?: number;
  expiresAt?: number;
  reason?: string;
}

// ============================================
// Map Area Types (NEW v2.0)
// ============================================

export interface MapAreaMetadata {
  areaKm2?: number;
  population?: number;
  description?: string;
}

export interface MapArea {
  id: string;
  name: string;
  type: 'PREDEFINED' | 'CUSTOM';
  bounds: MapBounds;
  junctionCount: number;
  roadCount: number;
  loadedAt?: string;
  cached: boolean;
  metadata?: MapAreaMetadata;
}

// ============================================
// System State Types
// ============================================

export type SystemMode = 'NORMAL' | 'EMERGENCY' | 'INCIDENT' | 'FAIL_SAFE';
export type AgentStatus = 'RUNNING' | 'PAUSED' | 'STOPPED';
export type AgentStrategy = 'RL' | 'RULE_BASED';

export interface SimulationState {
  time: number;
  timeMultiplier: number;
  isPaused: boolean;
  startTime: number;
}

export interface AgentState {
  status: AgentStatus;
  strategy: AgentStrategy;
  loopCount: number;
  lastDecisionTime: number;
  avgDecisionLatency: number;
}

export interface PerformanceMetrics {
  fps: number;
  vehicleCount: number;
  avgDensity: number;
  congestionPoints: number;
  throughput: number;
}

export interface SystemState {
  mode: SystemMode;
  simulation: SimulationState;
  agent: AgentState;
  performance: PerformanceMetrics;
}

// ============================================
// Violation & Challan Types
// ============================================

export type ViolationType = 'RED_LIGHT' | 'SPEEDING' | 'WRONG_DIRECTION' | 'NO_STOPPING';
export type ChallanStatus = 'ISSUED' | 'PAID' | 'PENDING' | 'CANCELLED';

export interface Violation {
  id: string;
  vehicleId: string;
  numberPlate: string;
  violationType: ViolationType;
  severity: 'LOW' | 'MEDIUM' | 'HIGH';
  location: string;
  timestamp: number;
  processed: boolean;
  challanId?: string;
}

export interface Challan {
  challanId: string;
  violationId: string;
  numberPlate: string;
  ownerName: string;
  violationType: ViolationType;
  violationDescription?: string;
  fineAmount: number;
  location: string;
  timestamp: number;
  status: ChallanStatus;
  paymentTimestamp?: number;
  transactionId?: string;
}

// ============================================
// Emergency Types
// ============================================

export interface EmergencyVehicle {
  vehicleId: string;
  type: 'AMBULANCE' | 'FIRE_TRUCK' | 'POLICE';
  origin: string;
  destination: string;
  corridor: string[];
  status: 'ACTIVE' | 'COMPLETED' | 'CANCELLED';
  activatedAt: number;
  eta?: number;
}

export interface EmergencyCorridor {
  vehicleId: string;
  path: string[];
  affectedJunctions: string[];
  activeSignalOverrides: Record<string, SignalColor>;
  estimatedClearTime: number;
}

