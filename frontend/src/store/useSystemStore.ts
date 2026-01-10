/**
 * Zustand Store for System State Management
 * 
 * Central store for all application state including vehicles,
 * junctions, roads, agent status, and performance metrics.
 */

import { create } from 'zustand';
import type { 
  Vehicle, 
  Junction, 
  RoadSegment, 
  SystemMode, 
  AgentStatus, 
  AgentStrategy,
  Violation,
  Challan,
  EmergencyVehicle,
  TrafficDataSource
} from '../types/models';

interface SystemStore {
  // Mode
  mode: SystemMode;
  
  // Simulation
  simulationTime: number;
  isPaused: boolean;
  isRunning: boolean;
  timeMultiplier: number;
  
  // Entities
  vehicles: Vehicle[];
  junctions: Junction[];
  roads: RoadSegment[];
  
  // Agent
  agentStatus: AgentStatus;
  agentStrategy: AgentStrategy;
  agentLoopCount: number;
  avgDecisionLatency: number;
  
  // Performance
  fps: number;
  vehicleCount: number;
  avgDensity: number;
  congestionPoints: number;
  throughput: number;
  
  // WebSocket
  wsConnected: boolean;
  
  // Violations & Challans
  violations: Violation[];
  challans: Challan[];
  
  // Emergency
  activeEmergencies: EmergencyVehicle[];
  
  // Data Source
  dataSource: TrafficDataSource;
  
  // Actions - Mode
  setMode: (mode: SystemMode) => void;
  
  // Actions - Simulation
  setSimulationTime: (time: number) => void;
  setIsPaused: (paused: boolean) => void;
  setIsRunning: (running: boolean) => void;
  setTimeMultiplier: (multiplier: number) => void;
  
  // Actions - Entities
  updateVehicles: (vehicles: Vehicle[]) => void;
  updateVehicle: (vehicle: Partial<Vehicle> & { id: string }) => void;
  removeVehicle: (vehicleId: string) => void;
  updateJunctions: (junctions: Junction[]) => void;
  updateJunctionSignal: (junctionId: string, direction: string, state: string) => void;
  updateRoads: (roads: RoadSegment[]) => void;
  updateRoadDensity: (roadId: string, densityScore: number, classification: string, vehicleCount: number) => void;
  
  // Actions - Agent
  setAgentStatus: (status: AgentStatus) => void;
  setAgentStrategy: (strategy: AgentStrategy) => void;
  updateAgentStats: (loopCount: number, latency: number) => void;
  
  // Actions - Performance
  updatePerformance: (metrics: Partial<{
    fps: number;
    vehicleCount: number;
    avgDensity: number;
    congestionPoints: number;
    throughput: number;
  }>) => void;
  
  // Actions - WebSocket
  setWsConnected: (connected: boolean) => void;
  
  // Actions - Violations & Challans
  addViolation: (violation: Violation) => void;
  addChallan: (challan: Challan) => void;
  updateChallanStatus: (challanId: string, status: string) => void;
  
  // Actions - Emergency
  addEmergency: (emergency: EmergencyVehicle) => void;
  removeEmergency: (vehicleId: string) => void;
  
  // Actions - System State (for WebSocket batch updates)
  setSystemState: (state: Partial<{
    mode: SystemMode;
    simulationTime: number;
    isPaused: boolean;
    vehicleCount: number;
    avgDensity: number;
    fps: number;
  }>) => void;
  
  // Actions - Data Source
  updateDataSource: (source: TrafficDataSource) => void;
  
  // Reset
  resetState: () => void;
}

const initialDataSource: TrafficDataSource = {
  mode: 'SIMULATION',
  apiKeyConfigured: false,
  activeOverrides: 0,
  globalMultiplier: 1.0,
};

const initialState = {
  mode: 'NORMAL' as SystemMode,
  simulationTime: 0,
  isPaused: false,
  isRunning: false,
  timeMultiplier: 1,
  vehicles: [] as Vehicle[],
  junctions: [] as Junction[],
  roads: [] as RoadSegment[],
  agentStatus: 'STOPPED' as AgentStatus,
  agentStrategy: 'RL' as AgentStrategy,
  agentLoopCount: 0,
  avgDecisionLatency: 0,
  fps: 60,
  vehicleCount: 0,
  avgDensity: 0,
  congestionPoints: 0,
  throughput: 0,
  wsConnected: false,
  violations: [] as Violation[],
  challans: [] as Challan[],
  activeEmergencies: [] as EmergencyVehicle[],
  dataSource: initialDataSource,
};

export const useSystemStore = create<SystemStore>((set, get) => ({
  ...initialState,
  
  // Mode
  setMode: (mode) => set({ mode }),
  
  // Simulation
  setSimulationTime: (time) => set({ simulationTime: time }),
  setIsPaused: (paused) => set({ isPaused: paused }),
  setIsRunning: (running) => set({ isRunning: running }),
  setTimeMultiplier: (multiplier) => set({ timeMultiplier: multiplier }),
  
  // Entities - Vehicles
  updateVehicles: (vehicles) => set({ 
    vehicles, 
    vehicleCount: vehicles.length 
  }),
  
  updateVehicle: (update) => set((state) => {
    const vehicles = state.vehicles.map((v) =>
      v.id === update.id ? { ...v, ...update } : v
    );
    return { vehicles };
  }),
  
  removeVehicle: (vehicleId) => set((state) => ({
    vehicles: state.vehicles.filter((v) => v.id !== vehicleId),
    vehicleCount: Math.max(0, state.vehicles.length - 1),
  })),
  
  // Entities - Junctions
  updateJunctions: (junctions) => set({ junctions }),
  
  updateJunctionSignal: (junctionId, direction, signalState) => set((s) => {
    const junctions = s.junctions.map((j) => {
      if (j.id === junctionId) {
        return {
          ...j,
          signals: {
            ...j.signals,
            [direction]: {
              ...j.signals[direction as keyof typeof j.signals],
              current: signalState,
              lastChange: Date.now() / 1000,
            },
          },
        };
      }
      return j;
    });
    return { junctions };
  }),
  
  // Entities - Roads
  updateRoads: (roads) => set({ roads }),
  
  updateRoadDensity: (roadId, densityScore, classification, vehicleCount) => set((s) => {
    const roads = s.roads.map((r) => {
      if (r.id === roadId) {
        return {
          ...r,
          traffic: {
            ...r.traffic,
            densityScore,
            density: classification as any,
            currentVehicles: Array(vehicleCount).fill(''),
          },
        };
      }
      return r;
    });
    return { roads };
  }),
  
  // Agent
  setAgentStatus: (agentStatus) => set({ agentStatus }),
  setAgentStrategy: (agentStrategy) => set({ agentStrategy }),
  updateAgentStats: (loopCount, latency) => set({
    agentLoopCount: loopCount,
    avgDecisionLatency: latency,
  }),
  
  // Performance
  updatePerformance: (metrics) => set(metrics),
  
  // WebSocket
  setWsConnected: (wsConnected) => set({ wsConnected }),
  
  // Violations
  addViolation: (violation) => set((s) => ({
    violations: [violation, ...s.violations].slice(0, 100), // Keep last 100
  })),
  
  // Challans
  addChallan: (challan) => set((s) => ({
    challans: [challan, ...s.challans].slice(0, 100),
  })),
  
  updateChallanStatus: (challanId, status) => set((s) => ({
    challans: s.challans.map((c) =>
      c.challanId === challanId ? { ...c, status: status as any } : c
    ),
  })),
  
  // Emergency
  addEmergency: (emergency) => set((s) => ({
    activeEmergencies: [...s.activeEmergencies, emergency],
    mode: 'EMERGENCY',
  })),
  
  removeEmergency: (vehicleId) => set((s) => {
    const activeEmergencies = s.activeEmergencies.filter(
      (e) => e.vehicleId !== vehicleId
    );
    return {
      activeEmergencies,
      mode: activeEmergencies.length === 0 ? 'NORMAL' : 'EMERGENCY',
    };
  }),
  
  // System State (for WebSocket batch updates)
  setSystemState: (state) => set({
    ...(state.mode !== undefined && { mode: state.mode }),
    ...(state.simulationTime !== undefined && { simulationTime: state.simulationTime }),
    ...(state.isPaused !== undefined && { isPaused: state.isPaused }),
    ...(state.vehicleCount !== undefined && { vehicleCount: state.vehicleCount }),
    ...(state.avgDensity !== undefined && { avgDensity: state.avgDensity }),
    ...(state.fps !== undefined && { fps: state.fps }),
  }),
  
  // Data Source
  updateDataSource: (dataSource) => set({ dataSource }),
  
  // Reset
  resetState: () => set(initialState),
}));
