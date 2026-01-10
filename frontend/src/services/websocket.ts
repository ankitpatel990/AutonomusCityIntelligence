/**
 * WebSocket Service
 * 
 * Handles real-time communication with the backend via Socket.IO.
 * Implements all events specified in FRD-01 Section 2.4.
 */

import { io, Socket } from 'socket.io-client';

const WS_URL = import.meta.env.VITE_WS_URL || 'http://localhost:8001';

// ============================================
// Event Types
// ============================================

export type ConnectionStatus = 'connected' | 'disconnected' | 'connecting' | 'error';

export interface ConnectionSuccessData {
  message: string;
  timestamp: number;
  serverVersion: string;
}

export interface VehicleUpdateData {
  vehicleId: string;
  position: { x: number; y: number };
  speed: number;
  heading: number;
  timestamp: number;
  lat?: number;
  lon?: number;
}

export interface VehicleBatchUpdate {
  vehicles: VehicleUpdateData[];
  count: number;
}

export interface VehicleSpawnedData {
  vehicleId: string;
  numberPlate: string;
  type: 'car' | 'bike' | 'ambulance';
  position: { x: number; y: number };
  destination: string;
  timestamp: number;
}

export interface VehicleRemovedData {
  vehicleId: string;
  reason: 'reached_destination' | 'despawned' | 'collision';
  timestamp: number;
}

export interface SignalChangeData {
  junctionId: string;
  direction: 'north' | 'east' | 'south' | 'west';
  newState: 'RED' | 'YELLOW' | 'GREEN';
  previousState?: string;
  duration: number;
  timestamp: number;
}

export interface DensityUpdateData {
  roadId: string;
  densityScore: number;
  classification: 'LOW' | 'MEDIUM' | 'HIGH';
  vehicleCount: number;
  timestamp: number;
  color?: string;
}

export interface DensityBatchUpdate {
  roads: DensityUpdateData[];
  count: number;
  timestamp: number;
}

export interface PredictionUpdateData {
  predictions: any[];
  generatedAt: number;
  nextUpdate: number;
  modelVersion: string;
}

export interface AgentDecisionData {
  timestamp: number;
  decisions: { junctionId: string; action: string; reason?: string }[];
  latency: number;
  strategy: 'RL' | 'RULE_BASED';
  mode: string;
}

export interface AgentStatusUpdateData {
  status: 'RUNNING' | 'PAUSED' | 'STOPPED';
  strategy: 'RL' | 'RULE_BASED';
  uptime: number;
  decisions: number;
  avgLatency: number;
}

export interface EmergencyActivatedData {
  vehicleId: string;
  corridorPath: string[];
  estimatedTime: number;
  destination: string;
  activatedAt: number;
}

export interface EmergencyDeactivatedData {
  vehicleId: string;
  completionTime: number;
  reason: 'reached_destination' | 'cancelled' | 'timeout';
}

export interface EmergencyProgressData {
  vehicleId: string;
  currentJunction: string;
  progress: number;
  estimatedArrival: number;
}

export interface FailsafeTriggeredData {
  reason: string;
  timestamp: number;
  affectedJunctions: string[];
  previousMode: string;
  newMode: string;
  signalState: string;
}

export interface ViolationDetectedData {
  id: string;
  vehicleId: string;
  numberPlate: string;
  violationType: 'RED_LIGHT' | 'SPEEDING' | 'WRONG_LANE';
  severity: 'LOW' | 'MEDIUM' | 'HIGH';
  location: string;
  timestamp: number;
  evidence: Record<string, any>;
}

export interface ChallanIssuedData {
  challanId: string;
  numberPlate: string;
  ownerName: string;
  violationType: string;
  fineAmount: number;
  location: string;
  timestamp: number;
}

export interface ChallanPaidData {
  challanId: string;
  transactionId: string;
  amount: number;
  newBalance: number;
  timestamp: number;
}

export interface TrafficControlActiveData {
  controlId: string;
  junctionId: string;
  direction: string;
  action: string;
  duration?: number;
  expiresAt?: number;
  createdAt: number;
}

export interface TrafficControlRemovedData {
  controlId: string;
  reason: 'expired' | 'manual' | 'emergency';
}

export interface LiveTrafficUpdatedData {
  roads: Record<string, any>;
  timestamp: string;
  provider: string;
  updatedCount: number;
}

export interface LiveTrafficErrorData {
  error: string;
  provider: string;
  timestamp: string;
  fallbackMode: string;
}

export interface MapLoadedData {
  mapArea: any;
  junctionCount: number;
  roadCount: number;
  loadTime: number;
}

export interface DataModeChangedData {
  oldMode: string;
  newMode: string;
  timestamp: string;
}

export interface SystemStateUpdateData {
  mode: string;
  simulationTime: number;
  isPaused: boolean;
  vehicleCount: number;
  avgDensity: number;
  fps: number;
  timestamp: number;
}

// ============================================
// WebSocket Service Class
// ============================================

export class WebSocketService {
  private socket: Socket;
  private listeners: Map<string, Set<Function>> = new Map();
  private _status: ConnectionStatus = 'disconnected';
  private _reconnectAttempts = 0;
  private _maxReconnectAttempts = 5;

  constructor() {
    this.socket = io(WS_URL, {
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      reconnectionAttempts: this._maxReconnectAttempts,
      timeout: 10000,
      autoConnect: true,
    });

    this._setupBaseListeners();
  }

  private _setupBaseListeners() {
    this.socket.on('connect', () => {
      console.log('[WS] Connected to server');
      this._status = 'connected';
      this._reconnectAttempts = 0;
    });

    this.socket.on('disconnect', (reason) => {
      console.log(`[WS] Disconnected: ${reason}`);
      this._status = 'disconnected';
    });

    this.socket.on('connect_error', (error) => {
      console.error('[WS] Connection error:', error.message);
      this._status = 'error';
      this._reconnectAttempts++;
    });

    this.socket.on('reconnect_attempt', (attempt) => {
      console.log(`[WS] Reconnect attempt ${attempt}`);
      this._status = 'connecting';
    });

    this.socket.on('reconnect', () => {
      console.log('[WS] Reconnected successfully');
      this._status = 'connected';
    });

    this.socket.on('connection:success', (data: ConnectionSuccessData) => {
      console.log(`[WS] ${data.message} (v${data.serverVersion})`);
    });
  }

  // ============================================
  // Public API
  // ============================================

  get status(): ConnectionStatus {
    return this._status;
  }

  get isConnected(): boolean {
    return this._status === 'connected';
  }

  get socketId(): string | undefined {
    return this.socket.id;
  }

  /**
   * Subscribe to an event
   */
  on<T = any>(event: string, callback: (data: T) => void): () => void {
    this.socket.on(event, callback);
    
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event)?.add(callback);

    // Return unsubscribe function
    return () => this.off(event, callback);
  }

  /**
   * Unsubscribe from an event
   */
  off(event: string, callback: Function): void {
    this.socket.off(event, callback as any);
    this.listeners.get(event)?.delete(callback);
  }

  /**
   * Emit an event to server
   */
  emit(event: string, data: any): void {
    if (this._status !== 'connected') {
      console.warn(`[WS] Cannot emit '${event}': not connected`);
      return;
    }
    this.socket.emit(event, data);
  }

  /**
   * Emit with acknowledgment callback
   */
  emitWithAck(event: string, data: any): Promise<any> {
    return new Promise((resolve, reject) => {
      if (this._status !== 'connected') {
        reject(new Error('Not connected'));
        return;
      }
      
      this.socket.emit(event, data, (response: any) => {
        if (response?.error) {
          reject(new Error(response.error));
        } else {
          resolve(response);
        }
      });
    });
  }

  /**
   * Manually connect
   */
  connect(): void {
    if (!this.socket.connected) {
      this.socket.connect();
    }
  }

  /**
   * Disconnect from server
   */
  disconnect(): void {
    this.socket.disconnect();
    this._status = 'disconnected';
  }

  /**
   * Remove all listeners for an event
   */
  removeAllListeners(event?: string): void {
    if (event) {
      this.socket.off(event);
      this.listeners.delete(event);
    } else {
      this.socket.removeAllListeners();
      this.listeners.clear();
      this._setupBaseListeners();
    }
  }

  // ============================================
  // Typed Event Helpers
  // ============================================

  // Vehicle events
  onVehicleUpdate(callback: (data: VehicleUpdateData) => void) {
    return this.on('vehicle:update', callback);
  }

  onVehicleBatchUpdate(callback: (data: VehicleBatchUpdate) => void) {
    return this.on('vehicles:batch_update', callback);
  }

  onVehicleSpawned(callback: (data: VehicleSpawnedData) => void) {
    return this.on('vehicle:spawned', callback);
  }

  onVehicleRemoved(callback: (data: VehicleRemovedData) => void) {
    return this.on('vehicle:removed', callback);
  }

  // Signal events
  onSignalChange(callback: (data: SignalChangeData) => void) {
    return this.on('signal:change', callback);
  }

  // Density events
  onDensityUpdate(callback: (data: DensityUpdateData) => void) {
    return this.on('density:update', callback);
  }

  onDensityBatchUpdate(callback: (data: DensityBatchUpdate) => void) {
    return this.on('density:batch_update', callback);
  }

  // Prediction events
  onPredictionUpdate(callback: (data: PredictionUpdateData) => void) {
    return this.on('prediction:update', callback);
  }

  // Agent events
  onAgentDecision(callback: (data: AgentDecisionData) => void) {
    return this.on('agent:decision', callback);
  }

  onAgentStatusUpdate(callback: (data: AgentStatusUpdateData) => void) {
    return this.on('agent:status_update', callback);
  }

  // Emergency events
  onEmergencyActivated(callback: (data: EmergencyActivatedData) => void) {
    return this.on('emergency:activated', callback);
  }

  onEmergencyDeactivated(callback: (data: EmergencyDeactivatedData) => void) {
    return this.on('emergency:deactivated', callback);
  }

  onEmergencyProgress(callback: (data: EmergencyProgressData) => void) {
    return this.on('emergency:progress', callback);
  }

  // Safety events
  onFailsafeTriggered(callback: (data: FailsafeTriggeredData) => void) {
    return this.on('failsafe:triggered', callback);
  }

  onFailsafeCleared(callback: (data: any) => void) {
    return this.on('failsafe:cleared', callback);
  }

  // Violation & Challan events
  onViolationDetected(callback: (data: ViolationDetectedData) => void) {
    return this.on('violation:detected', callback);
  }

  onChallanIssued(callback: (data: ChallanIssuedData) => void) {
    return this.on('challan:issued', callback);
  }

  onChallanPaid(callback: (data: ChallanPaidData) => void) {
    return this.on('challan:paid', callback);
  }

  // Traffic control events
  onTrafficControlActive(callback: (data: TrafficControlActiveData) => void) {
    return this.on('traffic:control:active', callback);
  }

  onTrafficControlRemoved(callback: (data: TrafficControlRemovedData) => void) {
    return this.on('traffic:control:removed', callback);
  }

  // Live traffic events
  onLiveTrafficUpdated(callback: (data: LiveTrafficUpdatedData) => void) {
    return this.on('live:traffic:updated', callback);
  }

  onLiveTrafficError(callback: (data: LiveTrafficErrorData) => void) {
    return this.on('live:traffic:error', callback);
  }

  // Map events
  onMapLoaded(callback: (data: MapLoadedData) => void) {
    return this.on('map:loaded', callback);
  }

  onMapLoading(callback: (data: any) => void) {
    return this.on('map:loading', callback);
  }

  onMapError(callback: (data: any) => void) {
    return this.on('map:error', callback);
  }

  // Data mode events
  onDataModeChanged(callback: (data: DataModeChangedData) => void) {
    return this.on('data:mode:changed', callback);
  }

  // System state events
  onSystemStateUpdate(callback: (data: SystemStateUpdateData) => void) {
    return this.on('system:state_update', callback);
  }

  onSimulationState(callback: (data: any) => void) {
    return this.on('simulation:state', callback);
  }

  // ============================================
  // Client → Server Emit Helpers
  // ============================================

  /**
   * Control simulation (PAUSE/RESUME/RESET/START/STOP)
   */
  controlSimulation(action: 'PAUSE' | 'RESUME' | 'RESET' | 'START' | 'STOP') {
    this.emit('simulation:control', { action, timestamp: Date.now() });
  }

  /**
   * Request vehicle spawn
   */
  spawnVehicle(type: 'car' | 'bike' | 'ambulance', spawnPoint?: string, destination?: string) {
    this.emit('vehicle:spawn', { type, spawnPoint, destination });
  }

  /**
   * Override signal at junction
   */
  overrideSignal(junctionId: string, direction: string, action: 'FORCE_GREEN' | 'LOCK_RED' | 'CLEAR', duration?: number) {
    this.emit('signal:override', { junctionId, direction, action, duration });
  }

  /**
   * Trigger emergency mode
   */
  triggerEmergency(spawnPoint: string, destination: string) {
    this.emit('emergency:trigger', { spawnPoint, destination });
  }

  /**
   * Clear emergency mode
   */
  clearEmergency(vehicleId?: string) {
    this.emit('emergency:clear', { vehicleId });
  }

  /**
   * Request map load
   */
  loadMap(method: 'bbox' | 'place' | 'radius' | 'predefined', parameters: Record<string, any>) {
    this.emit('map:load:request', { method, parameters });
  }

  /**
   * Change traffic data mode
   */
  changeTrafficMode(mode: 'LIVE_API' | 'MANUAL' | 'HYBRID' | 'SIMULATION', provider?: string) {
    this.emit('traffic:mode:change', { mode, provider });
  }

  /**
   * Set traffic override for a road
   */
  setTrafficOverride(roadId: string, congestionLevel: 'LOW' | 'MEDIUM' | 'HIGH' | 'JAM', duration?: number) {
    this.emit('traffic:override:set', { roadId, congestionLevel, duration });
  }

  /**
   * Clear traffic override
   */
  clearTrafficOverride(roadId?: string) {
    this.emit('traffic:override:clear', { roadId });
  }

  /**
   * Subscribe to update channels
   */
  subscribe(channels: string[]) {
    this.emit('subscribe:updates', { channels });
  }

  /**
   * Unsubscribe from channels
   */
  unsubscribe(channels: string[]) {
    this.emit('unsubscribe:updates', { channels });
  }
}

// ============================================
// Singleton Instance
// ============================================

export const wsService = new WebSocketService();
