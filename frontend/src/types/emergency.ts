/**
 * Emergency System Types
 * 
 * Type definitions for emergency vehicle tracking and green corridor management.
 * Implements FRD-07 frontend integration.
 */

// Emergency vehicle types
export type EmergencyVehicleType = 'AMBULANCE' | 'FIRE_TRUCK' | 'POLICE';

// Emergency session status
export type EmergencySessionStatus = 'ACTIVE' | 'COMPLETED' | 'CANCELLED';

// Position interface
export interface Position {
  x: number;
  y: number;
}

// Emergency vehicle data
export interface EmergencyVehicle {
  vehicleId: string;
  type: EmergencyVehicleType;
  numberPlate: string;
  currentPosition: Position;
  destination: Position;
  speed: number;
  heading: number;
}

// Emergency session
export interface EmergencySession {
  sessionId: string;
  vehicleId: string;
  vehicleType: EmergencyVehicleType;
  numberPlate: string;
  status: EmergencySessionStatus;
  activatedAt: number;
  completedAt?: number;
  currentPosition?: Position;
  destination: Position;
  destinationJunction: string;
  calculatedRoute: string[];
  affectedJunctions: string[];
  totalDistance: number;
  estimatedTime: number;
}

// Active corridor state
export interface ActiveCorridor {
  sessionId: string;
  junctionPath: string[];
  roadPath: string[];
  currentJunctionIndex: number;
  junctionCount: number;
  activatedAt: number;
  signalOverrides: Record<string, string>;  // junction -> green direction
  lookahead: number;
}

// Emergency status response
export interface EmergencyStatus {
  active: boolean;
  sessionId?: string;
  vehicleId?: string;
  vehicleType?: EmergencyVehicleType;
  numberPlate?: string;
  status?: EmergencySessionStatus;
  corridorPath: string[];
  roadPath: string[];
  currentJunction?: string;
  progress: number;
  estimatedArrival?: number;
  activatedAt?: number;
  corridorActive: boolean;
  corridor?: ActiveCorridor;
}

// Emergency trigger request
export interface EmergencyTriggerRequest {
  spawnPoint: string;
  destination: string;
  vehicleType?: EmergencyVehicleType;
  vehicleId?: string;
  numberPlate?: string;
}

// Emergency trigger response
export interface EmergencyTriggerResponse {
  status: string;
  sessionId: string;
  vehicleId: string;
  numberPlate: string;
  corridorPath: string[];
  roadPath: string[];
  estimatedTime: number;
  distance: number;
  activatedAt: number;
  destination: string;
}

// Emergency statistics
export interface EmergencyStatistics {
  totalEmergencies: number;
  completedEmergencies: number;
  cancelledEmergencies: number;
  activeEmergencies: number;
  currentSession?: string;
  totalTimeSaved: number;
  successRate: number;
  corridorStats: {
    corridorsActivated: number;
    corridorsCompleted: number;
    corridorActive: boolean;
    currentSession?: string;
  };
}

// Emergency progress update (from WebSocket)
export interface EmergencyProgressUpdate {
  vehicleId: string;
  currentJunction: string;
  progress: number;
  estimatedArrival: number;
}

// Emergency activated event (from WebSocket)
export interface EmergencyActivatedEvent {
  vehicleId: string;
  sessionId: string;
  corridorPath: string[];
  estimatedTime: number;
  destination: string;
  roadPath: string[];
  activatedAt: number;
}

// Emergency deactivated event (from WebSocket)
export interface EmergencyDeactivatedEvent {
  vehicleId: string;
  completionTime: number;
  reason: string;
}

// Path simulation result
export interface PathSimulation {
  simulated: boolean;
  corridorPath: string[];
  roadPath: string[];
  junctionCount: number;
  distance: number;
  estimatedTime: number;
  affectedJunctions: string[];
  dryRun: boolean;
  triggered?: boolean;
  sessionId?: string;
  vehicleId?: string;
}


