/**
 * WebSocket Integration with Zustand Store
 * 
 * This module connects WebSocket events to the global state store,
 * enabling real-time updates across the application.
 */

import { 
  wsService,
  VehicleUpdateData,
  VehicleBatchUpdate,
  VehicleSpawnedData,
  VehicleRemovedData,
  SignalChangeData,
  DensityUpdateData,
  DensityBatchUpdate,
  AgentDecisionData,
  AgentStatusUpdateData,
  EmergencyActivatedData,
  EmergencyDeactivatedData,
  FailsafeTriggeredData,
  ViolationDetectedData,
  ChallanIssuedData,
  SystemStateUpdateData,
  MapLoadedData,
  DataModeChangedData,
} from './websocket';
import { useSystemStore } from '../store/useSystemStore';

// Track cleanup functions
const cleanupFunctions: (() => void)[] = [];

/**
 * Setup all WebSocket event listeners and connect to store
 */
export function setupWebSocketListeners() {
  console.log('[WS Integration] Setting up listeners...');
  
  // Clean up any existing listeners
  cleanupWebSocketListeners();
  
  // ============================================
  // System State Updates
  // ============================================
  
  cleanupFunctions.push(
    wsService.onSystemStateUpdate((data: SystemStateUpdateData) => {
      useSystemStore.getState().setSystemState({
        mode: data.mode as any,
        simulationTime: data.simulationTime,
        isPaused: data.isPaused,
        vehicleCount: data.vehicleCount,
        avgDensity: data.avgDensity,
        fps: data.fps,
      });
    })
  );

  // ============================================
  // Vehicle Updates
  // ============================================
  
  cleanupFunctions.push(
    wsService.onVehicleUpdate((data: VehicleUpdateData) => {
      useSystemStore.setState((state) => {
        const vehicles = [...state.vehicles];
        const index = vehicles.findIndex(v => v.id === data.vehicleId);
        
        if (index !== -1) {
          vehicles[index] = {
            ...vehicles[index],
            position: data.position,
            speed: data.speed,
            heading: data.heading,
            lastUpdate: data.timestamp,
            lat: data.lat,
            lon: data.lon,
          };
        }
        
        return { vehicles };
      });
    })
  );

  cleanupFunctions.push(
    wsService.onVehicleBatchUpdate((data: VehicleBatchUpdate) => {
      useSystemStore.setState((state) => {
        const vehicleMap = new Map(state.vehicles.map(v => [v.id, v]));
        
        for (const update of data.vehicles) {
          const existing = vehicleMap.get(update.vehicleId);
          if (existing) {
            vehicleMap.set(update.vehicleId, {
              ...existing,
              position: update.position,
              speed: update.speed,
              heading: update.heading,
              lastUpdate: update.timestamp,
            });
          }
        }
        
        return { 
          vehicles: Array.from(vehicleMap.values()),
          vehicleCount: vehicleMap.size 
        };
      });
    })
  );

  cleanupFunctions.push(
    wsService.onVehicleSpawned((data: VehicleSpawnedData) => {
      console.log('[WS] Vehicle spawned:', data.vehicleId);
      
      useSystemStore.setState((state) => ({
        vehicles: [...state.vehicles, {
          id: data.vehicleId,
          numberPlate: data.numberPlate,
          type: data.type,
          position: data.position,
          speed: 0,
          acceleration: 0,
          heading: 0,
          currentRoad: null,
          currentJunction: null,
          destination: data.destination,
          path: [],
          pathIndex: 0,
          isEmergency: data.type === 'ambulance',
          isViolating: false,
          waitingTime: 0,
          spawnTime: data.timestamp,
          lastUpdate: data.timestamp,
        }],
        vehicleCount: state.vehicleCount + 1,
      }));
    })
  );

  cleanupFunctions.push(
    wsService.onVehicleRemoved((data: VehicleRemovedData) => {
      console.log('[WS] Vehicle removed:', data.vehicleId, data.reason);
      
      useSystemStore.setState((state) => ({
        vehicles: state.vehicles.filter(v => v.id !== data.vehicleId),
        vehicleCount: state.vehicleCount - 1,
      }));
    })
  );

  // ============================================
  // Signal Updates
  // ============================================
  
  cleanupFunctions.push(
    wsService.onSignalChange((data: SignalChangeData) => {
      useSystemStore.setState((state) => {
        const junctions = [...state.junctions];
        const junction = junctions.find(j => j.id === data.junctionId);
        
        if (junction && junction.signals[data.direction]) {
          junction.signals[data.direction] = {
            ...junction.signals[data.direction],
            current: data.newState,
            duration: data.duration,
            lastChange: data.timestamp,
          };
          junction.lastSignalChange = data.timestamp;
        }
        
        return { junctions };
      });
    })
  );

  // ============================================
  // Density Updates
  // ============================================
  
  cleanupFunctions.push(
    wsService.onDensityUpdate((data: DensityUpdateData) => {
      useSystemStore.setState((state) => {
        const roads = [...state.roads];
        const road = roads.find(r => r.id === data.roadId);
        
        if (road) {
          road.traffic = {
            ...road.traffic,
            densityScore: data.densityScore,
            density: data.classification,
            currentVehicles: Array(data.vehicleCount).fill(''),
          };
          road.lastUpdate = data.timestamp;
        }
        
        return { roads };
      });
    })
  );

  cleanupFunctions.push(
    wsService.onDensityBatchUpdate((data: DensityBatchUpdate) => {
      useSystemStore.setState((state) => {
        const roadMap = new Map(state.roads.map(r => [r.id, r]));
        
        for (const update of data.roads) {
          const existing = roadMap.get(update.roadId);
          if (existing) {
            roadMap.set(update.roadId, {
              ...existing,
              traffic: {
                ...existing.traffic,
                densityScore: update.densityScore,
                density: update.classification,
                currentVehicles: Array(update.vehicleCount).fill(''),
              },
              lastUpdate: update.timestamp,
            });
          }
        }
        
        return { roads: Array.from(roadMap.values()) };
      });
    })
  );

  // ============================================
  // Agent Updates
  // ============================================
  
  cleanupFunctions.push(
    wsService.onAgentStatusUpdate((data: AgentStatusUpdateData) => {
      useSystemStore.getState().setAgentStatus(data.status);
      useSystemStore.getState().setAgentStrategy(data.strategy);
    })
  );

  cleanupFunctions.push(
    wsService.onAgentDecision((data: AgentDecisionData) => {
      console.log('[WS] Agent decision:', data.decisions.length, 'actions');
      // Could update a decision log in state if needed
    })
  );

  // ============================================
  // Emergency Updates
  // ============================================
  
  cleanupFunctions.push(
    wsService.onEmergencyActivated((data: EmergencyActivatedData) => {
      console.log('[WS] Emergency activated:', data.vehicleId);
      useSystemStore.getState().setMode('EMERGENCY');
      // Could store emergency details in state
    })
  );

  cleanupFunctions.push(
    wsService.onEmergencyDeactivated((data: EmergencyDeactivatedData) => {
      console.log('[WS] Emergency deactivated:', data.reason);
      useSystemStore.getState().setMode('NORMAL');
    })
  );

  // ============================================
  // Safety Updates
  // ============================================
  
  cleanupFunctions.push(
    wsService.onFailsafeTriggered((data: FailsafeTriggeredData) => {
      console.warn('[WS] FAILSAFE TRIGGERED:', data.reason);
      useSystemStore.getState().setMode('FAIL_SAFE' as any);
      // Could show notification/alert
    })
  );

  cleanupFunctions.push(
    wsService.onFailsafeCleared(() => {
      console.log('[WS] Failsafe cleared');
      useSystemStore.getState().setMode('NORMAL');
    })
  );

  // ============================================
  // Violation & Challan Updates
  // ============================================
  
  cleanupFunctions.push(
    wsService.onViolationDetected((data: ViolationDetectedData) => {
      console.warn('[WS] Violation detected:', data.violationType, 'at', data.location);
      // Could add to violations list in state
    })
  );

  cleanupFunctions.push(
    wsService.onChallanIssued((data: ChallanIssuedData) => {
      console.log('[WS] Challan issued:', data.challanId, 'Rs.', data.fineAmount);
      // Could add to challans list in state
    })
  );

  // ============================================
  // Map & Data Mode Updates
  // ============================================
  
  cleanupFunctions.push(
    wsService.onMapLoaded((data: MapLoadedData) => {
      console.log('[WS] Map loaded:', data.junctionCount, 'junctions,', data.roadCount, 'roads');
      // Could update map state
    })
  );

  cleanupFunctions.push(
    wsService.onDataModeChanged((data: DataModeChangedData) => {
      console.log('[WS] Data mode changed:', data.oldMode, '->', data.newMode);
      useSystemStore.getState().updateDataSource({
        ...useSystemStore.getState().dataSource,
        mode: data.newMode as any,
      });
    })
  );

  // ============================================
  // Connection status monitoring
  // ============================================
  
  // Check connection status periodically
  const connectionCheck = setInterval(() => {
    if (!wsService.isConnected) {
      console.log('[WS] Connection lost, attempting reconnect...');
    }
  }, 5000);

  cleanupFunctions.push(() => clearInterval(connectionCheck));

  console.log('[WS Integration] Listeners setup complete');
}

/**
 * Cleanup all WebSocket listeners
 */
export function cleanupWebSocketListeners() {
  console.log('[WS Integration] Cleaning up listeners...');
  
  for (const cleanup of cleanupFunctions) {
    try {
      cleanup();
    } catch (e) {
      console.error('[WS Integration] Cleanup error:', e);
    }
  }
  
  cleanupFunctions.length = 0;
}

/**
 * Get current WebSocket connection status
 */
export function getWebSocketStatus() {
  return {
    status: wsService.status,
    isConnected: wsService.isConnected,
    socketId: wsService.socketId,
  };
}
